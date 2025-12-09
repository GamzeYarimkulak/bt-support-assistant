"""
Script to build indexes from sample ITSM tickets CSV.

This script implements the PHASE 3 pipeline:
1. Load tickets from CSV (PHASE 1)
2. Anonymize them (PHASE 2)
3. Build BM25 and embedding indexes (PHASE 3)

Usage:
    python scripts/build_sample_index.py [csv_path] [index_dir]

Examples:
    python scripts/build_sample_index.py
    python scripts/build_sample_index.py data/sample_itsm_tickets.csv indexes/
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.build_indexes import build_indexes_from_csv, IndexBuilder
from core.retrieval.hybrid_retriever import HybridRetriever


def main():
    """Build indexes from CSV file."""
    parser = argparse.ArgumentParser(description="Build retrieval indexes from ITSM tickets CSV")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="data/sample_itsm_tickets.csv",
        help="Path to CSV file (default: data/sample_itsm_tickets.csv)"
    )
    parser.add_argument(
        "index_dir",
        nargs="?",
        default="indexes/",
        help="Directory to save indexes (default: indexes/)"
    )
    parser.add_argument(
        "--no-anonymize",
        action="store_true",
        help="Skip PII anonymization"
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model to use"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("PHASE 3: Building Retrieval Indexes from ITSM Tickets")
    print("=" * 70)
    
    print(f"\nConfiguration:")
    print(f"  CSV file: {args.csv_path}")
    print(f"  Index directory: {args.index_dir}")
    print(f"  Anonymization: {'Disabled' if args.no_anonymize else 'Enabled'}")
    print(f"  Embedding model: {args.embedding_model}")
    
    # Check if CSV exists
    if not os.path.exists(args.csv_path):
        print(f"\n❌ Error: CSV file not found: {args.csv_path}")
        print("\nTo create a sample CSV, make sure data/sample_itsm_tickets.csv exists.")
        return 1
    
    print(f"\n{'='*70}")
    print("Step 1: Loading and processing tickets...")
    print(f"{'='*70}")
    
    try:
        # Build indexes using the integrated pipeline
        num_docs, stats = build_indexes_from_csv(
            csv_path=args.csv_path,
            index_dir=args.index_dir,
            language="tr",
            embedding_model=args.embedding_model,
            anonymize=not args.no_anonymize
        )
        
        print(f"\n✓ Successfully indexed {num_docs} tickets")
        print(f"\nIndex Statistics:")
        print(f"  - BM25 documents: {stats['bm25_stats']['num_documents']}")
        print(f"  - Embedding documents: {stats['embedding_stats']['num_documents']}")
        print(f"  - Embedding dimension: {stats['embedding_stats']['embedding_dim']}")
        print(f"  - Index directory: {args.index_dir}")
        
        # Test retrieval
        print(f"\n{'='*70}")
        print("Step 2: Testing retrieval...")
        print(f"{'='*70}")
        
        index_builder = IndexBuilder(index_dir=args.index_dir)
        bm25_retriever = index_builder.load_bm25_index()
        embedding_retriever = index_builder.load_embedding_index()
        
        if bm25_retriever and embedding_retriever:
            # Test with a Turkish query
            test_query = "Outlook şifremi unuttum"
            print(f"\nTest query: '{test_query}'")
            
            print("\nBM25 Results:")
            bm25_results = bm25_retriever.search(test_query, top_k=3)
            for i, result in enumerate(bm25_results, 1):
                short_desc = result.get('short_description', '')[:60]
                print(f"  {i}. [{result['ticket_id']}] {short_desc}... (score: {result['score']:.3f})")
            
            print("\nEmbedding Results:")
            embedding_results = embedding_retriever.search(test_query, top_k=3)
            for i, result in enumerate(embedding_results, 1):
                short_desc = result.get('short_description', '')[:60]
                print(f"  {i}. [{result['ticket_id']}] {short_desc}... (score: {result['score']:.3f})")
            
            print("\nHybrid Results:")
            hybrid_retriever = HybridRetriever(
                bm25_retriever=bm25_retriever,
                embedding_retriever=embedding_retriever,
                alpha=0.5
            )
            hybrid_results = hybrid_retriever.search(test_query, top_k=3)
            for i, result in enumerate(hybrid_results, 1):
                short_desc = result.get('short_description', '')[:60]
                print(f"  {i}. [{result['ticket_id']}] {short_desc}... (score: {result['score']:.3f})")
        
        print(f"\n{'='*70}")
        print("✅ Index building and testing completed successfully!")
        print(f"{'='*70}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

