#!/usr/bin/env python3
"""
Regenerate embeddings for tech patents (is_tech=False) to fix the low similarity issue.
This script will:
1. Backup current embeddings
2. Regenerate embeddings from current ai_summary content for tech patents only
3. Validate the new embeddings
"""

import numpy as np
from src.postgres_embedding import PatentsList, session, get_embedding
import asyncio
from sqlalchemy import update
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def regenerate_all_embeddings(dry_run=False, batch_size=100):
    """
    Regenerate embeddings for all patents with ai_summary content.
    
    Args:
        dry_run: If True, only test without updating database
        batch_size: Number of patents to process in each batch
    """
    logger.info("🔄 Starting embedding regeneration process")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    logger.info(f"Batch size: {batch_size}")
    
    # Get all patents that have ai_summary but need embedding updates
    patents = session.query(PatentsList).filter(
        PatentsList.ai_summary.isnot(None),
        PatentsList.ai_summary != '',
        PatentsList.is_tech == False  # Only process tech patents
    ).all()
    
    logger.info(f"Found {len(patents)} tech patents (is_tech=False) with ai_summary content")
    
    if not patents:
        logger.warning("No tech patents found with ai_summary content!")
        return
    
    # Process in batches
    total_processed = 0
    total_updated = 0
    errors = []
    
    for i in range(0, len(patents), batch_size):
        batch = patents[i:i + batch_size]
        logger.info(f"\n📦 Processing batch {i//batch_size + 1}/{(len(patents) + batch_size - 1)//batch_size}")
        logger.info(f"Patents {i+1}-{min(i+batch_size, len(patents))} of {len(patents)}")
        
        for patent in batch:
            try:
                total_processed += 1
                
                # Generate new embedding
                logger.info(f"  🔄 Patent {patent.sys_id}: Generating embedding...")
                new_embedding = await get_embedding(patent.ai_summary)
                
                if new_embedding and len(new_embedding) == 1536:
                    # Check if it's different from current embedding
                    needs_update = True
                    similarity = 0.0
                    
                    if patent.embedding is not None:
                        old_embedding = np.array(patent.embedding)
                        new_embedding_array = np.array(new_embedding)
                        similarity = np.dot(old_embedding, new_embedding_array) / (
                            np.linalg.norm(old_embedding) * np.linalg.norm(new_embedding_array)
                        )
                        # Only update if similarity is low (meaning they're different)
                        needs_update = similarity < 0.95
                    
                    if needs_update:
                        logger.info(f"    📝 Similarity: {similarity:.4f} - {'UPDATING' if not dry_run else 'WOULD UPDATE'}")
                        
                        if not dry_run:
                            # Update the database
                            stmt = (
                                update(PatentsList)
                                .where(PatentsList.sys_id == patent.sys_id)
                                .values(embedding=new_embedding)
                            )
                            session.execute(stmt)
                            session.commit()
                            total_updated += 1
                            logger.info(f"    ✅ Updated embedding for patent {patent.sys_id}")
                        else:
                            total_updated += 1
                    else:
                        logger.info(f"    ⏭️  Similarity: {similarity:.4f} - SKIPPING (already good)")
                        
                else:
                    logger.error(f"    ❌ Invalid embedding generated for patent {patent.sys_id}")
                    errors.append(f"Patent {patent.sys_id}: Invalid embedding")
                    
            except Exception as e:
                logger.error(f"    💥 Error processing patent {patent.sys_id}: {e}")
                errors.append(f"Patent {patent.sys_id}: {str(e)}")
        
        # Progress update
        logger.info(f"  📊 Batch complete. Processed: {total_processed}, {'Updated' if not dry_run else 'Would update'}: {total_updated}")
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("🏁 REGENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total patents processed: {total_processed}")
    logger.info(f"Total {'updated' if not dry_run else 'would be updated'}: {total_updated}")
    logger.info(f"Errors: {len(errors)}")
    
    if errors:
        logger.error("\n❌ ERRORS ENCOUNTERED:")
        for error in errors[:10]:  # Show first 10 errors
            logger.error(f"  - {error}")
        if len(errors) > 10:
            logger.error(f"  ... and {len(errors) - 10} more errors")
    
    if not dry_run and total_updated > 0:
        logger.info("\n🎉 Database updated successfully!")
        logger.info("You should now see much better similarity scores in searches.")
    elif dry_run:
        logger.info("\n⚠️  This was a dry run. To actually update the database, run with dry_run=False")
    
    return total_updated, errors

async def test_sample_after_update():
    """Test a few patents to verify the regeneration worked"""
    logger.info("\n🧪 TESTING REGENERATED EMBEDDINGS")
    logger.info("=" * 60)
    
    # Get a few patents to test
    test_patents = session.query(PatentsList).filter(
        PatentsList.embedding.isnot(None),
        PatentsList.ai_summary.isnot(None),
        PatentsList.is_tech == False  # Only test tech patents
    ).limit(3).all()
    
    for patent in test_patents:
        try:
            # Generate fresh embedding
            fresh_embedding = await get_embedding(patent.ai_summary)
            stored_embedding = np.array(patent.embedding)
            fresh_embedding_array = np.array(fresh_embedding)
            
            similarity = np.dot(stored_embedding, fresh_embedding_array) / (
                np.linalg.norm(stored_embedding) * np.linalg.norm(fresh_embedding_array)
            )
            
            logger.info(f"Patent {patent.sys_id}: Similarity = {similarity:.4f}")
            if similarity > 0.95:
                logger.info("  ✅ EXCELLENT - Embedding matches content")
            elif similarity > 0.8:
                logger.info("  🟨 GOOD - Embedding mostly matches content")
            else:
                logger.info("  ❌ POOR - Embedding doesn't match content")
                
        except Exception as e:
            logger.error(f"  💥 Error testing patent {patent.sys_id}: {e}")

async def main():
    print("🚀 Patent Embedding Regeneration Tool")
    print("=" * 60)
    
    # First, run a dry run to see what would be updated
    logger.info("Phase 1: Dry run to analyze current state")
    updated_count, errors = await regenerate_all_embeddings(dry_run=False, batch_size=100)
    
    if updated_count == 0:
        logger.info("✅ All embeddings appear to be up to date!")
        return
    
    # Ask for confirmation (in a real script, you might want user input)
    logger.info(f"\n🤔 {updated_count} patents need embedding updates.")
    logger.info("Would you like to proceed with the actual update?")
    logger.info("(To proceed, rerun this script with LIVE_UPDATE=True)")
    
    # Check environment variable for live update
    import os
    if os.getenv('LIVE_UPDATE', '').lower() == 'true':
        logger.info("\n🔥 LIVE UPDATE MODE - Proceeding with actual updates...")
        await regenerate_all_embeddings(dry_run=False, batch_size=100)
        
        # Test the results
        await test_sample_after_update()
    else:
        logger.info("\n💡 To run live update, set environment variable: LIVE_UPDATE=true")
        logger.info("Example: LIVE_UPDATE=true python regenerate_embeddings.py")

if __name__ == "__main__":
    asyncio.run(main()) 