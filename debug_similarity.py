#!/usr/bin/env python3
"""
Diagnostic tool to investigate low similarity scores in patent search.
This script helps identify whether the issue is with:
1. Embedding quality/content
2. Similarity calculation logic
3. Query vs content mismatch
"""

import numpy as np
from src.postgres_embedding import PatentsList, session
from sqlalchemy import func
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors (0-1 scale)"""
    if vec1 is None or vec2 is None or len(vec1) == 0 or len(vec2) == 0:
        return 0.0
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def analyze_embedding_stats():
    """Analyze basic statistics about embeddings in the database"""
    logger.info("=== EMBEDDING STATISTICS ===")
    
    # Count total patents and those with embeddings
    total_patents = session.query(PatentsList).count()
    patents_with_embeddings = session.query(PatentsList).filter(PatentsList.embedding.isnot(None)).count()
    
    logger.info(f"Total patents: {total_patents}")
    logger.info(f"Patents with embeddings: {patents_with_embeddings}")
    logger.info(f"Coverage: {patents_with_embeddings/total_patents*100:.1f}%")
    
    # Sample some embeddings to check their properties
    sample_patents = session.query(PatentsList).filter(
        PatentsList.embedding.isnot(None),
        PatentsList.is_tech == False  # Focus on non-tech patents as mentioned
    ).limit(10).all()
    
    if sample_patents:
        logger.info("\n=== SAMPLE EMBEDDING ANALYSIS ===")
        for i, patent in enumerate(sample_patents):
            if patent.embedding is not None and len(patent.embedding) > 0:
                embedding = np.array(patent.embedding)
                logger.info(f"Patent {patent.sys_id}:")
                logger.info(f"  Title: {patent.official_title[:100]}...")
                logger.info(f"  Embedding shape: {embedding.shape}")
                logger.info(f"  Embedding norm: {np.linalg.norm(embedding):.6f}")
                logger.info(f"  Mean value: {np.mean(embedding):.6f}")
                logger.info(f"  Std deviation: {np.std(embedding):.6f}")
                logger.info(f"  Min value: {np.min(embedding):.6f}")
                logger.info(f"  Max value: {np.max(embedding):.6f}")
                logger.info(f"  Is tech: {patent.is_tech}")
                print()

def test_similarity_with_sample_query(query_text="machine learning artificial intelligence"):
    """Test similarity calculation with a sample query"""
    logger.info(f"=== TESTING SIMILARITY WITH QUERY: '{query_text}' ===")
    
    # For this test, we'll use a simple approach - create a dummy embedding
    # In real scenario, you'd want to generate the embedding using the same model
    # that was used for the patents
    
    # Get some patents to test against
    sample_patents = session.query(PatentsList).filter(
        PatentsList.embedding.isnot(None),
        PatentsList.is_tech == False
    ).limit(5).all()
    
    if not sample_patents:
        logger.error("No patents with embeddings found!")
        return
    
    # Use the first patent's embedding as a "query" for testing
    query_patent = sample_patents[0]
    query_embedding = np.array(query_patent.embedding)
    
    logger.info(f"Using Patent {query_patent.sys_id} embedding as query")
    logger.info(f"Query patent title: {query_patent.official_title[:100]}...")
    
    logger.info("\n=== SIMILARITY RESULTS ===")
    
    for patent in sample_patents:
        if patent.embedding is not None and len(patent.embedding) > 0:
            patent_embedding = np.array(patent.embedding)
            
            # Calculate similarity using our function
            similarity_python = cosine_similarity(query_embedding, patent_embedding)
            
            # Calculate using PostgreSQL's method (1 - cosine_distance)
            cosine_distance = np.dot(query_embedding, patent_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(patent_embedding)
            )
            similarity_postgres = 1 - (1 - cosine_distance)  # This should be the same as cosine_distance
            
            logger.info(f"Patent {patent.sys_id}:")
            logger.info(f"  Title: {patent.official_title[:80]}...")
            logger.info(f"  Python similarity: {similarity_python:.6f}")
            logger.info(f"  PostgreSQL-style: {similarity_postgres:.6f}")
            logger.info(f"  Difference: {abs(similarity_python - similarity_postgres):.8f}")
            print()

def test_actual_query_similarity(query_text="artificial intelligence machine learning"):
    """Test with an actual query to see what similarities we get"""
    logger.info(f"=== TESTING WITH ACTUAL QUERY TEXT: '{query_text}' ===")
    
    # Note: This would require the actual embedding generation logic
    # For now, we'll simulate by using a patent embedding that might be related
    
    # Find patents that might be related to the query
    related_patents = session.query(PatentsList).filter(
        PatentsList.embedding.isnot(None),
        PatentsList.is_tech == False,
        PatentsList.official_title.ilike(f'%{query_text.split()[0]}%')
    ).limit(3).all()
    
    if not related_patents:
        logger.info("No patents found with title matching query terms")
        # Fall back to any patents
        related_patents = session.query(PatentsList).filter(
            PatentsList.embedding.isnot(None),
            PatentsList.is_tech == False
        ).limit(3).all()
    
    if related_patents:
        logger.info("Found potentially related patents:")
        for patent in related_patents:
            logger.info(f"  Patent {patent.sys_id}: {patent.official_title[:100]}...")
    
    # Test self-similarity (should be close to 1.0)
    if related_patents and len(related_patents) > 0:
        test_patent = related_patents[0]
        if test_patent.embedding is not None:
            embedding = np.array(test_patent.embedding)
            self_similarity = cosine_similarity(embedding, embedding)
            logger.info(f"\nSelf-similarity test for Patent {test_patent.sys_id}: {self_similarity:.6f}")
            
            if self_similarity < 0.99:
                logger.warning("⚠️  Self-similarity is unexpectedly low! This suggests an issue with the similarity calculation.")
            else:
                logger.info("✓ Self-similarity looks good")

def check_database_similarity_function():
    """Test PostgreSQL's cosine_distance function directly"""
    logger.info("=== TESTING DATABASE SIMILARITY FUNCTION ===")
    
    # Get a patent with embedding
    patent = session.query(PatentsList).filter(
        PatentsList.embedding.isnot(None),
        PatentsList.is_tech == False
    ).first()
    
    if not patent or patent.embedding is None:
        logger.error("No patent with embedding found!")
        return
    
    query_embedding = patent.embedding
    
    # Test database cosine_distance function
    similar_patents = session.query(
        PatentsList.sys_id,
        PatentsList.official_title,
        (1 - PatentsList.embedding.cosine_distance(query_embedding)).label('similarity')
    ).filter(
        PatentsList.embedding.isnot(None),
        PatentsList.is_tech == False
    ).order_by(
        (1 - PatentsList.embedding.cosine_distance(query_embedding)).desc()
    ).limit(5).all()
    
    logger.info(f"Using Patent {patent.sys_id} as query")
    logger.info("Top 5 similar patents from database:")
    
    for result in similar_patents:
        sys_id, title, similarity = result
        logger.info(f"  Patent {sys_id}: {similarity:.6f} - {title[:80]}...")

if __name__ == "__main__":
    print("🔍 Starting Patent Similarity Diagnostic Tool")
    print("=" * 60)
    
    try:
        # Run all diagnostic tests
        analyze_embedding_stats()
        print("\n" + "=" * 60)
        
        test_similarity_with_sample_query()
        print("\n" + "=" * 60)
        
        test_actual_query_similarity()
        print("\n" + "=" * 60)
        
        check_database_similarity_function()
        print("\n" + "=" * 60)
        
        print("🏁 Diagnostic complete!")
        
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close() 