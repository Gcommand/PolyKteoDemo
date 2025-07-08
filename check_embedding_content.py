#!/usr/bin/env python3
"""
Check what content the embeddings were generated from and identify duplication issues.
"""

import numpy as np
from src.postgres_embedding import PatentsList, session
import asyncio
from src.postgres_embedding import get_embedding

async def main():
    print("🔍 Checking Embedding Content and Generation")
    print("=" * 60)
    
    # Get a sample of patents with their content and embeddings
    patents = session.query(PatentsList).filter(
        PatentsList.embedding.isnot(None),
        PatentsList.ai_summary.isnot(None)
    ).limit(10).all()
    
    print(f"Found {len(patents)} patents with embeddings and summaries")
    print()
    
    # Check if all embeddings are identical
    embeddings = []
    for patent in patents:
        if patent.embedding is not None:
            embeddings.append(np.array(patent.embedding))
    
    if len(embeddings) > 1:
        # Compare first embedding with all others
        first_embedding = embeddings[0]
        all_identical = True
        for i, embedding in enumerate(embeddings[1:], 1):
            if not np.array_equal(first_embedding, embedding):
                all_identical = False
                print(f"❌ Embedding {i+1} is different from embedding 1")
                break
        
        if all_identical:
            print("🚨 CRITICAL: ALL EMBEDDINGS ARE IDENTICAL!")
            print("This confirms the embedding generation is broken.")
        else:
            print("✅ Embeddings are different (this is expected)")
    
    print("\n" + "=" * 60)
    print("PATENT CONTENT ANALYSIS:")
    print("=" * 60)
    
    for i, patent in enumerate(patents[:5]):
        print(f"\n📄 Patent {patent.sys_id}:")
        print(f"Title: {patent.official_title[:100]}...")
        print(f"AI Summary (first 200 chars): {patent.ai_summary[:200] if patent.ai_summary else 'None'}...")
        
        if patent.embedding is not None:
            embedding = np.array(patent.embedding)
            print(f"Embedding stats: norm={np.linalg.norm(embedding):.6f}, mean={np.mean(embedding):.6f}")
        
        # Test generating a new embedding for this content
        if patent.ai_summary:
            try:
                print("🔄 Testing new embedding generation...")
                new_embedding = await get_embedding(patent.ai_summary)
                new_embedding_array = np.array(new_embedding)
                
                print(f"New embedding stats: norm={np.linalg.norm(new_embedding_array):.6f}, mean={np.mean(new_embedding_array):.6f}")
                
                if patent.embedding is not None:
                    stored_embedding = np.array(patent.embedding)
                    similarity = np.dot(stored_embedding, new_embedding_array) / (
                        np.linalg.norm(stored_embedding) * np.linalg.norm(new_embedding_array)
                    )
                    print(f"Similarity between stored and new: {similarity:.6f}")
                    
                    if similarity < 0.95:
                        print("⚠️  Low similarity suggests stored embedding may be wrong")
                    else:
                        print("✅ High similarity suggests stored embedding is correct")
                
            except Exception as e:
                print(f"❌ Error generating new embedding: {e}")
        
        print("-" * 40)
    
    # Check if the issue is in the update process
    print("\n" + "=" * 60)
    print("CHECKING UPDATE LOGIC:")
    print("=" * 60)
    
    # Look for patterns in when embeddings were created
    all_patents = session.query(PatentsList).filter(PatentsList.embedding.isnot(None)).all()
    
    if all_patents:
        print(f"Total patents with embeddings: {len(all_patents)}")
        
        # Check if they all have the same created_dt (suggesting bulk update)
        creation_times = [patent.created_dt for patent in all_patents if patent.created_dt]
        unique_times = set(creation_times)
        
        print(f"Unique creation times: {len(unique_times)}")
        if len(unique_times) < 5:
            print("⚠️  Very few unique creation times suggests bulk processing")
            for time in sorted(unique_times):
                count = creation_times.count(time)
                print(f"  {time}: {count} patents")
    
    session.close()

if __name__ == "__main__":
    asyncio.run(main()) 