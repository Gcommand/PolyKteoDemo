import os
import logging
from dotenv import load_dotenv
from typing import List, Tuple
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, desc, asc, func, text, bindparam, ARRAY, Float
from sqlalchemy.orm import sessionmaker, joinedload, contains_eager
from src.postgres_embedding import PatentsList, SearchLog, get_embedding, update_embedding, Departments, PatentDepartments, Assignees, PatentAssignees, TechSectors, PatentTechSectors
import asyncio
import re
from langdetect import detect, LangDetectException
from opencc import OpenCC

# Create Flask app
load_dotenv()
app = Flask(__name__)

# Initialize OpenCC converters for Chinese character conversion
converter_tw_to_cn = OpenCC('tw2sp')  # Traditional Chinese to Simplified Chinese
converter_cn_to_tw = OpenCC('s2twp')  # Simplified Chinese to Traditional Chinese

def detect_language(text: str) -> str:
    """
    Detect if the text is Traditional Chinese, Simplified Chinese, or English.
    Returns:
        'zh-TW': Traditional Chinese
        'zh-CN': Simplified Chinese
        'en': English
    """
    try:
        # First try to detect the general language
        lang = detect(text)
        # print(f"Detected language by langdetect: {lang}") # For debugging
        
        if 'zh' in lang: # Corrected check for any Chinese variant
            # Convert the original text to its purely Simplified form
            text_converted_to_simplified = converter_tw_to_cn.convert(text)
            # Convert the original text to its purely Traditional form
            text_converted_to_traditional = converter_cn_to_tw.convert(text)

            diff_to_simplified = 0
            # Ensure lengths match before character-wise comparison, though OpenCC usually preserves length for CJK
            if len(text) == len(text_converted_to_simplified):
                for i in range(len(text)):
                    if text[i] != text_converted_to_simplified[i]:
                        diff_to_simplified += 1
            else: # Fallback if lengths differ, consider it a large difference
                diff_to_simplified = len(text) 

            diff_to_traditional = 0
            if len(text) == len(text_converted_to_traditional):
                for i in range(len(text)):
                    if text[i] != text_converted_to_traditional[i]:
                        diff_to_traditional += 1
            else: # Fallback if lengths differ
                diff_to_traditional = len(text)
            
            # print(f"Text: '{text}', Diff to Simplified: {diff_to_simplified}, Diff to Traditional: {diff_to_traditional}") # For debugging

            if diff_to_simplified < diff_to_traditional:
                return 'zh-CN'  # Leans more towards Simplified
            elif diff_to_traditional < diff_to_simplified:
                return 'zh-TW'  # Leans more towards Traditional
            else:
                # Tie-breaker: Default to Traditional Chinese ('zh-TW')
                # This covers cases like "你好" (0 diff for both) or equally mixed inputs.
                return 'zh-TW' 
        return 'en' # If langdetect doesn't say 'zh'
    except LangDetectException:
        print(f"LangDetectException for text: '{text}'. Defaulting to 'en'.") # For debugging
        return 'en' # Default to English if langdetect fails
    except Exception as e:
        # Catch any other unexpected errors during conversion or comparison
        print(f"Error in detect_language for text '{text}': {e}")
        return 'en' # Fallback to English

def convert_chinese_summary(summary: str, target_lang: str) -> str:
    """
    Convert Chinese summary to target language (Traditional or Simplified).
    Rules:
    - For Traditional Chinese (zh-TW): Convert to Traditional Chinese
    - For Simplified Chinese (zh-CN): Convert to Simplified Chinese
    - For English (en): Convert to Traditional Chinese (default for English queries)
    
    The function preserves English text and only converts Chinese characters.
    
    Args:
        summary: The text to convert
        target_lang: Target language ('zh-TW', 'zh-CN', or 'en')
    
    Returns:
        Converted text or original text if conversion is not needed/fails
    """
    if not summary or target_lang == 'en':
        return summary
    
    try:
        # Split the text into Chinese and non-Chinese parts
        parts = []
        current_part = ""
        is_chinese = False
        
        for char in summary:
            # Check if character is Chinese
            is_current_chinese = '\u4e00' <= char <= '\u9fff'
            
            # If we're switching between Chinese and non-Chinese, save the current part
            if is_current_chinese != is_chinese and current_part:
                parts.append((current_part, is_chinese))
                current_part = ""
                is_chinese = is_current_chinese
            
            current_part += char
        
        # Add the last part
        if current_part:
            parts.append((current_part, is_chinese))
        
        # Convert only the Chinese parts
        converted_parts = []
        for part, is_chinese_part in parts:
            if is_chinese_part:
                if target_lang == 'zh-TW':
                    converted_parts.append(converter_cn_to_tw.convert(part))
                elif target_lang == 'zh-CN':
                    converted_parts.append(converter_tw_to_cn.convert(part))
            else:
                converted_parts.append(part)
        
        return ''.join(converted_parts)
    except Exception as e:
        print(f"Error converting Chinese summary: {e}")
        return summary

# Database connection
DATABASE_URL = os.getenv("AZURE_POSTGRES_CONNECTION")
engine = create_engine(DATABASE_URL, connect_args={'client_encoding': 'utf8'})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Response model
class PatentResponse:
    def __init__(self, sys_id, official_title, tech_sector=None, inventor=None, department=None, country_region=None, google_patent_link=None, ai_summary=None, similarity=None, is_tech=None, ai_short_summary=None):
        self.sys_id = sys_id
        self.official_title = official_title
        self.tech_sector = tech_sector
        self.inventor = inventor
        self.department = department
        self.country_region = country_region
        self.google_patent_link = google_patent_link
        self.ai_summary = ai_summary
        self.similarity = similarity
        self.is_tech = is_tech
        self.ai_short_summary = ai_short_summary

def apply_sorting(query, sort_order, similarity_score, department_ids=None, assignee_ids=None, tech_sector_ids=None, is_cn_applied=None, confidence_level=None, query_embedding=None):
    """Apply sorting to the query based on the sort order.
    
    This function handles different sorting criteria for patent search results.
    
    Key Implementation Notes:
    1. Query Structure:
       - Uses SQLAlchemy's query API for better type safety
       - Joins all necessary tables in a single query
       - Handles null values appropriately
       - Uses subqueries for department sorting to get first department name
       - Includes similarity score for all sorting orders
    
    Args:
        query: Base query to apply sorting to
        sort_order: String indicating the sort order (REL_DESC, REL_ASC, etc.)
        similarity_score: The similarity score expression to use for sorting
        department_ids: List of department IDs to filter by
        assignee_ids: List of assignee IDs to filter by
        tech_sector_ids: List of tech sector IDs to filter by
        is_cn_applied: Boolean filter for CN application status
        confidence_level: Minimum similarity score threshold
        query_embedding: The embedding vector for similarity calculation
    
    Returns:
        Query with appropriate sorting and relationship loading applied
    """
    print(f"DEBUG: apply_sorting called with sort_order: {sort_order}")
    print(f"DEBUG: apply_sorting filters - dept: {department_ids}, assignee: {assignee_ids}, tech: {tech_sector_ids}, cn: {is_cn_applied}, conf: {confidence_level}")
    
    # Recreate the similarity score expression if query_embedding is provided
    if query_embedding is not None:
        similarity_score = (1 - PatentsList.embedding.cosine_distance(query_embedding)).label("similarity")
        print(f"DEBUG: Recreated similarity score expression with query_embedding length: {len(query_embedding)}")
    
    # Create a subquery for ranked departments that preserves the original query's filters
    print("DEBUG: Creating ranked departments subquery with original filters...")
    
    # Start with the same base query structure as the original query
    ranked_departments_query = (
        query.session.query(
            PatentsList.sys_id,
            Departments.department_name,
            func.row_number().over(
                partition_by=PatentsList.sys_id,
                order_by=Departments.department_name
            ).label('dept_rank')
        )
        .outerjoin(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
        .outerjoin(Departments, PatentDepartments.department_id == Departments.department_id)
    )
    
    # Apply the same filters as the original query
    print("DEBUG: Applying original query filters to ranked departments subquery...")
    
    # Apply embedding filter
    if confidence_level is not None:
        ranked_departments_query = ranked_departments_query.filter(PatentsList.embedding.is_not(None))
        # Note: We can't apply similarity filter here as we don't have the query embedding in this context
    
    # Apply department filter
    if department_ids:
        ranked_departments_query = ranked_departments_query.filter(PatentDepartments.department_id.in_(department_ids))
    
    # Apply assignee filter
    if assignee_ids:
        ranked_departments_query = ranked_departments_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
        ranked_departments_query = ranked_departments_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
    
    # Apply tech sector filter
    if tech_sector_ids:
        ranked_departments_query = ranked_departments_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
        ranked_departments_query = ranked_departments_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
    
    # Apply is_cn_applied filter
    if is_cn_applied is not None:
        ranked_departments_query = ranked_departments_query.filter(PatentsList.is_cn_applied == is_cn_applied)
    
    ranked_departments = ranked_departments_query.subquery()
    print("DEBUG: Ranked departments subquery created")
    
    if sort_order == 'REL_DESC':
        print("DEBUG: Applying REL_DESC sorting (relevance descending)")
        main_query = (
            query.session.query(
                PatentsList,
                similarity_score,
                ranked_departments.c.department_name
            )
            .outerjoin(ranked_departments, PatentsList.sys_id == ranked_departments.c.sys_id)
            .filter(ranked_departments.c.dept_rank == 1)
        )
        
        # Apply the same filters as the original query
        if confidence_level is not None:
            main_query = main_query.filter(PatentsList.embedding.is_not(None))
            main_query = main_query.filter(similarity_score >= confidence_level)
            print(f"DEBUG: Applied embedding and similarity filters with confidence_level: {confidence_level}")
        
        if department_ids:
            main_query = main_query.join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            main_query = main_query.filter(PatentDepartments.department_id.in_(department_ids))
            print(f"DEBUG: Applied department filter for IDs: {department_ids}")
        
        if assignee_ids:
            main_query = main_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            main_query = main_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            print(f"DEBUG: Applied assignee filter for IDs: {assignee_ids}")
        
        if tech_sector_ids:
            main_query = main_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            main_query = main_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            print(f"DEBUG: Applied tech sector filter for IDs: {tech_sector_ids}")
        
        if is_cn_applied is not None:
            main_query = main_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print(f"DEBUG: Applied is_cn_applied filter: {is_cn_applied}")
        
        print(f"DEBUG: Final query filters applied. Returning query with {sort_order} sorting.")
        return main_query.order_by(similarity_score.desc())
    elif sort_order == 'REL_ASC':
        print("DEBUG: Applying REL_ASC sorting (relevance ascending)")
        main_query = (
            query.session.query(
                PatentsList,
                similarity_score,
                ranked_departments.c.department_name
            )
            .outerjoin(ranked_departments, PatentsList.sys_id == ranked_departments.c.sys_id)
            .filter(ranked_departments.c.dept_rank == 1)
        )
        
        # Apply the same filters as the original query
        if confidence_level is not None:
            main_query = main_query.filter(PatentsList.embedding.is_not(None))
            main_query = main_query.filter(similarity_score >= confidence_level)
            print(f"DEBUG: Applied embedding and similarity filters with confidence_level: {confidence_level}")
        
        if department_ids:
            main_query = main_query.join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            main_query = main_query.filter(PatentDepartments.department_id.in_(department_ids))
            print(f"DEBUG: Applied department filter for IDs: {department_ids}")
        
        if assignee_ids:
            main_query = main_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            main_query = main_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            print(f"DEBUG: Applied assignee filter for IDs: {assignee_ids}")
        
        if tech_sector_ids:
            main_query = main_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            main_query = main_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            print(f"DEBUG: Applied tech sector filter for IDs: {tech_sector_ids}")
        
        if is_cn_applied is not None:
            main_query = main_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print(f"DEBUG: Applied is_cn_applied filter: {is_cn_applied}")
        
        print(f"DEBUG: Final query filters applied. Returning query with {sort_order} sorting.")
        return main_query.order_by(similarity_score)
    elif sort_order == 'FSD_ASC':
        print("DEBUG: Applying FSD_ASC sorting (faculty/school/department A-Z)")
        # For department sorting, we need to join directly with departments to get proper sorting
        main_query = (
            query.session.query(
                PatentsList,
                similarity_score,
                Departments.department_name
            )
            .outerjoin(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            .outerjoin(Departments, PatentDepartments.department_id == Departments.department_id)
        )
        
        # Apply the same filters as the original query
        if confidence_level is not None:
            main_query = main_query.filter(PatentsList.embedding.is_not(None))
            main_query = main_query.filter(similarity_score >= confidence_level)
            print(f"DEBUG: Applied embedding and similarity filters with confidence_level: {confidence_level}")
        
        if department_ids:
            main_query = main_query.filter(PatentDepartments.department_id.in_(department_ids))
            print(f"DEBUG: Applied department filter for IDs: {department_ids}")
        
        if assignee_ids:
            main_query = main_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            main_query = main_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            print(f"DEBUG: Applied assignee filter for IDs: {assignee_ids}")
        
        if tech_sector_ids:
            main_query = main_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            main_query = main_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            print(f"DEBUG: Applied tech sector filter for IDs: {tech_sector_ids}")
        
        if is_cn_applied is not None:
            main_query = main_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print(f"DEBUG: Applied is_cn_applied filter: {is_cn_applied}")
        
        print(f"DEBUG: Final query filters applied. Returning query with {sort_order} sorting.")
        # Use binary collation to match Python's default string comparison
        return main_query.order_by(Departments.department_name.collate('C').nulls_last(), PatentsList.sys_id)
    elif sort_order == 'FSD_DESC':
        print("DEBUG: Applying FSD_DESC sorting (faculty/school/department Z-A)")
        # For department sorting, we need to join directly with departments to get proper sorting
        main_query = (
            query.session.query(
                PatentsList,
                similarity_score,
                Departments.department_name
            )
            .outerjoin(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            .outerjoin(Departments, PatentDepartments.department_id == Departments.department_id)
        )
        
        # Apply the same filters as the original query
        if confidence_level is not None:
            main_query = main_query.filter(PatentsList.embedding.is_not(None))
            main_query = main_query.filter(similarity_score >= confidence_level)
            print(f"DEBUG: Applied embedding and similarity filters with confidence_level: {confidence_level}")
        
        if department_ids:
            main_query = main_query.filter(PatentDepartments.department_id.in_(department_ids))
            print(f"DEBUG: Applied department filter for IDs: {department_ids}")
        
        if assignee_ids:
            main_query = main_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            main_query = main_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            print(f"DEBUG: Applied assignee filter for IDs: {assignee_ids}")
        
        if tech_sector_ids:
            main_query = main_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            main_query = main_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            print(f"DEBUG: Applied tech sector filter for IDs: {tech_sector_ids}")
        
        if is_cn_applied is not None:
            main_query = main_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print(f"DEBUG: Applied is_cn_applied filter: {is_cn_applied}")
        
        print(f"DEBUG: Final query filters applied. Returning query with {sort_order} sorting.")
        # Use binary collation to match Python's default string comparison
        return main_query.order_by(desc(Departments.department_name.collate('C')).nulls_last(), PatentsList.sys_id)
    elif sort_order == 'DATE_DESC':
        print("DEBUG: Applying DATE_DESC sorting (date descending)")
        main_query = (
            query.session.query(
                PatentsList,
                similarity_score,
                ranked_departments.c.department_name
            )
            .outerjoin(ranked_departments, PatentsList.sys_id == ranked_departments.c.sys_id)
            .filter(ranked_departments.c.dept_rank == 1)
        )
        
        # Apply the same filters as the original query
        if confidence_level is not None:
            main_query = main_query.filter(PatentsList.embedding.is_not(None))
            main_query = main_query.filter(similarity_score >= confidence_level)
            print(f"DEBUG: Applied embedding and similarity filters with confidence_level: {confidence_level}")
        
        if department_ids:
            main_query = main_query.join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            main_query = main_query.filter(PatentDepartments.department_id.in_(department_ids))
            print(f"DEBUG: Applied department filter for IDs: {department_ids}")
        
        if assignee_ids:
            main_query = main_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            main_query = main_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            print(f"DEBUG: Applied assignee filter for IDs: {assignee_ids}")
        
        if tech_sector_ids:
            main_query = main_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            main_query = main_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            print(f"DEBUG: Applied tech sector filter for IDs: {tech_sector_ids}")
        
        if is_cn_applied is not None:
            main_query = main_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print(f"DEBUG: Applied is_cn_applied filter: {is_cn_applied}")
        
        print(f"DEBUG: Final query filters applied. Returning query with {sort_order} sorting.")
        return main_query.order_by(desc(PatentsList.created_dt))
    elif sort_order == 'DATE_ASC':
        print("DEBUG: Applying DATE_ASC sorting (date ascending)")
        main_query = (
            query.session.query(
                PatentsList,
                similarity_score,
                ranked_departments.c.department_name
            )
            .outerjoin(ranked_departments, PatentsList.sys_id == ranked_departments.c.sys_id)
            .filter(ranked_departments.c.dept_rank == 1)
        )
        
        # Apply the same filters as the original query
        if confidence_level is not None:
            main_query = main_query.filter(PatentsList.embedding.is_not(None))
            main_query = main_query.filter(similarity_score >= confidence_level)
            print(f"DEBUG: Applied embedding and similarity filters with confidence_level: {confidence_level}")
        
        if department_ids:
            main_query = main_query.join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            main_query = main_query.filter(PatentDepartments.department_id.in_(department_ids))
            print(f"DEBUG: Applied department filter for IDs: {department_ids}")
        
        if assignee_ids:
            main_query = main_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            main_query = main_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            print(f"DEBUG: Applied assignee filter for IDs: {assignee_ids}")
        
        if tech_sector_ids:
            main_query = main_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            main_query = main_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            print(f"DEBUG: Applied tech sector filter for IDs: {tech_sector_ids}")
        
        if is_cn_applied is not None:
            main_query = main_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print(f"DEBUG: Applied is_cn_applied filter: {is_cn_applied}")
        
        print(f"DEBUG: Final query filters applied. Returning query with {sort_order} sorting.")
        return main_query.order_by(PatentsList.created_dt)
    else:
        # Default to unsorted results
        print(f"DEBUG: Unknown sort_order '{sort_order}', using default unsorted")
        main_query = (
            query.session.query(
                PatentsList,
                similarity_score,
                ranked_departments.c.department_name
            )
            .outerjoin(ranked_departments, PatentsList.sys_id == ranked_departments.c.sys_id)
            .filter(ranked_departments.c.dept_rank == 1)
        )
        
        # Apply the same filters as the original query
        if confidence_level is not None:
            main_query = main_query.filter(PatentsList.embedding.is_not(None))
            main_query = main_query.filter(similarity_score >= confidence_level)
            print(f"DEBUG: Applied embedding and similarity filters with confidence_level: {confidence_level}")
        
        if department_ids:
            main_query = main_query.join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            main_query = main_query.filter(PatentDepartments.department_id.in_(department_ids))
            print(f"DEBUG: Applied department filter for IDs: {department_ids}")
        
        if assignee_ids:
            main_query = main_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            main_query = main_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            print(f"DEBUG: Applied assignee filter for IDs: {assignee_ids}")
        
        if tech_sector_ids:
            main_query = main_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            main_query = main_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            print(f"DEBUG: Applied tech sector filter for IDs: {tech_sector_ids}")
        
        if is_cn_applied is not None:
            main_query = main_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print(f"DEBUG: Applied is_cn_applied filter: {is_cn_applied}")
        
        print(f"DEBUG: Final query filters applied. Returning query with {sort_order} sorting.")
        return main_query

@app.route('/search', methods=['GET'])
def search_patents():
    """
    Search for patents similar to the query text using vector embeddings.
    Returns a list of patents sorted by the specified criteria.
    
    Language-specific behavior:
    - Traditional Chinese queries: Display summaries in English + Traditional Chinese
    - Simplified Chinese queries: Display summaries in English + Simplified Chinese
    - English queries: Display summaries in English + Traditional Chinese

    Query parameters:
    - query: The search query to find similar patents
    - confidence_level: Minimum similarity score threshold (default: 0.2)
    - sorting_order: Sort order for results (default: REL_DESC)
        Options:
        - REL_DESC: Sort by Relevance: Descending
        - REL_ASC: Sort by Relevance: Ascending
        - FSD_ASC: Sort by Faculties, Schools & Departments: A-Z
        - FSD_DESC: Sort by Faculties, Schools & Departments: Z-A
        - DATE_DESC: Sort by Latest date: Latest
        - DATE_ASC: Sort by Latest date: Oldest
    - current_page: Current page number (default: 1)
    - page_size: Number of results per page (default: 12)
    - department: Department ID(s) to filter results (optional, can be multiple values)
        Examples:
        - department=1,2,3 (comma-separated)
        - department=1&department=2 (multiple parameters)
    - tech_sector_id: Tech sector ID(s) to filter results (optional, can be multiple values)
        Examples:
        - tech_sector_id=1,2,3 (comma-separated)
        - tech_sector_id=1&tech_sector_id=2 (multiple parameters)
    - assignee_id: Assignee ID(s) to filter results (optional, can be multiple values)
        Examples:
        - assignee_id=1,2,3 (comma-separated)
        - assignee_id=1&assignee_id=2 (multiple parameters)
    - is_cn_applied: Filter by CN application status (optional, boolean)
    """
    print("=== SEARCH DEBUG START ===")
    
    # Get query parameters
    query = request.args.get('query')
    confidence_level = request.args.get('confidence_level', default=0.2, type=float)
    sorting_order = request.args.get('sorting_order', default='REL_DESC')
    current_page = request.args.get('current_page', default=1, type=int)
    page_size = request.args.get('page_size', default=12, type=int)
    
    print(f"DEBUG: Raw query parameters:")
    print(f"  - query: {query}")
    print(f"  - confidence_level: {confidence_level}")
    print(f"  - sorting_order: {sorting_order}")
    print(f"  - current_page: {current_page}")
    print(f"  - page_size: {page_size}")
    
    # Handle multiple department_id values
    department_ids = []
    department_param = request.args.get('department') or request.args.get('departmentNumber')
    if department_param and department_param.strip():
        department_ids.extend([
            int(id.strip()) 
            for id in department_param.split(',')
            if id.strip()
        ])
    
    # Handle multiple tech_sector_id values
    tech_sector_ids = []
    tech_sector_param = request.args.get('tech_sector_id') or request.args.get('techSectorId')
    if tech_sector_param and tech_sector_param.strip():
        tech_sector_ids.extend([
            int(id.strip()) 
            for id in tech_sector_param.split(',')
            if id.strip()
        ])
    
    # Handle multiple assignee_id values
    assignee_ids = []
    assignee_param = request.args.get('assignee_id') or request.args.get('assigneeId')
    if assignee_param and assignee_param.strip():
        assignee_ids.extend([
            int(id.strip()) 
            for id in assignee_param.split(',')
            if id.strip()
        ])
    
    is_cn_applied = request.args.get('is_cn_applied', type=lambda v: v.lower() == 'true' if v is not None else None)

    # Add debug logging
    print(f"DEBUG: Processed filter parameters:")
    print(f"  - department_ids: {department_ids}")
    print(f"  - tech_sector_ids: {tech_sector_ids}")
    print(f"  - assignee_ids: {assignee_ids}")
    print(f"  - is_cn_applied: {is_cn_applied}")

    # Validate confidence_level is between 0 and 1
    if confidence_level < 0 or confidence_level > 1:
        print(f"DEBUG: Invalid confidence_level: {confidence_level}")
        return jsonify({"error": "confidence_level must be between 0 and 1"}), 400

    if not query:
        print("DEBUG: Missing query parameter")
        return jsonify({"error": "Query parameter is required"}), 400

    # Detect query language
    query_lang = detect_language(query)
    print(f"DEBUG: Query language detected: {query_lang}")

    # Get a database session
    db = SessionLocal()
    print("DEBUG: Database session created")

    try:
        # Generate embedding for the query
        print(f"DEBUG: Generating embedding for query: '{query}'")
        query_embedding = asyncio.run(get_embedding(query))
        print(f"DEBUG: Embedding generated, length: {len(query_embedding)}")

        # Calculate similarity score expression
        similarity_score = (1 - PatentsList.embedding.cosine_distance(query_embedding)).label("similarity")
        print("DEBUG: Similarity score expression created")

        # Base query with similarity score
        print("DEBUG: Building base query...")
        base_query = (
            db.query(
                PatentsList,
                similarity_score
            )
            .filter(PatentsList.embedding.is_not(None))
            .filter(similarity_score >= confidence_level)
        )
        print(f"DEBUG: Base query built with confidence threshold: {confidence_level}")

        # Add department filter if department_ids are provided
        if department_ids:
            print(f"DEBUG: Adding department filter for IDs: {department_ids}")
            base_query = (
                base_query
                .join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
                .filter(PatentDepartments.department_id.in_(department_ids))
            )
            print("DEBUG: Department filter added")

        # Add assignee filter if assignee_ids are provided
        if assignee_ids:
            print(f"DEBUG: Adding assignee filter for IDs: {assignee_ids}")
            base_query = (
                base_query
                .join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
                .filter(PatentAssignees.assignee_id.in_(assignee_ids))
            )
            print("DEBUG: Assignee filter added")

        # Add tech_sector filter if provided
        if tech_sector_ids:
            print(f"DEBUG: Adding tech sector filter for IDs: {tech_sector_ids}")
            base_query = (
                base_query
                .join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
                .filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            )
            print("DEBUG: Tech sector filter added")

        # Add is_cn_applied filter if provided
        if is_cn_applied is not None:
            print(f"DEBUG: Adding is_cn_applied filter: {is_cn_applied}")
            base_query = base_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            print("DEBUG: is_cn_applied filter added")

        # Calculate total count for pagination using a subquery
        print("DEBUG: Calculating total count for pagination...")
        
        # Use the same base query structure for counting
        count_query = (
            db.query(PatentsList.sys_id)
            .filter(PatentsList.embedding.is_not(None))
            .filter(similarity_score >= confidence_level)
        )
        
        # Apply the same filters as the base query
        if department_ids:
            count_query = count_query.join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            count_query = count_query.filter(PatentDepartments.department_id.in_(department_ids))
        if assignee_ids:
            count_query = count_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
            count_query = count_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
        if tech_sector_ids:
            count_query = count_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
            count_query = count_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
        if is_cn_applied is not None:
            count_query = count_query.filter(PatentsList.is_cn_applied == is_cn_applied)
        
        # Debug: Check similarity scores for patents in department 1
        print("DEBUG: Checking similarity scores for patents in department 1...")
        test_query = (
            db.query(PatentsList.sys_id, similarity_score)
            .filter(PatentsList.embedding.is_not(None))
            .join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
            .filter(PatentDepartments.department_id.in_(department_ids))
            .limit(5)
        )
        test_results = test_query.all()
        print(f"DEBUG: Found {len(test_results)} patents in department 1")
        for i, (patent_id, similarity) in enumerate(test_results):
            print(f"DEBUG: Patent {patent_id} - Similarity: {similarity}")
        
        total_count = count_query.count()
        print(f"DEBUG: Total count calculated: {total_count}")
        
        # If no results found, try with a lower confidence threshold
        adjusted_confidence_level = confidence_level
        if total_count == 0 and test_results:
            # Find the highest similarity score
            max_similarity = max(similarity for _, similarity in test_results)
            print(f"DEBUG: Highest similarity score found: {max_similarity}")
            
            # Set confidence level to 80% of the highest similarity score, but not lower than 0.05
            adjusted_confidence_level = max(max_similarity * 0.8, 0.05)
            print(f"DEBUG: Adjusted confidence level from {confidence_level} to {adjusted_confidence_level}")
            
            # Rebuild the queries with the adjusted confidence level
            base_query = (
                db.query(
                    PatentsList,
                    similarity_score
                )
                .filter(PatentsList.embedding.is_not(None))
                .filter(similarity_score >= adjusted_confidence_level)
            )
            
            # Reapply filters to base_query
            if department_ids:
                base_query = (
                    base_query
                    .join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
                    .filter(PatentDepartments.department_id.in_(department_ids))
                )
            if assignee_ids:
                base_query = (
                    base_query
                    .join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
                    .filter(PatentAssignees.assignee_id.in_(assignee_ids))
                )
            if tech_sector_ids:
                base_query = (
                    base_query
                    .join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
                    .filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
                )
            if is_cn_applied is not None:
                base_query = base_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            
            # Recalculate count with adjusted confidence level
            count_query = (
                db.query(PatentsList.sys_id)
                .filter(PatentsList.embedding.is_not(None))
                .filter(similarity_score >= adjusted_confidence_level)
            )
            if department_ids:
                count_query = count_query.join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
                count_query = count_query.filter(PatentDepartments.department_id.in_(department_ids))
            if assignee_ids:
                count_query = count_query.join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
                count_query = count_query.filter(PatentAssignees.assignee_id.in_(assignee_ids))
            if tech_sector_ids:
                count_query = count_query.join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
                count_query = count_query.filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            if is_cn_applied is not None:
                count_query = count_query.filter(PatentsList.is_cn_applied == is_cn_applied)
            
            total_count = count_query.count()
            print(f"DEBUG: Total count with adjusted confidence level: {total_count}")
        
        # Debug: Show count query SQL (with error handling)
        try:
            count_sql = str(count_query.compile(compile_kwargs={'literal_binds': True}))
            print(f"DEBUG: Count query SQL: {count_sql}")
        except Exception as e:
            print(f"DEBUG: Could not compile count query SQL: {e}")

        # Apply sorting
        print(f"DEBUG: Applying sorting with order: {sorting_order}")
        
        # Instead of creating a new query, let's modify the existing base_query
        if sorting_order == 'REL_DESC':
            print("DEBUG: Applying REL_DESC sorting to existing base_query")
            base_query = base_query.order_by(similarity_score.desc())
        elif sorting_order == 'REL_ASC':
            print("DEBUG: Applying REL_ASC sorting to existing base_query")
            base_query = base_query.order_by(similarity_score)
        elif sorting_order == 'FSD_ASC':
            print("DEBUG: Applying FSD_ASC sorting to existing base_query")
            # For department sorting, we need to join with departments
            base_query = (
                base_query
                .outerjoin(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
                .outerjoin(Departments, PatentDepartments.department_id == Departments.department_id)
                .order_by(Departments.department_name)
            )
        elif sorting_order == 'FSD_DESC':
            print("DEBUG: Applying FSD_DESC sorting to existing base_query")
            base_query = (
                base_query
                .outerjoin(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
                .outerjoin(Departments, PatentDepartments.department_id == Departments.department_id)
                .order_by(desc(Departments.department_name))
            )
        elif sorting_order == 'DATE_DESC':
            print("DEBUG: Applying DATE_DESC sorting to existing base_query")
            base_query = base_query.order_by(desc(PatentsList.created_dt))
        elif sorting_order == 'DATE_ASC':
            print("DEBUG: Applying DATE_ASC sorting to existing base_query")
            base_query = base_query.order_by(PatentsList.created_dt)
        else:
            print(f"DEBUG: Unknown sort_order '{sorting_order}', using default unsorted")
        
        print("DEBUG: Sorting applied to existing base_query")
        
        # Debug: Show main query SQL (with error handling)
        try:
            main_sql = str(base_query.compile(compile_kwargs={'literal_binds': True}))
            print(f"DEBUG: Main query SQL: {main_sql}")
        except Exception as e:
            print(f"DEBUG: Could not compile main query SQL: {e}")

        # Apply pagination
        offset = (current_page - 1) * page_size
        print(f"DEBUG: Applying pagination - offset: {offset}, limit: {page_size}")
        results = base_query.offset(offset).limit(page_size).all()
        print(f"DEBUG: Query executed, returned {len(results)} results")
        
        # Debug: Check similarity scores
        if results:
            print("DEBUG: Checking similarity scores for results:")
            for i, result in enumerate(results):
                patent, similarity = result
                print(f"DEBUG: Result {i+1} - Patent ID: {patent.sys_id}, Similarity: {similarity}, Type: {type(similarity)}")
        else:
            print("DEBUG: No results returned from query")
            
            # Let's debug the query itself
            print("DEBUG: Checking base query without pagination...")
            all_results = base_query.all()
            print(f"DEBUG: Base query without pagination returned {len(all_results)} results")
            if all_results:
                print("DEBUG: First few results from base query:")
                for i, result in enumerate(all_results[:3]):
                    patent, similarity = result
                    print(f"DEBUG: Base result {i+1} - Patent ID: {patent.sys_id}, Similarity: {similarity}")

        # Format the results
        print("DEBUG: Formatting results...")
        response = []
        for i, result in enumerate(results):
            print(f"DEBUG: Processing result {i+1}/{len(results)}")
            
            # Unpack the result tuple (patent, similarity) - simpler structure now
            if len(result) == 2:
                patent, similarity = result
                department_name = None  # We'll get this separately
            else:
                patent, similarity, department_name = result
            
            print(f"DEBUG: Result {i+1} - Patent ID: {patent.sys_id}, Similarity: {similarity}, Type: {type(similarity)}")
            
            # Get departments for this patent
            patent_departments = (
                db.query(Departments)
                .join(PatentDepartments, Departments.department_id == PatentDepartments.department_id)
                .filter(PatentDepartments.patent_id == patent.sys_id)
                .all()
            )
            print(f"DEBUG: Found {len(patent_departments)} departments for patent {patent.sys_id}")
            
            departments_list = [
                {
                    "department_id": dept.department_id,
                    "department_name": dept.department_name,
                    "abbreviation": dept.abbreviation
                }
                for dept in patent_departments
            ]

            # Get tech sectors for this patent
            tech_sectors_list = [
                {
                    "tech_sector_id": ts.tech_sector_id,
                    "tech_sector_name": ts.tech_sector_name
                }
                for ts in patent.tech_sectors
            ]
            print(f"DEBUG: Found {len(tech_sectors_list)} tech sectors for patent {patent.sys_id}")

            # Determine target Chinese language based on query language
            target_chinese = 'zh-TW'  # Default to Traditional Chinese
            if query_lang == 'zh-CN':
                target_chinese = 'zh-CN'

            # Convert summaries to target Chinese language
            chinese_summary = convert_chinese_summary(patent.ai_summary, target_chinese)
            chinese_short_summary = convert_chinese_summary(patent.ai_short_summary, target_chinese)

            patent_dict = {
                "sys_id": patent.sys_id,
                "official_title": patent.official_title,
                "tech_sectors": tech_sectors_list,
                "inventor": patent.inventor,
                "department": patent.department,  # Keep for backward compatibility
                "departments": departments_list,
                "country_region": patent.country_region,
                "google_patent_link": patent.google_patent_link,
                "ai_summary": chinese_summary,
                "similarity": float(similarity) if similarity is not None else 0.0,
                "is_tech": patent.is_tech,
                "is_cn_applied": patent.is_cn_applied,
                "ai_short_summary": chinese_short_summary,
                "query_language": query_lang
            }
            response.append(patent_dict)
            print(f"DEBUG: Result {i+1} formatted successfully")

        print(f"DEBUG: All {len(response)} results formatted successfully")

        # Log the successful search
        log_entry = SearchLog(
            ip_address=request.remote_addr,
            headers=dict(request.headers),
            query=query,
            query_limit=page_size,
            confidence_level=confidence_level,
            status="success"
        )
        db.add(log_entry)
        db.commit()
        print("DEBUG: Search log entry created and committed")

        final_response = {
            "results": response,
            "pagination": {
                "total_count": total_count,
                "current_page": current_page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            },
            "query_language": query_lang
        }
        
        print("=== SEARCH DEBUG END ===")
        return jsonify(final_response)

    except Exception as e:
        # Enhanced error logging
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "query": query,
            "sorting_order": sorting_order,
            "confidence_level": confidence_level,
            "department_ids": department_ids,
            "tech_sector_ids": tech_sector_ids,
            "assignee_ids": assignee_ids,
            "is_cn_applied": is_cn_applied
        }
        print("=== SEARCH ERROR DETAILS ===")
        print(f"Error Type: {error_details['error_type']}")
        print(f"Error Message: {error_details['error_message']}")
        print(f"Query Parameters:")
        print(f"  - Query: {error_details['query']}")
        print(f"  - Sorting Order: {error_details['sorting_order']}")
        print(f"  - Confidence Level: {error_details['confidence_level']}")
        print(f"  - Department IDs: {error_details['department_ids']}")
        print(f"  - Tech Sector IDs: {error_details['tech_sector_ids']}")
        print(f"  - Assignee IDs: {error_details['assignee_ids']}")
        print(f"  - Is CN Applied: {error_details['is_cn_applied']}")
        print("=========================")

        # Log the failed search
        log_entry = SearchLog(
            ip_address=request.remote_addr,
            headers=dict(request.headers),
            query=query,
            query_limit=page_size,
            confidence_level=confidence_level,
            status="error"
        )
        db.add(log_entry)
        db.commit()

        return jsonify({"error": f"Search error: {str(e)}"}), 500

    finally:
        db.close()
        print("DEBUG: Database session closed")

@app.route('/get_embedding', methods=['POST'])
async def run_get_embedding() -> List[float]:
    """Get embedding vector from OpenAI."""
    data = request.get_json()
    text = data.get('text')

    try:
        response = await get_embedding(text)
        return response
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536  # Return zero vector on error

@app.route('/update_embedding', methods=['GET'])
async def run_update_embedding():
    try:
        await update_embedding()
        return "Successfully updated embedding"
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return "Error updating embedding"

@app.route('/poly_assignees', methods=['GET'])
def get_poly_assignees():
    """
    Get all assignees where is_poly is TRUE.
    Returns a list of assignees with their details.
    """
    # Get a database session
    db = SessionLocal()

    try:
        # Query assignees where is_poly is TRUE and sort by assignee_id
        assignees = db.query(Assignees).filter(Assignees.is_poly == True).order_by(Assignees.assignee_id.asc()).all()

        # Format the results
        response = [
            {
                "assignee_id": assignee.assignee_id,
                "assignee_name": assignee.assignee_name,
                "is_poly": assignee.is_poly
            }
            for assignee in assignees
        ]

        return jsonify({
            "results": response,
            "total_count": len(response)
        })

    except Exception as e:
        return jsonify({"error": f"Error fetching poly assignees: {str(e)}"}), 500

    finally:
        db.close()

# Add a simple health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

# Add a new endpoint to get all tech sectors
@app.route('/tech_sectors', methods=['GET'])
def get_all_tech_sectors():
    """
    Get all unique tech sectors.
    Returns a list of tech sectors with their IDs and names.
    """
    db = SessionLocal()
    try:
        tech_sectors = db.query(TechSectors).order_by(TechSectors.tech_sector_name).all()
        response = [
            {
                "tech_sector_id": ts.tech_sector_id,
                "tech_sector_name": ts.tech_sector_name
            }
            for ts in tech_sectors
        ]
        return jsonify({
            "results": response,
            "total_count": len(response)
        })
    except Exception as e:
        return jsonify({"error": f"Error fetching tech sectors: {str(e)}"}), 500
    finally:
        db.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
