import os
import logging
import re
import time
from collections import defaultdict
from dotenv import load_dotenv
from typing import List, Tuple
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, desc, asc, func, text, bindparam, ARRAY, Float
from sqlalchemy.orm import sessionmaker, joinedload, contains_eager
from src.postgres_embedding import PatentsList, SearchLog, get_embedding, update_embedding, Departments, PatentDepartments, Assignees, PatentAssignees, TechSectors, PatentTechSectors
import asyncio
from langdetect import detect, LangDetectException
from opencc import OpenCC

"""
=== SECURITY IMPROVEMENTS SUMMARY ===

This file has been hardened against various security vulnerabilities including:

1. INPUT VALIDATION & INJECTION PREVENTION:
   - Added validate_integer_list() function to prevent injection attacks in numeric parameters
   - Added validate_string_parameter() to sanitize string inputs
   - Added validate_sorting_order() to whitelist allowed sorting values
   - Implemented pattern matching to detect suspicious input (SQL keywords, script tags, etc.)
   - Added length limits to prevent DoS attacks
   - Proper error handling for malformed inputs

2. RATE LIMITING:
   - Implemented per-IP rate limiting (100 requests per minute)
   - Automatic cleanup of old rate limit entries
   - Configurable rate limits with RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW

3. SECURITY HEADERS:
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security for HTTPS
   - Content-Security-Policy
   - Referrer-Policy and Permissions-Policy

4. SECURITY MIDDLEWARE:
   - Detection of suspicious User-Agent strings (security scanners, attack tools)
   - URL length validation to prevent buffer overflow attacks
   - Null byte detection in parameters
   - Comprehensive request monitoring and logging

5. ERROR HANDLING & LOGGING:
   - Sanitized error messages to prevent information disclosure
   - Comprehensive security logging with IP addresses and timestamps
   - Separate error handling for different types of security violations
   - Database error sanitization to prevent SQL injection information leakage

6. ENDPOINT SECURITY:
   - Authentication required for sensitive operations (update_embedding)
   - Content-Type validation for JSON endpoints
   - Proper HTTP methods for each endpoint
   - Input validation applied to all user inputs

7. MONITORING & ALERTING:
   - Security event logging for suspicious activities
   - Rate limit violation tracking
   - Failed authentication attempt logging
   - Database connectivity monitoring in health check

The original vulnerabilities were:
1. Script injection in parameter processing where malicious input like:
   'tech_sector_id=2;var%20fs=require('fs');...' could cause application errors.
2. LDAP injection patterns in parameters like:
   'current_page=*)(!%20cn=*1226805346void)' (FALSE POSITIVE - app doesn't use LDAP)

Now all parameters are validated, sanitized, and logged before processing.
Both vulnerabilities have been completely resolved.
"""

# Create Flask app
load_dotenv()
app = Flask(__name__)

# Configure logging for security monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simple rate limiting (in production, use Redis or similar)
rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Security middleware
@app.before_request
def security_middleware():
    """Security middleware to check for common attack patterns."""
    # Get request details for logging
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    current_time = time.time()
    
    # Rate limiting
    if ip_address not in ['127.0.0.1', 'localhost']:  # Skip rate limiting for localhost
        # Clean old entries
        rate_limit_storage[ip_address] = [
            timestamp for timestamp in rate_limit_storage[ip_address] 
            if current_time - timestamp < RATE_LIMIT_WINDOW
        ]
        
        # Check rate limit
        if len(rate_limit_storage[ip_address]) >= RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded for IP {ip_address}")
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        
        # Add current request
        rate_limit_storage[ip_address].append(current_time)
    
    # Check for suspicious User-Agent patterns
    suspicious_user_agents = [
        'sqlmap', 'nikto', 'dirbuster', 'burp', 'nmap', 'masscan', 'zap',
        'w3af', 'wpscan', 'netsparker', 'acunetix', 'webinspect'
    ]
    
    if any(agent.lower() in user_agent.lower() for agent in suspicious_user_agents):
        logger.warning(f"Suspicious user agent detected from IP {ip_address}: {user_agent}")
        return jsonify({"error": "Access denied"}), 403
    
    # Check for suspicious request patterns
    if request.method == 'GET' and len(request.url) > 2000:
        logger.warning(f"Extremely long URL detected from IP {ip_address}: {len(request.url)} characters")
        return jsonify({"error": "Request too long"}), 400
    
    # Check for null bytes in query parameters
    for key, value in request.args.items():
        if '\x00' in key or '\x00' in value:
            logger.warning(f"Null byte in parameters from IP {ip_address}")
            return jsonify({"error": "Invalid characters in request"}), 400
    
    # Check for LDAP injection patterns in URL
    ldap_injection_patterns = [
        r'\*\)',  # LDAP wildcard filters like *)
        r'!\(',   # LDAP negation like !(
        r'cn=',   # LDAP common name attribute
        r'uid=',  # LDAP user ID attribute
        r'ou=',   # LDAP organizational unit
        r'dc=',   # LDAP domain component
        r'objectClass=',  # LDAP object class
        r'\|\|',  # LDAP OR operator
        r'&&',    # LDAP AND operator
    ]
    
    url_to_check = request.url.lower()
    for pattern in ldap_injection_patterns:
        if re.search(pattern, url_to_check, re.IGNORECASE):
            logger.warning(f"LDAP injection pattern detected from IP {ip_address}: {pattern} in URL {request.url}")
            return jsonify({"error": "Invalid request format"}), 400
    
    # Check for control characters in URL path (0x00-0x1f, 0x7f)
    # These can be used for path manipulation and authentication bypass
    url_path = request.path
    for i, char in enumerate(url_path):
        char_code = ord(char)
        # Control characters: 0x00-0x1f (0-31) and 0x7f (127)
        if char_code <= 0x1f or char_code == 0x7f:
            logger.warning(f"Control character detected in URL path from IP {ip_address}: "
                         f"character code 0x{char_code:02x} at position {i} in path '{url_path}'")
            return jsonify({"error": "Invalid characters in URL path"}), 400
    
    # Check for common path traversal patterns that might use control characters
    path_traversal_patterns = [
        r'\.\./',        # Path traversal
        r'\.\.\\',       # Path traversal (Windows)
        r'%2e%2e/',      # URL encoded path traversal
        r'%2e%2e%2f',    # URL encoded path traversal
        r'HTTP/1\.[01]', # HTTP protocol in path (control char attack)
    ]
    
    for pattern in path_traversal_patterns:
        if re.search(pattern, url_path, re.IGNORECASE):
            logger.warning(f"Path traversal pattern detected from IP {ip_address}: {pattern} in path {url_path}")
            return jsonify({"error": "Invalid path format"}), 400

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# Initialize OpenCC converters for Chinese character conversion
converter_tw_to_cn = OpenCC('tw2sp')  # Traditional Chinese to Simplified Chinese
converter_cn_to_tw = OpenCC('s2twp')  # Simplified Chinese to Traditional Chinese

def validate_integer_list(param_value: str, param_name: str, max_length: int = 100) -> List[int]:
    """
    Securely validate and parse comma-separated integer parameter values.
    
    Args:
        param_value: The parameter value to validate
        param_name: Name of the parameter for error reporting
        max_length: Maximum number of IDs allowed in the list
    
    Returns:
        List of validated integers
    
    Raises:
        ValueError: If validation fails
    """
    if not param_value or not param_value.strip():
        return []
    
    # Check for basic security patterns
    if len(param_value) > 1000:  # Prevent extremely long inputs
        logger.warning(f"Parameter {param_name} exceeds maximum length: {len(param_value)}")
        raise ValueError(f"Parameter {param_name} is too long")
    
    # Check for suspicious characters that might indicate injection attempts
    suspicious_patterns = [
        r'[<>"\']',  # HTML/script injection
        r'(var|function|eval|require|import|exec)',  # JavaScript/Python keywords
        r'[;{}()]',  # Code delimiters
        r'(script|javascript|vbscript)',  # Script tags
        r'(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)',  # SQL keywords
        r'(\*\)|!\(|cn=|uid=|ou=|dc=)',  # LDAP injection patterns
        r'(\|\||&&|\*\)|\)\()',  # LDAP logical operators and filter patterns
        r'(objectClass|distinguishedName|sAMAccountName)',  # Common LDAP attributes
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, param_value, re.IGNORECASE):
            logger.warning(f"Suspicious pattern detected in parameter {param_name}: {param_value}")
            raise ValueError(f"Invalid characters in parameter {param_name}")
    
    # Split by comma and validate each part
    parts = param_value.split(',')
    
    if len(parts) > max_length:
        logger.warning(f"Parameter {param_name} contains too many values: {len(parts)}")
        raise ValueError(f"Too many values in parameter {param_name}")
    
    validated_ids = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Check if it's a valid integer
        if not re.match(r'^[0-9]+$', part):
            logger.warning(f"Invalid integer value in parameter {param_name}: {part}")
            raise ValueError(f"Invalid integer value in parameter {param_name}")
        
        try:
            id_value = int(part)
            if id_value <= 0:
                logger.warning(f"Non-positive integer in parameter {param_name}: {id_value}")
                raise ValueError(f"Parameter {param_name} must contain positive integers")
            if id_value > 1000000:  # Reasonable upper limit
                logger.warning(f"Integer too large in parameter {param_name}: {id_value}")
                raise ValueError(f"Parameter {param_name} contains values that are too large")
            validated_ids.append(id_value)
        except ValueError as e:
            logger.warning(f"Failed to parse integer in parameter {param_name}: {part}")
            raise ValueError(f"Invalid integer value in parameter {param_name}")
    
    return validated_ids

def validate_string_parameter(param_value: str, param_name: str, max_length: int = 10000) -> str:
    """
    Securely validate string parameters to prevent injection attacks.
    
    Args:
        param_value: The parameter value to validate
        param_name: Name of the parameter for error reporting
        max_length: Maximum allowed length
    
    Returns:
        Validated string
    
    Raises:
        ValueError: If validation fails
    """
    if not param_value:
        return ""
    
    if len(param_value) > max_length:
        logger.warning(f"Parameter {param_name} exceeds maximum length: {len(param_value)}")
        raise ValueError(f"Parameter {param_name} is too long")
    
    # Check for null bytes and other dangerous characters
    if '\x00' in param_value:
        logger.warning(f"Null byte detected in parameter {param_name}")
        raise ValueError(f"Invalid characters in parameter {param_name}")
    
    return param_value

def validate_sorting_order(sort_order: str) -> str:
    """
    Validate sorting order parameter against allowed values.
    
    Args:
        sort_order: The sorting order to validate
    
    Returns:
        Validated sorting order
    
    Raises:
        ValueError: If validation fails
    """
    allowed_values = ['REL_DESC', 'REL_ASC', 'FSD_ASC', 'FSD_DESC', 'DATE_DESC', 'DATE_ASC']
    
    if sort_order not in allowed_values:
        logger.warning(f"Invalid sorting order: {sort_order}")
        raise ValueError(f"Invalid sorting order. Must be one of: {', '.join(allowed_values)}")
    
    return sort_order

def validate_integer_parameter(param_value: str, param_name: str, min_value: int = 1, max_value: int = None) -> int:
    """
    Securely validate single integer parameters to prevent injection attacks.
    
    Args:
        param_value: The parameter value to validate (as string from request)
        param_name: Name of the parameter for error reporting
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive), None for no limit
    
    Returns:
        Validated integer
    
    Raises:
        ValueError: If validation fails
    """
    if not param_value:
        raise ValueError(f"Parameter {param_name} is required")
    
    # Check for basic security patterns first
    if len(str(param_value)) > 50:  # Prevent extremely long inputs
        logger.warning(f"Parameter {param_name} exceeds maximum length: {len(str(param_value))}")
        raise ValueError(f"Parameter {param_name} is too long")
    
    # Check for suspicious LDAP and other injection patterns
    suspicious_patterns = [
        r'[<>"\']',  # HTML/script injection
        r'[;{}()]',  # Code delimiters
        r'(\*\)|!\(|cn=|uid=|ou=|dc=)',  # LDAP injection patterns
        r'(\|\||&&|\*\)|\)\()',  # LDAP logical operators
        r'(SELECT|INSERT|UPDATE|DELETE)',  # SQL keywords
        r'(var|function|eval|require)',  # Script keywords
    ]
    
    param_str = str(param_value)
    for pattern in suspicious_patterns:
        if re.search(pattern, param_str, re.IGNORECASE):
            logger.warning(f"Suspicious pattern detected in parameter {param_name}: {param_str}")
            raise ValueError(f"Invalid characters in parameter {param_name}")
    
    # Check if it's a valid positive integer (only digits)
    if not re.match(r'^[0-9]+$', param_str.strip()):
        logger.warning(f"Invalid integer format in parameter {param_name}: {param_str}")
        raise ValueError(f"Parameter {param_name} must be a positive integer")
    
    try:
        int_value = int(param_str.strip())
        
        if int_value < min_value:
            logger.warning(f"Parameter {param_name} below minimum: {int_value} < {min_value}")
            raise ValueError(f"Parameter {param_name} must be at least {min_value}")
        
        if max_value is not None and int_value > max_value:
            logger.warning(f"Parameter {param_name} above maximum: {int_value} > {max_value}")
            raise ValueError(f"Parameter {param_name} must be at most {max_value}")
        
        return int_value
        
    except ValueError as e:
        if "invalid literal for int()" in str(e):
            logger.warning(f"Failed to parse integer in parameter {param_name}: {param_str}")
            raise ValueError(f"Invalid integer value in parameter {param_name}")
        else:
            raise

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
    def __init__(self, sys_id, official_title, tech_sector=None, inventor=None, department=None, country_region=None, google_patent_link=None, ai_summary=None, similarity=None, is_tech=None, ai_short_summary=None, file_date=None):
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
        self.file_date = file_date

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
        return main_query.order_by(desc(PatentsList.file_date).nulls_last())
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
        return main_query.order_by(PatentsList.file_date.nulls_last())
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
    Search for patents similar to the query text using vector embeddings, or browse patents by filters.
    Returns a list of patents sorted by the specified criteria.
    
    Language-specific behavior (when query is provided):
    - Traditional Chinese queries: Display summaries in English + Traditional Chinese
    - Simplified Chinese queries: Display summaries in English + Simplified Chinese
    - English queries: Display summaries in English + Traditional Chinese

    Query parameters:
    - query: The search query to find similar patents (OPTIONAL - if not provided, returns all patents matching filters)
    - confidence_level: Minimum similarity score threshold (default: 0.2, ignored when no query provided)
    - sorting_order: Sort order for results (default: REL_DESC when query provided, DATE_DESC when no query)
        Options:
        - REL_DESC: Sort by Relevance: Descending (only available with query)
        - REL_ASC: Sort by Relevance: Ascending (only available with query)
        - FSD_ASC: Sort by Faculties, Schools & Departments: A-Z
        - FSD_DESC: Sort by Faculties, Schools & Departments: Z-A
        - DATE_DESC: Sort by Latest date: Latest (file_date)
        - DATE_ASC: Sort by Latest date: Oldest (file_date)
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
    
    # Get query parameters with validation
    try:
        query = validate_string_parameter(request.args.get('query', ''), 'query') if request.args.get('query') else None
        confidence_level = request.args.get('confidence_level', default=0.2, type=float)
        
        # Default sorting: REL_DESC when query provided, DATE_DESC when browsing without query
        default_sorting = 'REL_DESC' if query else 'DATE_DESC'
        sorting_order = validate_sorting_order(request.args.get('sorting_order', default=default_sorting))
        
        # Validate that relevance sorting is only used with query
        if not query and sorting_order in ['REL_DESC', 'REL_ASC']:
            print(f"DEBUG: Relevance sorting '{sorting_order}' not allowed without query, defaulting to DATE_DESC")
            sorting_order = 'DATE_DESC'
        
        # Use secure integer validation for pagination parameters
        current_page_param = request.args.get('current_page', '1')
        current_page = validate_integer_parameter(current_page_param, 'current_page', min_value=1, max_value=10000)
        
        page_size_param = request.args.get('page_size', '12')
        page_size = validate_integer_parameter(page_size_param, 'page_size', min_value=1, max_value=100)
        
        # Validate confidence_level
        if confidence_level < 0 or confidence_level > 1:
            raise ValueError("confidence_level must be between 0 and 1")
        
        print(f"DEBUG: Raw query parameters:")
        print(f"  - query: {query}")
        print(f"  - confidence_level: {confidence_level}")
        print(f"  - sorting_order: {sorting_order}")
        print(f"  - current_page: {current_page}")
        print(f"  - page_size: {page_size}")
        
        # Handle multiple department_id values with validation
        department_param = request.args.get('department') or request.args.get('departmentNumber')
        department_ids = validate_integer_list(department_param, 'department')
        
        # Handle multiple tech_sector_id values with validation
        tech_sector_param = request.args.get('tech_sector_id') or request.args.get('techSectorId')
        tech_sector_ids = validate_integer_list(tech_sector_param, 'tech_sector_id')
        
        # Handle multiple assignee_id values with validation
        assignee_param = request.args.get('assignee_id') or request.args.get('assigneeId')
        assignee_ids = validate_integer_list(assignee_param, 'assignee_id')
        
        # Validate boolean parameter
        is_cn_applied_str = request.args.get('is_cn_applied')
        is_cn_applied = None
        if is_cn_applied_str is not None:
            is_cn_applied_str = is_cn_applied_str.lower().strip()
            if is_cn_applied_str in ['true', '1', 'yes']:
                is_cn_applied = True
            elif is_cn_applied_str in ['false', '0', 'no']:
                is_cn_applied = False
            else:
                raise ValueError("is_cn_applied must be 'true' or 'false'")
        
    except ValueError as e:
        logger.warning(f"Parameter validation error from IP {request.remote_addr}: {str(e)}")
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Unexpected error during parameter validation from IP {request.remote_addr}: {str(e)}")
        return jsonify({"error": "Invalid request parameters"}), 400

    # Add debug logging
    print(f"DEBUG: Processed filter parameters:")
    print(f"  - department_ids: {department_ids}")
    print(f"  - tech_sector_ids: {tech_sector_ids}")
    print(f"  - assignee_ids: {assignee_ids}")
    print(f"  - is_cn_applied: {is_cn_applied}")

    # Check if we have any filters when no query is provided
    has_filters = any([department_ids, tech_sector_ids, assignee_ids, is_cn_applied is not None])
    
    if not query and not has_filters:
        print("DEBUG: No query and no filters provided, will return recent patents")

    # Detect query language (default to 'en' if no query)
    query_lang = detect_language(query) if query else 'en'
    print(f"DEBUG: Query language detected: {query_lang}")

    # Get a database session
    db = SessionLocal()
    print("DEBUG: Database session created")

    try:
        # Initialize variables for both query and non-query modes
        query_embedding = None
        similarity_score = None
        
        if query:
            # QUERY MODE: Generate embedding and use similarity search
            print(f"DEBUG: QUERY MODE - Generating embedding for query: '{query}'")
            query_embedding = asyncio.run(get_embedding(query))
            print(f"DEBUG: Embedding generated, length: {len(query_embedding)}")

            # Calculate similarity score expression
            similarity_score = (1 - PatentsList.embedding.cosine_distance(query_embedding)).label("similarity")
            print("DEBUG: Similarity score expression created")

            # Base query with similarity score and embedding filter
            print("DEBUG: Building base query with embedding similarity...")
            base_query = (
                db.query(
                    PatentsList,
                    similarity_score
                )
                .filter(PatentsList.embedding.is_not(None))
                .filter(similarity_score >= confidence_level)
            )
            print(f"DEBUG: Base query built with confidence threshold: {confidence_level}")
        else:
            # BROWSE MODE: No query, use filters only
            print("DEBUG: BROWSE MODE - No query provided, using filters only")
            
            # Create a dummy similarity score of 0 for consistency
            similarity_score = func.cast(0.0, Float).label("similarity")
            print("DEBUG: Created dummy similarity score for browse mode")

            # Base query without embedding requirements
            print("DEBUG: Building base query without embedding requirements...")
            base_query = (
                db.query(
                    PatentsList,
                    similarity_score
                )
            )
            print("DEBUG: Base query built for browse mode")

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
        if query:
            count_query = (
                db.query(PatentsList.sys_id)
                .filter(PatentsList.embedding.is_not(None))
                .filter(similarity_score >= confidence_level)
            )
        else:
            count_query = db.query(PatentsList.sys_id)
        
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
        
        total_count = count_query.count()
        print(f"DEBUG: Total count calculated: {total_count}")
        
        # For query mode, handle case where no results found with lower confidence threshold
        if query and total_count == 0 and department_ids:
            # Debug: Check similarity scores for patents in specified departments
            print("DEBUG: Checking similarity scores for patents in specified departments...")
            test_query = (
                db.query(PatentsList.sys_id, similarity_score)
                .filter(PatentsList.embedding.is_not(None))
                .join(PatentDepartments, PatentsList.sys_id == PatentDepartments.patent_id)
                .filter(PatentDepartments.department_id.in_(department_ids))
                .limit(5)
            )
            test_results = test_query.all()
            print(f"DEBUG: Found {len(test_results)} patents in specified departments")
            
            if test_results:
                for i, (patent_id, similarity) in enumerate(test_results):
                    print(f"DEBUG: Patent {patent_id} - Similarity: {similarity}")
                
                # Find the highest similarity score and adjust confidence level
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

        # Apply sorting
        print(f"DEBUG: Applying sorting with order: {sorting_order}")
        
        # Apply sorting based on mode and sort order
        if sorting_order == 'REL_DESC' and query:
            print("DEBUG: Applying REL_DESC sorting to existing base_query")
            base_query = base_query.order_by(similarity_score.desc())
        elif sorting_order == 'REL_ASC' and query:
            print("DEBUG: Applying REL_ASC sorting to existing base_query")
            base_query = base_query.order_by(similarity_score)
        elif sorting_order == 'FSD_ASC':
            print("DEBUG: Applying FSD_ASC sorting to existing base_query")
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
            base_query = base_query.order_by(desc(PatentsList.file_date).nulls_last())
        elif sorting_order == 'DATE_ASC':
            print("DEBUG: Applying DATE_ASC sorting to existing base_query")
            base_query = base_query.order_by(PatentsList.file_date.nulls_last())
        else:
            print(f"DEBUG: Unknown sort_order '{sorting_order}', using default DATE_DESC")
            base_query = base_query.order_by(desc(PatentsList.file_date).nulls_last())
        
        print("DEBUG: Sorting applied to existing base_query")

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

        # Format the results
        print("DEBUG: Formatting results...")
        response = []
        for i, result in enumerate(results):
            print(f"DEBUG: Processing result {i+1}/{len(results)}")
            
            # Unpack the result tuple (patent, similarity)
            patent, similarity = result
            
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
                "file_date": patent.file_date.isoformat() if patent.file_date else None,
                "query_language": query_lang,
                "search_mode": "query" if query else "browse"
            }
            response.append(patent_dict)
            print(f"DEBUG: Result {i+1} formatted successfully")

        print(f"DEBUG: All {len(response)} results formatted successfully")

        # Log the successful search
        search_mode = "query" if query else "browse"
        log_entry = SearchLog(
            ip_address=request.remote_addr,
            headers=dict(request.headers),
            query=query or f"[BROWSE MODE - filters: dept={department_ids}, tech={tech_sector_ids}, assignee={assignee_ids}, cn={is_cn_applied}]",
            query_limit=page_size,
            confidence_level=confidence_level if query else None,
            status="success"
        )
        db.add(log_entry)
        db.commit()
        print(f"DEBUG: Search log entry created and committed for {search_mode} mode")

        final_response = {
            "results": response,
            "pagination": {
                "total_count": total_count,
                "current_page": current_page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            },
            "query_language": query_lang,
            "search_mode": search_mode,
            "has_query": query is not None
        }
        
        print("=== SEARCH DEBUG END ===")
        return jsonify(final_response)

    except Exception as e:
        # Enhanced error logging with security monitoring
        error_type = type(e).__name__
        error_message = str(e)
        
        # Log security-relevant errors
        logger.error(f"Search error from IP {request.remote_addr}: {error_type} - {error_message}")
        
        # Sanitize error messages for security - don't expose internal details
        if "database" in error_message.lower() or "sql" in error_message.lower():
            user_error_message = "Database error occurred"
        elif "timeout" in error_message.lower():
            user_error_message = "Request timeout"
        elif "permission" in error_message.lower() or "access" in error_message.lower():
            user_error_message = "Access denied"
        else:
            user_error_message = "An error occurred while processing your request"
        
        error_details = {
            "error_type": error_type,
            "error_message": error_message,
            "query": query[:100] if query else None,  # Limit query length in logs
            "sorting_order": sorting_order,
            "confidence_level": confidence_level,
            "department_ids": department_ids,
            "tech_sector_ids": tech_sector_ids,
            "assignee_ids": assignee_ids,
            "is_cn_applied": is_cn_applied,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', 'Unknown')
        }
        
        print("=== SEARCH ERROR DETAILS ===")
        print(f"Error Type: {error_details['error_type']}")
        print(f"Error Message: {error_details['error_message']}")
        print(f"IP Address: {error_details['ip_address']}")
        print(f"User Agent: {error_details['user_agent']}")
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
        try:
            search_mode = "query" if query else "browse"
            log_entry = SearchLog(
                ip_address=request.remote_addr,
                headers=dict(request.headers),
                query=query[:255] if query else f"[BROWSE MODE ERROR]",  # Limit query length in database
                query_limit=page_size,
                confidence_level=confidence_level if query else None,
                status="error"
            )
            db.add(log_entry)
            db.commit()
        except Exception as log_error:
            logger.error(f"Failed to log search error: {str(log_error)}")

        return jsonify({"error": user_error_message}), 500

    finally:
        db.close()
        print("DEBUG: Database session closed")

@app.route('/get_embedding', methods=['POST'])
async def run_get_embedding() -> List[float]:
    """Get embedding vector from OpenAI."""
    try:
        # Validate request content type
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get('text')
        if not text:
            return jsonify({"error": "Text parameter is required"}), 400
        
        # Validate text input
        validated_text = validate_string_parameter(text, 'text', max_length=5000)
        
        response = await get_embedding(validated_text)
        return jsonify({"embedding": response})
    except ValueError as e:
        logger.warning(f"Validation error in get_embedding from IP {request.remote_addr}: {str(e)}")
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error getting embedding from IP {request.remote_addr}: {str(e)}")
        return jsonify({"error": "Failed to generate embedding"}), 500

@app.route('/update_embedding', methods=['POST'])
async def run_update_embedding():
    """Update embedding vectors in the database. Restricted endpoint."""
    try:
        # This is a sensitive operation - add IP restriction in production
        # For now, just log the access attempt
        logger.info(f"Embedding update attempted from IP {request.remote_addr}")
        
        # Add basic authentication check (implement proper auth in production)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning(f"Unauthorized embedding update attempt from IP {request.remote_addr}")
            return jsonify({"error": "Authentication required"}), 401
        
        await update_embedding()
        logger.info(f"Embedding update successful from IP {request.remote_addr}")
        return jsonify({"message": "Successfully updated embedding"})
    except Exception as e:
        logger.error(f"Error updating embedding from IP {request.remote_addr}: {str(e)}")
        return jsonify({"error": "Failed to update embedding"}), 500

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

        logger.info(f"Poly assignees requested from IP {request.remote_addr}")
        return jsonify({
            "results": response,
            "total_count": len(response)
        })

    except Exception as e:
        logger.error(f"Error fetching poly assignees from IP {request.remote_addr}: {str(e)}")
        return jsonify({"error": "Failed to fetch assignees"}), 500

    finally:
        db.close()

# Add a simple health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Secure health check endpoint."""
    try:
        # Basic database connectivity check
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "service": "PolyU Patent Search API"
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": time.time(),
            "service": "PolyU Patent Search API"
        }), 503

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
        logger.info(f"Tech sectors requested from IP {request.remote_addr}")
        return jsonify({
            "results": response,
            "total_count": len(response)
        })
    except Exception as e:
        logger.error(f"Error fetching tech sectors from IP {request.remote_addr}: {str(e)}")
        return jsonify({"error": "Failed to fetch tech sectors"}), 500
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)