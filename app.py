import os
from dotenv import load_dotenv
from typing import List
from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.postgres_embedding import PatentsList, get_embedding, update_embedding
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
    def __init__(self, sys_id, official_title, tech_sector=None, inventor=None, department=None, country_region=None, google_patent_link=None, ai_summary=None, similarity=None):
        self.sys_id = sys_id
        self.official_title = official_title
        self.tech_sector = tech_sector
        self.inventor = inventor
        self.department = department
        self.country_region = country_region
        self.google_patent_link = google_patent_link
        self.ai_summary = ai_summary
        self.similarity = similarity

@app.route('/search', methods=['GET'])
def search_patents():
    """
    Search for patents similar to the query text using vector embeddings.
    Returns a list of patents sorted by similarity.
    
    Query parameters:
    - query: The search query to find similar patents
    - limit: Maximum number of results to return (default: 10)
    - confidence_level: Minimum similarity score threshold (default: 0.0)
    """
    # Get query parameters
    query = request.args.get('query')
    limit = request.args.get('limit', default=20, type=int)
    confidence_level = request.args.get('confidence_level', default=0.2, type=float)
    
    # Validate confidence_level is between 0 and 1
    if confidence_level < 0 or confidence_level > 1:
        return jsonify({"error": "confidence_level must be between 0 and 1"}), 400
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    # Get a database session
    db = SessionLocal()
    
    try:
        # Generate embedding for the query
        # We need to run the async function in a synchronous context
        query_embedding = asyncio.run(get_embedding(query))
        
        # Calculate similarity score expression
        similarity_score = (1 - PatentsList.embedding.cosine_distance(query_embedding)).label("similarity")
        
        # Perform similarity search using cosine distance
        # The <-> operator in pgvector calculates cosine distance
        results = (
            db.query(
                PatentsList,
                similarity_score
            )
            .filter(PatentsList.embedding.is_not(None))
            # Apply confidence level filter directly in the query
            .filter(similarity_score >= confidence_level)
            .order_by(PatentsList.embedding.cosine_distance(query_embedding),
                      similarity_score.desc()
                      )
            .limit(limit)
            .all()
        )
        
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
                "similarity": float(similarity)  # Ensure it's a float for JSON serialization
            }
            response.append(patent_dict)
        
        return jsonify(response)
    
    except Exception as e:
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
