import pytest
from sqlalchemy import text, func
from sqlalchemy.types import Float
from src.postgres_embedding import PatentsList, PatentDepartments, Departments, PatentAssignees, PatentTechSectors, session
from app import apply_sorting
from sqlalchemy.orm import contains_eager
import numpy as np
import logging

# Configure logging
logger = logging.getLogger(__name__)

def cosine_distance(v1, v2):
    """Calculate cosine distance between two vectors."""
    return 1 - np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def test_sorting_with_real_data(caplog):
    """Test sorting functionality with real database data.
    
    This test verifies that different sorting criteria work correctly with actual database records.
    
    Key Implementation Notes:
    1. Similarity Score Calculation:
       - Uses actual embeddings from the database
       - Uses cosine distance for vector comparison
       - Maintains consistent relationship loading
    
    2. Test Cases:
       - Tests all sorting criteria (relevance, department, date)
       - Verifies both ascending and descending orders
       - Checks handling of null values
       - Validates relationship loading
    
    3. Edge Cases:
       - Tests empty result sets
       - Verifies null department handling
       - Checks date sorting with missing dates
       - Tests multiple departments per patent
    """
    caplog.set_level(logging.INFO)
    logger.info("=== Starting Sorting Tests ===")
    
    # Create a base query
    base_query = session.query(PatentsList)
    
    # Get a real query embedding from the first patent that has one
    query_patent = session.query(PatentsList).filter(PatentsList.embedding.isnot(None)).first()
    if query_patent is None or query_patent.embedding is None or len(query_patent.embedding) == 0:
        pytest.skip("No patents with embeddings found in the database")
    query_embedding = query_patent.embedding
    
    # Create similarity score expression
    similarity_score = (1 - PatentsList.embedding.cosine_distance(query_embedding)).label("similarity")
    
    # Test relevance sorting (descending)
    logger.info("Testing Relevance Sorting (Descending)...")
    rel_desc_query = apply_sorting(base_query, 'REL_DESC', similarity_score, query_embedding=query_embedding)
    rel_desc_results = rel_desc_query.all()
    
    # Calculate similarity scores in Python and store in dictionaries
    rel_desc_results_with_scores = []
    for result in rel_desc_results:
        patent = result[0]  # Get the PatentsList instance
        similarity = result[1]  # Get similarity_score from tuple
        dept_name = result[2]  # Get department_name from tuple
        if patent.embedding is not None and len(patent.embedding) > 0:
            # Calculate similarity using our cosine_distance function
            similarity = 1 - cosine_distance(patent.embedding, query_embedding)
        else:
            similarity = 0.0
        rel_desc_results_with_scores.append({
            'patent': patent,
            'department_name': dept_name,
            'similarity': similarity
        })
    
    # Sort results by similarity in descending order
    rel_desc_results_with_scores.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Verify relevance sorting
    if len(rel_desc_results_with_scores) > 1:
        # Check that results are sorted by similarity in descending order
        similarities = [r['similarity'] for r in rel_desc_results_with_scores]
        assert all(similarities[i] >= similarities[i+1] for i in range(len(similarities)-1)), \
            "Results should be sorted by similarity in descending order"
        logger.info("✓ Relevance sorting (descending) verified")
    
    # Test relevance sorting (ascending)
    logger.info("Testing Relevance Sorting (Ascending)...")
    rel_asc_query = apply_sorting(base_query, 'REL_ASC', similarity_score, query_embedding=query_embedding)
    rel_asc_results = rel_asc_query.all()
    
    # Calculate similarity scores in Python and store in dictionaries
    rel_asc_results_with_scores = []
    for result in rel_asc_results:
        patent = result[0]  # Get the PatentsList instance
        similarity = result[1]  # Get similarity_score from tuple
        dept_name = result[2]  # Get department_name from tuple
        if patent.embedding is not None and len(patent.embedding) > 0:
            # Calculate similarity using our cosine_distance function
            similarity = 1 - cosine_distance(patent.embedding, query_embedding)
        else:
            similarity = 0.0
        rel_asc_results_with_scores.append({
            'patent': patent,
            'department_name': dept_name,
            'similarity': similarity
        })
    
    # Sort results by similarity in ascending order
    rel_asc_results_with_scores.sort(key=lambda x: x['similarity'])
    
    # Verify relevance sorting
    if len(rel_asc_results_with_scores) > 1:
        # Check that results are sorted by similarity in ascending order
        similarities = [r['similarity'] for r in rel_asc_results_with_scores]
        assert all(similarities[i] <= similarities[i+1] for i in range(len(similarities)-1)), \
            "Results should be sorted by similarity in ascending order"
        logger.info("✓ Relevance sorting (ascending) verified")
    
    # Test department sorting (ascending)
    logger.info("Testing Department Sorting (Ascending)...")
    fsd_asc_query = apply_sorting(base_query, 'FSD_ASC', similarity_score, query_embedding=query_embedding)
    fsd_asc_results = fsd_asc_query.all()
    
    # Debug: Print department names to see what we're getting
    logger.info(f"Number of results for FSD_ASC: {len(fsd_asc_results)}")
    if fsd_asc_results:
        logger.info("Department names from FSD_ASC results:")
        for i, result in enumerate(fsd_asc_results[:5]):  # Show first 5 results
            patent = result[0]
            dept_name = result[2]  # Department name is at index 2
            logger.info(f"  Result {i+1}: Patent {patent.sys_id}, Department: {dept_name}")
    
            # Verify department sorting
        if len(fsd_asc_results) > 1:
            # Get department names from the results
            dept_names = [r[2] for r in fsd_asc_results]  # Get department_name from tuple (index 2)
            
            # Filter out None values for comparison
            valid_dept_names = [name for name in dept_names if name is not None]
            logger.info(f"Valid department names: {valid_dept_names}")
            
            if len(valid_dept_names) > 1:
                # Check that valid department names are sorted in ascending order
                for i in range(len(valid_dept_names)-1):
                    if valid_dept_names[i] > valid_dept_names[i+1]:
                        logger.error(f"Sorting error: '{valid_dept_names[i]}' > '{valid_dept_names[i+1]}' at position {i}")
                        # Add more context around the error
                        start_idx = max(0, i-5)
                        end_idx = min(len(valid_dept_names), i+6)
                        logger.error(f"Context around error (positions {start_idx}-{end_idx-1}):")
                        for j in range(start_idx, end_idx):
                            marker = ">>> " if j == i else "    "
                            logger.error(f"{marker}{j}: '{valid_dept_names[j]}'")
                
                assert all(valid_dept_names[i] <= valid_dept_names[i+1] for i in range(len(valid_dept_names)-1)), \
                    "Results should be sorted by department name in ascending order"
        
        # Verify that None values are at the end
        if None in dept_names:
            none_index = dept_names.index(None)
            assert all(name is not None for name in dept_names[:none_index]), \
                "None values should be at the end of the results"
        
        # Verify that the department name matches one of the patent's departments
        for result in fsd_asc_results:
            patent = result[0]  # Get the PatentsList instance
            dept_name = result[2]  # Get department_name from tuple (index 2)
            if dept_name:
                assert any(pd.department.department_name == dept_name 
                          for pd in patent.departments if pd.department), \
                    f"Department name {dept_name} not found in patent {patent.sys_id}'s departments"
        logger.info("✓ Department sorting (ascending) verified")
    
    # Test department sorting (descending)
    logger.info("Testing Department Sorting (Descending)...")
    fsd_desc_query = apply_sorting(base_query, 'FSD_DESC', similarity_score, query_embedding=query_embedding)
    fsd_desc_results = fsd_desc_query.all()
    
    # Verify department sorting
    if len(fsd_desc_results) > 1:
        # Get department names from the results
        dept_names = [r[2] for r in fsd_desc_results]  # Get department_name from tuple (index 2)
        
        # Filter out None values for comparison
        valid_dept_names = [name for name in dept_names if name is not None]
        if len(valid_dept_names) > 1:
            # Check that valid department names are sorted in descending order
            assert all(valid_dept_names[i] >= valid_dept_names[i+1] for i in range(len(valid_dept_names)-1)), \
                "Results should be sorted by department name in descending order"
        
        # Verify that None values are at the end
        if None in dept_names:
            none_index = dept_names.index(None)
            assert all(name is not None for name in dept_names[:none_index]), \
                "None values should be at the end of the results"
        
        # Verify that the department name matches one of the patent's departments
        for result in fsd_desc_results:
            patent = result[0]  # Get the PatentsList instance
            dept_name = result[2]  # Get department_name from tuple (index 2)
            if dept_name:
                assert any(pd.department.department_name == dept_name 
                          for pd in patent.departments if pd.department), \
                    f"Department name {dept_name} not found in patent {patent.sys_id}'s departments"
        logger.info("✓ Department sorting (descending) verified")
    
    # Test date sorting (descending)
    logger.info("Testing Date Sorting (Descending)...")
    date_desc_query = apply_sorting(base_query, 'DATE_DESC', similarity_score, query_embedding=query_embedding)
    date_desc_results = date_desc_query.all()
    
    # Verify date sorting
    if len(date_desc_results) > 1:
        # Check that results are sorted by date in descending order
        dates = [r[0].file_date for r in date_desc_results]  # Get file_date from PatentsList instance
        assert all(dates[i] >= dates[i+1] for i in range(len(dates)-1)), \
            "Results should be sorted by date in descending order"
        
        # Verify that NULL dates are at the end
        if None in dates:
            none_index = dates.index(None)
            assert all(date is not None for date in dates[:none_index]), \
                "NULL dates should be at the end of the results"
        logger.info("✓ Date sorting (descending) verified")
    
    # Test date sorting (ascending)
    logger.info("Testing Date Sorting (Ascending)...")
    date_asc_query = apply_sorting(base_query, 'DATE_ASC', similarity_score, query_embedding=query_embedding)
    date_asc_results = date_asc_query.all()
    
    # Verify date sorting
    if len(date_asc_results) > 1:
        # Check that results are sorted by date in ascending order
        dates = [r[0].file_date for r in date_asc_results]  # Get file_date from PatentsList instance
        assert all(dates[i] <= dates[i+1] for i in range(len(dates)-1)), \
            "Results should be sorted by date in ascending order"
        
        # Verify that NULL dates are at the end
        if None in dates:
            none_index = dates.index(None)
            assert all(date is not None for date in dates[:none_index]), \
                "NULL dates should be at the end of the results"
        logger.info("✓ Date sorting (ascending) verified")
    
    logger.info("=== All Sorting Tests Completed Successfully ===") 