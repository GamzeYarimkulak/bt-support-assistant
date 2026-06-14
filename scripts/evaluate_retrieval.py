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
from core.retrieval.eval_metrics import precision_at_k, recall_at_k, ndcg_at_k

logger = structlog.get_logger()


def _fix_cp1254_mojibake(value: Any) -> str:
    """Fix small cp1254/latin1 mojibake seen in some eval labels."""
    text = "" if value is None else str(value).strip()
    if not text:
        return ""

    if any(char in text for char in "ðþýÝÐÞ"):
        try:
            return text.encode("latin1").decode("cp1254")
        except UnicodeError:
            return text

    return text


def _normalize_label(value: Any) -> str:
    """Normalize labels for category fallback comparisons."""
    return _fix_cp1254_mojibake(value).casefold()


def _normalize_doc_id(value: Any) -> str:
    """Normalize document IDs so KB-0020 and KB-00020 can match."""
    text = "" if value is None else str(value).strip()
    if not text:
        return ""

    import re

    match = re.fullmatch(r"([A-Za-z]+)-0*(\d+)", text)
    if match:
        return f"{match.group(1).upper()}-{int(match.group(2))}"

    return text.upper()


def _split_raw_relevant_doc_ids(value: Any) -> List[str]:
    """Parse pipe/comma/semicolon separated relevant document IDs, preserving display values."""
    import re

    text = "" if value is None else str(value).strip()
    if not text or text.lower() == "nan":
        return []

    ids: List[str] = []
    seen: set[str] = set()
    for part in re.split(r"[|,;]", text):
        doc_id = part.strip()
        if doc_id and doc_id not in seen:
            ids.append(doc_id)
            seen.add(doc_id)
    return ids


def _split_relevant_doc_ids(value: Any) -> set[str]:
    """Parse pipe/comma/semicolon separated relevant document IDs."""
    ids = _split_raw_relevant_doc_ids(value)
    return {_normalize_doc_id(part) for part in ids if _normalize_doc_id(part)}


def _candidate_doc_ids(document: Dict[str, Any]) -> set[str]:
    """Return all comparable IDs for a retrieved document."""
    candidates = set()
    for field in ("id", "doc_id", "ticket_id", "document_id"):
        value = document.get(field)
        if value:
            raw = str(value).strip()
            candidates.add(raw)
            normalized = _normalize_doc_id(raw)
            if normalized:
                candidates.add(normalized)
    return candidates


def _primary_doc_id(document: Dict[str, Any]) -> str:
    """Return a stable primary document ID for metrics."""
    for field in ("id", "doc_id", "ticket_id", "document_id"):
        value = document.get(field)
        if value:
            return str(value).strip()
    return ""


def _doc_label(document: Dict[str, Any], field: str) -> str:
    """Return a display label from a retrieved document."""
    return _fix_cp1254_mojibake(document.get(field, ""))


def _is_kb_document(document: Dict[str, Any]) -> bool:
    """Return True if a retrieved document is a KB document/chunk."""
    doc_type = str(document.get("doc_type", "")).casefold()
    doc_id = _primary_doc_id(document).upper()
    return doc_type == "kb" or doc_id.startswith("KB-")


def load_queries_from_eval_csv(eval_queries_path: Path) -> List[Dict[str, Any]]:
    """Load retrieval evaluation queries from a curated CSV file."""
    if not eval_queries_path.exists():
        raise FileNotFoundError(f"Retrieval eval query file not found: {eval_queries_path}")

    frame = pd.read_csv(eval_queries_path, dtype=str, keep_default_na=False)
    required_columns = {"query_id", "query", "expected_category", "relevant_doc_ids"}
    missing = required_columns - set(frame.columns)
    if missing:
        raise ValueError(f"Retrieval eval query file missing columns: {sorted(missing)}")

    queries = []
    for row_index, row in frame.iterrows():
        query = str(row.get("query", "")).strip()
        if not query:
            logger.warning("empty_retrieval_eval_query", row=row_index + 2)
            continue

        raw_relevant_doc_ids = _split_raw_relevant_doc_ids(row.get("relevant_doc_ids", ""))
        queries.append(
            {
                "query_id": str(row.get("query_id", f"Q-{row_index + 1:03d}")).strip(),
                "query": query,
                "expected_category": _fix_cp1254_mojibake(row.get("expected_category", "")),
                "expected_subcategory": _fix_cp1254_mojibake(row.get("expected_subcategory", "")),
                "relevant_doc_ids": _split_relevant_doc_ids(row.get("relevant_doc_ids", "")),
                "relevant_doc_ids_raw": raw_relevant_doc_ids,
                "query_type": str(row.get("query_type", "")).strip(),
                "relevance_strategy": str(row.get("relevance_strategy", "")).strip().casefold(),
            }
        )

    return queries


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


def evaluate_retrieval_from_eval_csv(
    eval_queries_path: Optional[str] = None,
    output_file: Optional[str] = None,
    index_dir: Optional[str] = None,
    debug_output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate retrieval using curated query ground truth from CSV.

    If relevant_doc_ids is empty for a query, relevance falls back to matching
    expected_category against indexed document categories.
    """
    if eval_queries_path is None:
        eval_queries_path = os.path.join(
            settings.data_dir,
            "evaluation",
            "retrieval",
            "retrieval_eval_queries.csv",
        )

    if output_file is None:
        output_file = os.path.join(
            settings.data_dir,
            "evaluation",
            "retrieval",
            "retrieval_metrics.json",
        )

    if index_dir is None:
        index_dir = "indexes/"

    if debug_output_file is None:
        debug_output_file = os.path.join(
            settings.data_dir,
            "evaluation",
            "retrieval",
            "retrieval_debug_top5.csv",
        )

    eval_queries_file = Path(eval_queries_path)
    output_path = Path(output_file)
    index_path = Path(index_dir)
    debug_output_path = Path(debug_output_file)

    print("=" * 70)
    print("RETRIEVAL EVALUATION")
    print("=" * 70)
    print(f"Eval queries: {eval_queries_path}")
    print(f"Index directory: {index_dir}")
    print(f"Output file: {output_file}")
    print()

    print("Loading indexes...")
    index_builder = IndexBuilder(index_dir=str(index_path))

    bm25_retriever = index_builder.load_bm25_index()
    if not bm25_retriever:
        raise FileNotFoundError(f"BM25 index not found in {index_dir}")

    embedding_retriever = index_builder.load_embedding_index()
    if not embedding_retriever:
        raise FileNotFoundError(f"Embedding index not found in {index_dir}")

    hybrid_retriever = HybridRetriever(
        bm25_retriever=bm25_retriever,
        embedding_retriever=embedding_retriever,
        alpha=0.5,
        use_dynamic_weighting=True,
    )

    indexed_documents = hybrid_retriever.bm25_retriever.documents
    category_to_doc_ids: Dict[str, set[str]] = {}
    category_subcategory_to_doc_ids: Dict[tuple[str, str], set[str]] = {}
    for document in indexed_documents:
        category = _normalize_label(document.get("category", ""))
        if not category:
            continue
        candidate_ids = _candidate_doc_ids(document)
        category_to_doc_ids.setdefault(category, set()).update(candidate_ids)

        subcategory = _normalize_label(document.get("subcategory", ""))
        if subcategory:
            category_subcategory_to_doc_ids.setdefault((category, subcategory), set()).update(candidate_ids)

    print(f"  Loaded {len(indexed_documents)} indexed documents")

    print("\nLoading eval queries...")
    queries = load_queries_from_eval_csv(eval_queries_file)
    print(f"  Loaded {len(queries)} queries")

    exact_recall_5_scores: List[float] = []
    exact_recall_10_scores: List[float] = []
    exact_precision_5_scores: List[float] = []
    exact_ndcg_10_scores: List[float] = []
    category_hit_5_scores: List[float] = []
    category_hit_10_scores: List[float] = []
    subcategory_hit_5_scores: List[float] = []
    subcategory_hit_10_scores: List[float] = []
    category_precision_5_scores: List[float] = []
    subcategory_precision_5_scores: List[float] = []
    kb_hit_5_scores: List[float] = []
    exact_hit_5_scores: List[float] = []
    exact_hit_10_scores: List[float] = []
    exact_reciprocal_ranks: List[float] = []
    strategy_recall_5_scores: List[float] = []
    strategy_recall_10_scores: List[float] = []
    strategy_precision_5_scores: List[float] = []
    strategy_ndcg_10_scores: List[float] = []
    strategy_hit_5_scores: List[float] = []
    strategy_hit_10_scores: List[float] = []
    strategy_reciprocal_ranks: List[float] = []
    latencies: List[float] = []
    query_results: List[Dict[str, Any]] = []
    debug_rows: List[Dict[str, Any]] = []
    error_count = 0
    successful_queries = 0

    print("\nEvaluating retrieval...")
    for index, query_data in enumerate(queries, start=1):
        query_id = query_data["query_id"]
        query = query_data["query"]

        try:
            start_time = time.time()
            results = hybrid_retriever.search(query, top_k=10)
            latency = time.time() - start_time
            latencies.append(latency)

            configured_strategy = query_data.get("relevance_strategy", "")
            explicit_relevant_doc_ids = set(query_data["relevant_doc_ids"])
            expected_category = _normalize_label(query_data.get("expected_category", ""))
            expected_subcategory = _normalize_label(query_data.get("expected_subcategory", ""))

            if configured_strategy in {"category_subcategory", "subcategory"}:
                relevance_strategy = "category_subcategory"
                relevant_doc_ids = category_subcategory_to_doc_ids.get(
                    (expected_category, expected_subcategory),
                    set(),
                )
            elif configured_strategy == "category":
                relevance_strategy = "category"
                relevant_doc_ids = category_to_doc_ids.get(expected_category, set())
            elif explicit_relevant_doc_ids:
                relevance_strategy = "doc_ids"
                relevant_doc_ids = explicit_relevant_doc_ids
            else:
                relevance_strategy = "category"
                relevant_doc_ids = category_to_doc_ids.get(expected_category, set())

            retrieved_metric_ids: List[str] = []
            relevances: List[float] = []
            retrieved_ids = [_primary_doc_id(result) for result in results]
            top5_results = results[:5]
            top10_results = results[:10]

            for result in results:
                candidates = _candidate_doc_ids(result)
                matched_ids = candidates & relevant_doc_ids
                retrieved_metric_ids.append(next(iter(matched_ids)) if matched_ids else _primary_doc_id(result))
                relevances.append(1.0 if matched_ids else 0.0)

            exact_recall_5 = recall_at_k(retrieved_metric_ids, relevant_doc_ids, k=5)
            exact_recall_10 = recall_at_k(retrieved_metric_ids, relevant_doc_ids, k=10)
            exact_precision_5 = precision_at_k(retrieved_metric_ids, relevant_doc_ids, k=5)
            exact_ndcg_10 = ndcg_at_k(relevances, k=10)
            hit_5 = 1.0 if any(relevances[:5]) else 0.0
            hit_10 = 1.0 if any(relevances[:10]) else 0.0
            reciprocal_rank = 0.0
            for rank, relevance in enumerate(relevances, start=1):
                if relevance > 0:
                    reciprocal_rank = 1.0 / rank
                    break

            strategy_recall_5 = exact_recall_5
            strategy_recall_10 = exact_recall_10
            if relevance_strategy in {"category", "category_subcategory"}:
                strategy_recall_5 = hit_5
                strategy_recall_10 = hit_10
            strategy_precision_5 = exact_precision_5
            strategy_ndcg_10 = exact_ndcg_10

            category_matches_top5 = [
                bool(expected_category and _normalize_label(result.get("category", "")) == expected_category)
                for result in top5_results
            ]
            category_matches_top10 = [
                bool(expected_category and _normalize_label(result.get("category", "")) == expected_category)
                for result in top10_results
            ]
            subcategory_matches_top5 = [
                bool(expected_subcategory and _normalize_label(result.get("subcategory", "")) == expected_subcategory)
                for result in top5_results
            ]
            subcategory_matches_top10 = [
                bool(expected_subcategory and _normalize_label(result.get("subcategory", "")) == expected_subcategory)
                for result in top10_results
            ]

            category_hit_5 = 1.0 if any(category_matches_top5) else 0.0
            category_hit_10 = 1.0 if any(category_matches_top10) else 0.0
            category_precision_5 = (
                sum(category_matches_top5) / len(top5_results)
                if top5_results and expected_category
                else 0.0
            )
            subcategory_hit_5 = 1.0 if any(subcategory_matches_top5) else 0.0
            subcategory_hit_10 = 1.0 if any(subcategory_matches_top10) else 0.0
            subcategory_precision_5 = (
                sum(subcategory_matches_top5) / len(top5_results)
                if top5_results and expected_subcategory
                else 0.0
            )
            kb_hit_5 = 1.0 if any(_is_kb_document(result) for result in top5_results) else 0.0

            if relevance_strategy == "doc_ids":
                exact_recall_5_scores.append(exact_recall_5)
                exact_recall_10_scores.append(exact_recall_10)
                exact_precision_5_scores.append(exact_precision_5)
                exact_ndcg_10_scores.append(exact_ndcg_10)
                exact_hit_5_scores.append(hit_5)
                exact_hit_10_scores.append(hit_10)
                exact_reciprocal_ranks.append(reciprocal_rank)
            category_hit_5_scores.append(category_hit_5)
            category_hit_10_scores.append(category_hit_10)
            category_precision_5_scores.append(category_precision_5)
            kb_hit_5_scores.append(kb_hit_5)
            strategy_recall_5_scores.append(strategy_recall_5)
            strategy_recall_10_scores.append(strategy_recall_10)
            strategy_precision_5_scores.append(strategy_precision_5)
            strategy_ndcg_10_scores.append(strategy_ndcg_10)
            strategy_hit_5_scores.append(hit_5)
            strategy_hit_10_scores.append(hit_10)
            strategy_reciprocal_ranks.append(reciprocal_rank)
            if expected_subcategory:
                subcategory_hit_5_scores.append(subcategory_hit_5)
                subcategory_hit_10_scores.append(subcategory_hit_10)
                subcategory_precision_5_scores.append(subcategory_precision_5)
            successful_queries += 1

            query_results.append(
                {
                    "query_id": query_id,
                    "query_type": query_data.get("query_type", ""),
                    "expected_category": query_data.get("expected_category", ""),
                    "expected_subcategory": query_data.get("expected_subcategory", ""),
                    "relevance_strategy": relevance_strategy,
                    "num_relevant_ids": len(relevant_doc_ids),
                    "num_results": len(results),
                    "exact_recall_at_5": float(exact_recall_5),
                    "exact_recall_at_10": float(exact_recall_10),
                    "exact_precision_at_5": float(exact_precision_5),
                    "exact_ndcg_at_10": float(exact_ndcg_10),
                    "hit_at_5": float(hit_5),
                    "hit_at_10": float(hit_10),
                    "reciprocal_rank": float(reciprocal_rank),
                    "strategy_recall_at_5": float(strategy_recall_5),
                    "strategy_recall_at_10": float(strategy_recall_10),
                    "strategy_precision_at_5": float(strategy_precision_5),
                    "strategy_ndcg_at_10": float(strategy_ndcg_10),
                    "category_hit_at_5": float(category_hit_5),
                    "category_hit_at_10": float(category_hit_10),
                    "subcategory_hit_at_5": float(subcategory_hit_5) if expected_subcategory else None,
                    "subcategory_hit_at_10": float(subcategory_hit_10) if expected_subcategory else None,
                    "category_precision_at_5": float(category_precision_5),
                    "subcategory_precision_at_5": float(subcategory_precision_5) if expected_subcategory else None,
                    "kb_hit_at_5": float(kb_hit_5),
                    "latency_seconds": float(latency),
                    "retrieved_ids": retrieved_ids,
                }
            )

            if len(debug_rows) < 30:
                debug_rows.append(
                    {
                        "query_id": query_id,
                        "query": query,
                        "expected_category": query_data.get("expected_category", ""),
                        "expected_subcategory": query_data.get("expected_subcategory", ""),
                        "relevant_doc_ids": "|".join(query_data.get("relevant_doc_ids_raw", [])),
                        "relevance_strategy": relevance_strategy,
                        "retrieved_top5_ids": "|".join(retrieved_ids[:5]),
                        "retrieved_top5_categories": "|".join(_doc_label(result, "category") for result in top5_results),
                        "retrieved_top5_subcategories": "|".join(_doc_label(result, "subcategory") for result in top5_results),
                        "exact_hit_at_5": bool(hit_5),
                        "category_hit_at_5": bool(category_hit_5),
                        "subcategory_hit_at_5": bool(subcategory_hit_5) if expected_subcategory else "",
                    }
                )

        except Exception as exc:
            error_count += 1
            logger.warning("retrieval_eval_query_failed", query_id=query_id, error=str(exc))
            query_results.append(
                {
                    "query_id": query_id,
                    "error": str(exc),
                }
            )

        if index % 25 == 0:
            print(f"  Processed {index}/{len(queries)} queries...")

    def average(values: List[float]) -> float:
        return float(sum(values) / len(values)) if values else 0.0

    per_strategy: Dict[str, Dict[str, Any]] = {}
    for query_result in query_results:
        strategy = query_result.get("relevance_strategy")
        if not strategy:
            continue
        bucket = per_strategy.setdefault(
            strategy,
            {
                "query_count": 0,
                "strategy_recall_at_5": [],
                "strategy_recall_at_10": [],
                "strategy_precision_at_5": [],
                "strategy_ndcg_at_10": [],
                "hit_at_5": [],
                "hit_at_10": [],
                "reciprocal_rank": [],
                "category_hit_at_5": [],
                "subcategory_hit_at_5": [],
            },
        )
        bucket["query_count"] += 1
        for key in (
            "strategy_recall_at_5",
            "strategy_recall_at_10",
            "strategy_precision_at_5",
            "strategy_ndcg_at_10",
            "hit_at_5",
            "hit_at_10",
            "reciprocal_rank",
            "category_hit_at_5",
            "subcategory_hit_at_5",
        ):
            value = query_result.get(key)
            if value is not None:
                bucket[key].append(float(value))

    per_strategy_metrics: Dict[str, Dict[str, Any]] = {}
    for strategy, bucket in per_strategy.items():
        per_strategy_metrics[strategy] = {
            "query_count": bucket["query_count"],
            "strategy_recall_at_5": average(bucket["strategy_recall_at_5"]),
            "strategy_recall_at_10": average(bucket["strategy_recall_at_10"]),
            "strategy_precision_at_5": average(bucket["strategy_precision_at_5"]),
            "strategy_ndcg_at_10": average(bucket["strategy_ndcg_at_10"]),
            "category_hit_at_5": average(bucket["category_hit_at_5"]),
            "subcategory_hit_at_5": average(bucket["subcategory_hit_at_5"]),
        }

    metrics = {
        "query_count": len(queries),
        "successful_queries": successful_queries,
        "error_count": error_count,
        "average_metrics": {
            "exact_recall_at_5": average(exact_recall_5_scores),
            "exact_recall_at_10": average(exact_recall_10_scores),
            "exact_precision_at_5": average(exact_precision_5_scores),
            "exact_ndcg_at_10": average(exact_ndcg_10_scores),
            "exact_hit_at_5": average(exact_hit_5_scores),
            "exact_hit_at_10": average(exact_hit_10_scores),
            "exact_mrr": average(exact_reciprocal_ranks),
            "category_hit_at_5": average(category_hit_5_scores),
            "category_hit_at_10": average(category_hit_10_scores),
            "subcategory_hit_at_5": average(subcategory_hit_5_scores),
            "subcategory_hit_at_10": average(subcategory_hit_10_scores),
            "category_precision_at_5": average(category_precision_5_scores),
            "subcategory_precision_at_5": average(subcategory_precision_5_scores),
            "kb_hit_at_5": average(kb_hit_5_scores),
            "mean_latency_sec": average(latencies),
            "strategy_recall_at_5": average(strategy_recall_5_scores),
            "strategy_recall_at_10": average(strategy_recall_10_scores),
            "strategy_precision_at_5": average(strategy_precision_5_scores),
            "strategy_ndcg_at_10": average(strategy_ndcg_10_scores),
            "strategy_hit_at_5": average(strategy_hit_5_scores),
            "strategy_hit_at_10": average(strategy_hit_10_scores),
            "strategy_mrr": average(strategy_reciprocal_ranks),
            "recall_at_5": average(strategy_recall_5_scores),
            "recall_at_10": average(strategy_recall_10_scores),
            "precision_at_5": average(strategy_precision_5_scores),
            "ndcg_at_10": average(strategy_ndcg_10_scores),
            "avg_latency_seconds": average(latencies),
        },
        "per_strategy_metrics": per_strategy_metrics,
        "sources": {
            "eval_queries": str(eval_queries_file),
            "index_dir": str(index_path),
            "debug_top5_csv": str(debug_output_path),
        },
        "index": {
            "indexed_documents": len(indexed_documents),
        },
        "metric_notes": {
            "exact_metrics": "Only the explicit relevant_doc_ids are counted as relevant.",
            "strategy_metrics": "Primary recall/precision/nDCG use each query's relevance_strategy: doc_ids for ticket-specific queries, category/category_subcategory for generic support queries.",
            "category_metrics": "A retrieved document is relevant if its category matches expected_category.",
            "subcategory_metrics": "Queries with empty expected_subcategory are excluded from subcategory denominators.",
            "kb_hit_at_5": "Share of queries where at least one top-5 retrieved document is a KB document/chunk.",
        },
        "query_results": query_results,
        "last_updated": pd.Timestamp.now().isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    debug_output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        debug_rows,
        columns=[
            "query_id",
            "query",
            "expected_category",
            "expected_subcategory",
            "relevant_doc_ids",
            "relevance_strategy",
            "retrieved_top5_ids",
            "retrieved_top5_categories",
            "retrieved_top5_subcategories",
            "exact_hit_at_5",
            "category_hit_at_5",
            "subcategory_hit_at_5",
        ],
    ).to_csv(debug_output_path, index=False, encoding="utf-8")

    print()
    print("=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"Query count: {metrics['query_count']}")
    print(f"Successful queries: {metrics['successful_queries']}")
    print(f"Error count: {metrics['error_count']}")
    print(f"Exact Recall@5: {metrics['average_metrics']['exact_recall_at_5']:.4f}")
    print(f"Exact Recall@10: {metrics['average_metrics']['exact_recall_at_10']:.4f}")
    print(f"Exact Precision@5: {metrics['average_metrics']['exact_precision_at_5']:.4f}")
    print(f"Exact nDCG@10: {metrics['average_metrics']['exact_ndcg_at_10']:.4f}")
    print(f"Exact Hit@5: {metrics['average_metrics']['exact_hit_at_5']:.4f}")
    print(f"Exact MRR: {metrics['average_metrics']['exact_mrr']:.4f}")
    print(f"Strategy Recall@5: {metrics['average_metrics']['strategy_recall_at_5']:.4f}")
    print(f"Strategy Precision@5: {metrics['average_metrics']['strategy_precision_at_5']:.4f}")
    print(f"Strategy nDCG@10: {metrics['average_metrics']['strategy_ndcg_at_10']:.4f}")
    print(f"Strategy Hit@5: {metrics['average_metrics']['strategy_hit_at_5']:.4f}")
    print(f"Strategy MRR: {metrics['average_metrics']['strategy_mrr']:.4f}")
    print(f"Category Hit@5: {metrics['average_metrics']['category_hit_at_5']:.4f}")
    print(f"Subcategory Hit@5: {metrics['average_metrics']['subcategory_hit_at_5']:.4f}")
    print(f"Category Precision@5: {metrics['average_metrics']['category_precision_at_5']:.4f}")
    print(f"KB Hit@5: {metrics['average_metrics']['kb_hit_at_5']:.4f}")
    print(f"Mean latency: {metrics['average_metrics']['mean_latency_sec']:.4f} seconds")
    print(f"\nResults saved to: {output_path}")
    print(f"Debug top-5 saved to: {debug_output_path}")

    return metrics


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval performance from curated eval queries"
    )
    parser.add_argument(
        "--eval-queries",
        type=str,
        help="Path to retrieval_eval_queries.csv (default: data/evaluation/retrieval/retrieval_eval_queries.csv)"
    )
    parser.add_argument(
        "--parquet",
        type=str,
        help="Legacy option kept for compatibility; curated CSV eval is used by default"
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
        help="Output JSON file (default: data/evaluation/retrieval/retrieval_metrics.json)"
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        help="Index directory (default: indexes/)"
    )
    
    args = parser.parse_args()
    
    try:
        result = evaluate_retrieval_from_eval_csv(
            eval_queries_path=args.eval_queries,
            output_file=args.output,
            index_dir=args.index_dir,
        )
        
        print("\nEvaluation completed successfully")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

