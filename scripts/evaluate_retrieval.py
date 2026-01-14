"""
Retrieval evaluation script: Measure Recall@5, nDCG@10, and latency.

Reads tickets from data/processed/tickets.parquet and evaluates retrieval
performance using the hybrid retriever.

Ground truth: If a ticket's resolution field is not empty, use PART of the ticket's
text (first 60-70%) as the query and the same ticket's ID as ground truth.
This prevents exact matching and provides a more realistic evaluation.

Note: We use partial text to simulate real-world scenarios where users don't
type the exact ticket text, but rather a query that should retrieve the relevant ticket.
"""

import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from data_pipeline.build_indexes import IndexBuilder
from core.retrieval.hybrid_retriever import HybridRetriever
from core.retrieval.eval_metrics import recall_at_k, ndcg_at_k

logger = structlog.get_logger()


def load_queries_from_parquet(
    parquet_path: Path,
    n_queries: int = 100,
    seed: int = 42,
    indexed_doc_ids: Optional[set] = None
) -> List[Dict[str, Any]]:
    """
    Load queries from parquet file.
    
    Uses tickets with non-empty resolution as queries.
    The ticket text is the query, and the resolution is the ground truth.
    
    If indexed_doc_ids is provided, only selects tickets that exist in the index.
    
    Args:
        parquet_path: Path to tickets.parquet
        n_queries: Number of queries to generate
        seed: Random seed
        indexed_doc_ids: Set of document IDs that exist in the index (optional)
        
    Returns:
        List of query dictionaries with 'query', 'ground_truth', 'ticket_id'
    """
    df = pd.read_parquet(parquet_path)
    
    # Filter tickets with non-empty resolution
    df_with_resolution = df[df["resolution"].notna() & (df["resolution"] != "")]
    
    if len(df_with_resolution) == 0:
        raise ValueError("No tickets with resolution found in parquet file")
    
    # Filter by indexed document IDs if provided
    if indexed_doc_ids is not None:
        # Convert ticket IDs to string for comparison (use .copy() to avoid SettingWithCopyWarning)
        df_with_resolution = df_with_resolution.copy()
        df_with_resolution["id_str"] = df_with_resolution["id"].astype(str)
        df_with_resolution = df_with_resolution[
            df_with_resolution["id_str"].isin(indexed_doc_ids)
        ].copy()
        df_with_resolution = df_with_resolution.drop(columns=["id_str"])
        
        if len(df_with_resolution) == 0:
            raise ValueError(
                "No tickets with resolution found that exist in the index. "
                "Try rebuilding index without limit or with a larger limit."
            )
        
        if len(df_with_resolution) < n_queries:
            logger.warning(
                "insufficient_indexed_tickets",
                requested=n_queries,
                available=len(df_with_resolution),
                message=f"Only {len(df_with_resolution)} tickets with resolution found in index (requested {n_queries})"
            )
    
    # Sample queries
    if n_queries:
        df_with_resolution = df_with_resolution.sample(
            n=min(n_queries, len(df_with_resolution)),
            random_state=seed
        )
    
    queries = []
    
    for _, row in df_with_resolution.iterrows():
        # Use only PART of the ticket text as query to avoid exact match
        # This simulates a real scenario where user doesn't type the exact ticket
        full_text = str(row.get("text", ""))
        
        # Take a smaller portion to make evaluation more realistic
        # Strategy: Take first 30-40% of words, or first 50 words, whichever is smaller
        words = full_text.split()
        
        if len(words) > 100:
            # For long texts: take first 30% or first 50 words (whichever is smaller)
            query_text = " ".join(words[:min(int(len(words) * 0.3), 50)])
        elif len(words) > 30:
            # For medium texts: take first 40% or first 30 words
            query_text = " ".join(words[:min(int(len(words) * 0.4), 30)])
        else:
            # For short texts: take first 50% (but at least 5 words)
            query_text = " ".join(words[:max(int(len(words) * 0.5), min(5, len(words)))])
        
        query = {
            "query": query_text,
            "ground_truth": str(row.get("resolution", "")),
            "ticket_id": str(row.get("id", "")),
            "category": str(row.get("category", "")),
            "full_text_length": len(words),  # Debug: original text length
            "query_length": len(query_text.split()),  # Debug: query length
        }
        queries.append(query)
    
    return queries


def evaluate_retrieval(
    parquet_path: Optional[str] = None,
    n_queries: int = 100,
    seed: int = 42,
    output_file: Optional[str] = None,
    index_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate retrieval performance.
    
    Args:
        parquet_path: Path to tickets.parquet (default: data/processed/tickets.parquet)
        n_queries: Number of queries to evaluate
        seed: Random seed for query sampling
        output_file: Output JSON file (default: test_results.json)
        index_dir: Index directory (default: indexes/)
        
    Returns:
        Dictionary with evaluation results
    """
    if parquet_path is None:
        parquet_path = os.path.join(settings.data_dir, "processed", "tickets.parquet")
    
    if output_file is None:
        output_file = "test_results.json"
    
    if index_dir is None:
        index_dir = "indexes/"
    
    parquet_file = Path(parquet_path)
    output_path = Path(output_file)
    index_path = Path(index_dir)
    
    print("=" * 70)
    print("RETRIEVAL EVALUATION")
    print("=" * 70)
    print(f"Tickets parquet: {parquet_path}")
    print(f"Number of queries: {n_queries}")
    print(f"Random seed: {seed}")
    print(f"Index directory: {index_dir}")
    print(f"Output file: {output_file}")
    print()
    
    if not parquet_file.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
    
    # Load indexes FIRST to get indexed document IDs
    print("Loading indexes...")
    index_builder = IndexBuilder(index_dir=str(index_path))
    
    bm25_retriever = index_builder.load_bm25_index()
    if not bm25_retriever:
        raise FileNotFoundError(f"BM25 index not found in {index_dir}")
    
    embedding_retriever = index_builder.load_embedding_index()
    if not embedding_retriever:
        raise FileNotFoundError(f"Embedding index not found in {index_dir}")
    
    # Extract indexed document IDs as a set
    indexed_doc_ids = set()
    for doc in bm25_retriever.documents:
        doc_id = str(doc.get("id") or doc.get("doc_id") or "")
        if doc_id:
            indexed_doc_ids.add(doc_id)
    
    print(f"  Found {len(indexed_doc_ids)} documents in index")
    
    # Load queries (filtered by indexed document IDs)
    print("\nLoading queries...")
    try:
        queries = load_queries_from_parquet(
            parquet_file, 
            n_queries=n_queries, 
            seed=seed,
            indexed_doc_ids=indexed_doc_ids
        )
        print(f"  Loaded {len(queries)} queries (filtered by indexed documents)")
        
        # Always show query length info if available
        if queries:
            first_query = queries[0]
            if "query_length" in first_query and "full_text_length" in first_query:
                # Calculate average query lengths
                query_lengths = [q.get("query_length", 0) for q in queries]
                full_lengths = [q.get("full_text_length", 0) for q in queries]
                
                avg_query_length = sum(query_lengths) / len(query_lengths) if query_lengths else 0
                avg_full_length = sum(full_lengths) / len(full_lengths) if full_lengths else 0
                
                print(f"  Average query length: {avg_query_length:.1f} words (from {avg_full_length:.1f} words original)")
                if avg_full_length > 0:
                    reduction_pct = 100 * (1 - avg_query_length / avg_full_length)
                    print(f"  Query reduction: {reduction_pct:.1f}%")
                
                # Show first query as example
                print(f"\n  Example query:")
                print(f"    Original: {first_query.get('full_text_length', 'N/A')} words")
                print(f"    Query: {first_query.get('query_length', 'N/A')} words")
                print(f"    Preview: {first_query['query'][:100]}...")
            else:
                # Fallback: calculate from actual query text
                first_query_text = first_query.get('query', '')
                first_query_words = len(first_query_text.split())
                print(f"  ⚠️  Debug info missing, calculated from query: {first_query_words} words")
                print(f"    Query preview: {first_query_text[:100]}...")
    except ValueError as e:
        # Fallback to old behavior if filtering fails
        if "No tickets with resolution found that exist in the index" in str(e):
            print(f"  ⚠️  Warning: {e}")
            print("  Falling back to old behavior (may include tickets not in index)")
            queries = load_queries_from_parquet(
                parquet_file, 
                n_queries=n_queries, 
                seed=seed,
                indexed_doc_ids=None  # No filtering
            )
            print(f"  Loaded {len(queries)} queries (unfiltered)")
        else:
            raise
    
    # Create hybrid retriever
    hybrid_retriever = HybridRetriever(
        bm25_retriever=bm25_retriever,
        embedding_retriever=embedding_retriever,
        alpha=0.5,
        use_dynamic_weighting=True
    )
    
    print("  Indexes loaded successfully")
    
    # Evaluate
    print("\nEvaluating retrieval...")
    
    recall_scores = []
    ndcg_scores = []
    latencies = []
    
    # Build document ID to index mapping for ground truth
    doc_id_to_index = {}
    for idx, doc in enumerate(hybrid_retriever.bm25_retriever.documents):
        doc_id = str(doc.get("id") or doc.get("doc_id") or str(idx))
        doc_id_to_index[doc_id] = idx
    
    # Debug: Verify that query ticket IDs are in index
    print(f"\n  Debug: Verifying query ticket IDs are in index...")
    queries_in_index = 0
    for query_data in queries:
        ticket_id = str(query_data["ticket_id"])
        if ticket_id in doc_id_to_index:
            queries_in_index += 1
    
    print(f"    Queries with tickets in index: {queries_in_index}/{len(queries)}")
    
    if queries_in_index < len(queries):
        print(f"    ⚠️  Warning: {len(queries) - queries_in_index} queries have tickets not in index")
    
    ground_truth_not_found_count = 0
    
    for i, query_data in enumerate(queries, 1):
        query = query_data["query"]
        ground_truth_ticket_id = str(query_data["ticket_id"])  # Ensure string
        
        if i % 10 == 0:
            print(f"  Processing query {i}/{len(queries)}...")
        
        # Measure latency
        start_time = time.time()
        results = hybrid_retriever.search(query, top_k=10)
        latency = time.time() - start_time
        latencies.append(latency)
        
        # Find ground truth document index
        ground_truth_idx = doc_id_to_index.get(ground_truth_ticket_id, -1)
        
        if ground_truth_idx == -1:
            # Ground truth document not in index
            ground_truth_not_found_count += 1
            if i <= 3:  # Debug first 3
                print(f"    ⚠️  Query {i}: Ground truth ticket_id '{ground_truth_ticket_id}' not found in index")
                print(f"       Available IDs (sample): {list(doc_id_to_index.keys())[:5]}")
            recall_scores.append(0.0)
            ndcg_scores.append(0.0)
            continue
        
        # Build retrieved document IDs list and relevance scores
        retrieved_ids = []
        relevances = []
        relevant_set = {ground_truth_ticket_id}  # Set with ground truth ID
        
        for result in results:
            result_id = str(result.get("id") or result.get("doc_id") or "")
            retrieved_ids.append(result_id)
            
            # Relevance score: 1.0 if ground truth, 0.0 otherwise
            if result_id == ground_truth_ticket_id:
                relevances.append(1.0)
            else:
                relevances.append(0.0)
        
        # Calculate metrics
        recall_5 = recall_at_k(retrieved_ids, relevant_set, k=5)
        ndcg_10 = ndcg_at_k(relevances, k=10)
        
        recall_scores.append(recall_5)
        ndcg_scores.append(ndcg_10)
    
    # Calculate averages
    avg_recall_5 = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    avg_ndcg_10 = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    
    results = {
        "num_queries": len(queries),
        "recall_at_5": float(avg_recall_5),
        "ndcg_at_10": float(avg_ndcg_10),
        "avg_latency_seconds": float(avg_latency),
        "individual_recall_scores": [float(s) for s in recall_scores],
        "individual_ndcg_scores": [float(s) for s in ndcg_scores],
        "individual_latencies": [float(l) for l in latencies],
        "seed": seed,
        "parquet_source": str(parquet_path),
    }
    
    # Load existing results if file exists
    existing_results = {}
    if output_path.exists():
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
        except:
            pass
    
    # Merge results (new results take precedence)
    if "evaluation_results" not in existing_results:
        existing_results["evaluation_results"] = []
    
    existing_results["evaluation_results"].append(results)
    existing_results["last_updated"] = pd.Timestamp.now().isoformat()
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(existing_results, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"Number of queries: {len(queries)}")
    print(f"Ground truth not found in index: {ground_truth_not_found_count}/{len(queries)}")
    print(f"Recall@5: {avg_recall_5:.4f}")
    print(f"nDCG@10: {avg_ndcg_10:.4f}")
    print(f"Average latency: {avg_latency:.4f} seconds")
    
    if ground_truth_not_found_count > 0:
        print(f"\n⚠️  WARNING: {ground_truth_not_found_count} queries had ground truth not found in index.")
        print("   This might be because:")
        print("   - Ticket IDs don't match between parquet and index")
        print("   - Index was built with limit, excluding some tickets")
        print("   - ID format mismatch")
    
    print(f"\nResults saved to: {output_path}")
    
    return results


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval performance (Recall@5, nDCG@10, latency)"
    )
    parser.add_argument(
        "--parquet",
        type=str,
        help="Path to tickets.parquet (default: data/processed/tickets.parquet)"
    )
    parser.add_argument(
        "--n-queries",
        type=int,
        default=100,
        help="Number of queries to evaluate (default: 100)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for query sampling (default: 42)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file (default: test_results.json)"
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        help="Index directory (default: indexes/)"
    )
    
    args = parser.parse_args()
    
    try:
        result = evaluate_retrieval(
            parquet_path=args.parquet,
            n_queries=args.n_queries,
            seed=args.seed,
            output_file=args.output,
            index_dir=args.index_dir
        )
        
        print("\n✓ Evaluation completed successfully")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

