import os
import logging
from dotenv import load_dotenv
from typing import List
from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.postgres_embedding import PatentsList, SearchLog, get_embedding, update_embedding
import asyncio

# Create Flask app
load_dotenv()
app = Flask(__name__)

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
    - page_size: Number of results per page (default: 10)
    """
    # Get query parameters
    query = request.args.get('query')
    confidence_level = request.args.get('confidence_level', default=0.2, type=float)
    sorting_order = request.args.get('sorting_order', default='REL_DESC')
    current_page = request.args.get('current_page', default=1, type=int)
    page_size = request.args.get('page_size', default=10, type=int)

    # Validate confidence_level is between 0 and 1
    if confidence_level < 0 or confidence_level > 1:
        return jsonify({"error": "confidence_level must be between 0 and 1"}), 400

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Get a database session
    db = SessionLocal()

    try:
        # Generate embedding for the query
        query_embedding = asyncio.run(get_embedding(query))

        # Calculate similarity score expression
        similarity_score = (1 - PatentsList.embedding.cosine_distance(query_embedding)).label("similarity")

        # Base query with similarity score and DISTINCT on sys_id
        base_query = (
            db.query(
                PatentsList,
                similarity_score
            )
            .filter(PatentsList.embedding.is_not(None))
            .filter(similarity_score >= confidence_level)
        )

        # Apply sorting based on sorting_order
        if sorting_order == 'REL_DESC':
            base_query = base_query.order_by(similarity_score.desc())
        elif sorting_order == 'REL_ASC':
            base_query = base_query.order_by(similarity_score.asc())
        elif sorting_order == 'FSD_ASC':
            base_query = base_query.order_by(PatentsList.department.asc())
        elif sorting_order == 'FSD_DESC':
            base_query = base_query.order_by(PatentsList.department.desc())
        elif sorting_order == 'DATE_DESC':
            base_query = base_query.order_by(PatentsList.sys_id.desc())
        elif sorting_order == 'DATE_ASC':
            base_query = base_query.order_by(PatentsList.sys_id.asc())
        else:
            # Default to relevance descending if invalid sorting order
            base_query = base_query.order_by(similarity_score.desc())

        # Calculate total count for pagination
        total_count = base_query.count()

        # Apply pagination
        offset = (current_page - 1) * page_size
        results = base_query.offset(offset).limit(page_size).all()

        # Format the results
        response = []
        for patent, similarity in results:
            patent_dict = {
                "sys_id": patent.sys_id,
                "official_title": patent.official_title,
                "tech_sector": patent.tech_sector,
                "inventor": patent.inventor,
                "department": patent.department,
                "country_region": patent.country_region,
                "google_patent_link": patent.google_patent_link,
                "ai_summary": patent.ai_summary,
                "similarity": float(similarity),
                "is_tech": patent.is_tech,
                "ai_short_summary": patent.ai_short_summary
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
            }
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

# Add a simple health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
