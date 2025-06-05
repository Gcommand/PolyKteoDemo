import os
import logging
from dotenv import load_dotenv
from typing import List, Tuple
from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
    # Get query parameters
    query = request.args.get('query')
    confidence_level = request.args.get('confidence_level', default=0.2, type=float)
    sorting_order = request.args.get('sorting_order', default='REL_DESC')
    current_page = request.args.get('current_page', default=1, type=int)
    page_size = request.args.get('page_size', default=12, type=int)
    
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
    print(f"Received parameters:")
    print(f"department_ids: {department_ids}")
    print(f"tech_sector_ids: {tech_sector_ids}")
    print(f"assignee_ids: {assignee_ids}")
    print(f"is_cn_applied: {is_cn_applied}")

    # Validate confidence_level is between 0 and 1
    if confidence_level < 0 or confidence_level > 1:
        return jsonify({"error": "confidence_level must be between 0 and 1"}), 400

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Detect query language
    query_lang = detect_language(query)
    print(f"Query language: {query_lang}")

    # Get a database session
    db = SessionLocal()

    try:
        # Generate embedding for the query
        query_embedding = asyncio.run(get_embedding(query))

        # Calculate similarity score expression
        similarity_score = (1 - PatentsList.embedding.cosine_distance(query_embedding)).label("similarity")

        # Base query with similarity score
        base_query = (
            db.query(
                PatentsList,
                similarity_score
            )
            .filter(PatentsList.embedding.is_not(None))
            .filter(similarity_score >= confidence_level)
        )

        # Add department filter if department_ids are provided
        if department_ids:
            base_query = (
                base_query
                .join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
                .filter(PatentDepartments.department_id.in_(department_ids))
            )

        # Add assignee filter if assignee_ids are provided
        if assignee_ids:
            base_query = (
                base_query
                .join(PatentAssignees, PatentsList.sys_id == PatentAssignees.patent_id)
                .filter(PatentAssignees.assignee_id.in_(assignee_ids))
            )

        # Add tech_sector filter if provided
        if tech_sector_ids:
            base_query = (
                base_query
                .join(PatentTechSectors, PatentsList.sys_id == PatentTechSectors.patent_sys_id)
                .filter(PatentTechSectors.tech_sector_id.in_(tech_sector_ids))
            )

        # Add is_cn_applied filter if provided
        if is_cn_applied is not None:
            base_query = base_query.filter(PatentsList.is_cn_applied == is_cn_applied)

        # Calculate total count for pagination using a subquery
        count_query = db.query(PatentsList.sys_id).distinct()
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

        # Apply sorting based on sorting_order
        if sorting_order == 'REL_DESC':
            base_query = base_query.order_by(similarity_score.desc(), PatentsList.sys_id)
        elif sorting_order == 'REL_ASC':
            base_query = base_query.order_by(similarity_score.asc(), PatentsList.sys_id)
        elif sorting_order == 'FSD_ASC':
            base_query = base_query.order_by(PatentsList.department.asc(), PatentsList.sys_id)
        elif sorting_order == 'FSD_DESC':
            base_query = base_query.order_by(PatentsList.department.desc(), PatentsList.sys_id)
        elif sorting_order == 'DATE_DESC':
            base_query = base_query.order_by(PatentsList.sys_id.desc())
        elif sorting_order == 'DATE_ASC':
            base_query = base_query.order_by(PatentsList.sys_id.asc())
        else:
            # Default to relevance descending if invalid sorting order
            base_query = base_query.order_by(similarity_score.desc(), PatentsList.sys_id)

        # Apply distinct after ordering
        base_query = base_query.distinct(PatentsList.sys_id)

        # Apply pagination
        offset = (current_page - 1) * page_size
        results = base_query.offset(offset).limit(page_size).all()

        # Format the results
        response = []
        for patent, similarity in results:
            # Get departments for this patent
            patent_departments = (
                db.query(Departments)
                .join(PatentDepartments, Departments.department_id == PatentDepartments.department_id)
                .filter(PatentDepartments.patent_id == patent.sys_id)
                .all()
            )
            
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
                "similarity": float(similarity),
                "is_tech": patent.is_tech,
                "is_cn_applied": patent.is_cn_applied,
                "ai_short_summary": chinese_short_summary,
                "query_language": query_lang
            }
            response.append(patent_dict)

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

        return jsonify({
            "results": response,
            "pagination": {
                "total_count": total_count,
                "current_page": current_page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            },
            "query_language": query_lang
        })

    except Exception as e:
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
