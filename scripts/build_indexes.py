"""
Build indexes from processed data (tickets.parquet + kb_chunks.jsonl).

This script reads:
- data/processed/tickets.parquet
- data/processed/kb_chunks.jsonl

And creates:
- indexes/bm25_index.pkl
- indexes/faiss_index.bin
- indexes/embedding_data.pkl
- indexes/index_metadata.json

This is a NEW script that works with the processed data format.
It does NOT modify existing build_indexes.py.
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from data_pipeline.build_indexes import IndexBuilder

logger = structlog.get_logger()


def load_tickets_from_parquet(parquet_path: Path) -> List[Dict[str, Any]]:
    """
    Load tickets from parquet file and convert to document format.
    
    Args:
        parquet_path: Path to tickets.parquet
        
    Returns:
        List of document dictionaries
    """
    df = pd.read_parquet(parquet_path)
    
    documents = []
    
    for _, row in df.iterrows():
        doc = {
            "id": str(row.get("id", "")),
            "doc_id": str(row.get("id", "")),
            "doc_type": "ticket",
            "title": "",  # Not in parquet schema
            "text": str(row.get("text", "")),
            "category": str(row.get("category", "")),
            "priority": str(row.get("priority", "")),
            "status": "",  # Not in parquet schema
            "created_at": row.get("created_at"),
            "resolution": str(row.get("resolution", "")),
            "source": str(row.get("source", "")),
        }
        documents.append(doc)
    
    return documents


def load_kb_chunks_from_jsonl(jsonl_path: Path) -> List[Dict[str, Any]]:
    """
    Load KB chunks from JSONL file and convert to document format.
    
    Args:
        jsonl_path: Path to kb_chunks.jsonl
        
    Returns:
        List of document dictionaries
    """
    documents = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            chunk = json.loads(line.strip())
            
            doc = {
                "id": chunk.get("id", ""),
                "doc_id": chunk.get("id", ""),
                "doc_type": "kb",
                "title": f"{chunk.get('source_pdf', '')} - Page {chunk.get('page', 0)}",
                "text": chunk.get("text", ""),
                "category": "",  # KB chunks don't have category
                "priority": "",
                "status": "",
                "created_at": None,
                "source": chunk.get("source_pdf", ""),
                "page": chunk.get("page", 0),
                "chunk_index": chunk.get("chunk_index", 0),
            }
            documents.append(doc)
    
    return documents


def build_indexes(
    tickets_parquet: Optional[str] = None,
    kb_jsonl: Optional[str] = None,
    index_dir: Optional[str] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
    rebuild: bool = False
) -> Dict[str, Any]:
    """
    Build indexes from processed data files.
    
    Args:
        tickets_parquet: Path to tickets.parquet (default: data/processed/tickets.parquet)
        kb_jsonl: Path to kb_chunks.jsonl (default: data/processed/kb_chunks.jsonl)
        index_dir: Directory for indexes (default: indexes/)
        dry_run: If True, only analyze without building
        limit: Limit number of documents (for testing)
        rebuild: If True, rebuild even if indexes exist
        
    Returns:
        Dictionary with build statistics
    """
    if tickets_parquet is None:
        tickets_parquet = os.path.join(settings.data_dir, "processed", "tickets.parquet")
    
    if kb_jsonl is None:
        kb_jsonl = os.path.join(settings.data_dir, "processed", "kb_chunks.jsonl")
    
    if index_dir is None:
        index_dir = "indexes/"
    
    tickets_path = Path(tickets_parquet)
    kb_path = Path(kb_jsonl)
    index_path = Path(index_dir)
    
    print("=" * 70)
    print("INDEX BUILD PIPELINE")
    print("=" * 70)
    print(f"Tickets parquet: {tickets_parquet}")
    print(f"KB JSONL: {kb_jsonl}")
    print(f"Index directory: {index_dir}")
    print(f"Mode: {'DRY RUN' if dry_run else 'BUILD'}")
    print(f"Rebuild: {rebuild}")
    print()
    
    # Check input files
    if not tickets_path.exists():
        raise FileNotFoundError(f"Tickets parquet not found: {tickets_parquet}")
    
    if not kb_path.exists():
        logger.warning("kb_jsonl_not_found",
                      path=str(kb_path),
                      message="KB JSONL not found, will only index tickets")
        kb_path = None
    
    # Load documents
    print("Loading documents...")
    
    print(f"  Loading tickets from: {tickets_path.name}")
    ticket_docs = load_tickets_from_parquet(tickets_path)
    print(f"    Loaded {len(ticket_docs)} tickets")
    
    kb_docs = []
    if kb_path and kb_path.exists():
        print(f"  Loading KB chunks from: {kb_path.name}")
        kb_docs = load_kb_chunks_from_jsonl(kb_path)
        print(f"    Loaded {len(kb_docs)} KB chunks")
    
    # Apply limit with KB priority: KB docs are included first, then tickets
    if limit:
        if len(kb_docs) >= limit:
            # If KB docs exceed limit, only take KB docs (up to limit)
            all_documents = kb_docs[:limit]
            print(f"\n  Limited to {limit} documents (KB priority: all KB, no tickets)")
        else:
            # Include all KB docs, then fill remaining slots with tickets
            ticket_limit = limit - len(kb_docs)
            all_documents = kb_docs + ticket_docs[:ticket_limit]
            print(f"\n  Limited to {limit} documents (KB priority: {len(kb_docs)} KB + {ticket_limit} tickets)")
    else:
        # No limit: include all documents
        all_documents = ticket_docs + kb_docs
    
    print(f"\n  Total documents: {len(all_documents)}")
    
    if not all_documents:
        raise ValueError("No documents to index")
    
    if dry_run:
        print("\n[DRY RUN] Would build indexes (not building)")
        print(f"  BM25 index: {index_path / 'bm25_index.pkl'}")
        print(f"  FAISS index: {index_path / 'faiss_index.bin'}")
        print(f"  Embedding data: {index_path / 'embedding_data.pkl'}")
        print(f"  Metadata: {index_path / 'index_metadata.json'}")
        
        return {
            "num_documents": len(all_documents),
            "num_tickets": len(ticket_docs),
            "num_kb_chunks": len(kb_docs),
            "dry_run": True
        }
    
    # Check if indexes exist
    bm25_file = index_path / "bm25_index.pkl"
    faiss_file = index_path / "faiss_index.bin"
    embedding_data_file = index_path / "embedding_data.pkl"
    
    if not rebuild and (bm25_file.exists() or faiss_file.exists() or embedding_data_file.exists()):
        print("\n⚠️  Index files already exist!")
        print("  Use --rebuild to rebuild indexes")
        print(f"  BM25: {bm25_file.exists()}")
        print(f"  FAISS: {faiss_file.exists()}")
        print(f"  Embedding data: {embedding_data_file.exists()}")
        return {
            "num_documents": len(all_documents),
            "skipped": True,
            "message": "Indexes already exist, use --rebuild to rebuild"
        }
    
    # Build indexes
    print("\nBuilding indexes...")
    
    index_builder = IndexBuilder(
        index_dir=str(index_path),
        embedding_model_name=settings.embedding_model_name
    )
    
    print("  Building BM25 index...")
    bm25_retriever = index_builder.build_bm25_index(
        documents=all_documents,
        text_field="text",
        save=True
    )
    
    print("  Building embedding index...")
    embedding_retriever = index_builder.build_embedding_index(
        documents=all_documents,
        text_field="text",
        save=True
    )
    
    # Save metadata
    # Note: ticket_docs and kb_docs are the ORIGINAL loaded counts,
    # but all_documents is the ACTUAL indexed count (after limit)
    metadata = {
        "num_documents": len(all_documents),  # Actual indexed count
        "num_tickets_loaded": len(ticket_docs),  # Total loaded from parquet
        "num_tickets_indexed": len([d for d in all_documents if d.get("doc_type") == "ticket"]),  # Actually indexed
        "num_kb_chunks_loaded": len(kb_docs),  # Total loaded from jsonl
        "num_kb_chunks_indexed": len([d for d in all_documents if d.get("doc_type") == "kb"]),  # Actually indexed
        "limit_applied": limit is not None,
        "limit_value": limit,
        "tickets_source": str(tickets_path),
        "kb_source": str(kb_path) if kb_path else None,
        "embedding_model": settings.embedding_model_name,
        "bm25_stats": bm25_retriever.get_index_stats(),
        "embedding_stats": embedding_retriever.get_index_stats(),
    }
    
    metadata_path = index_path / "index_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    
    print()
    print("=" * 70)
    print("BUILD COMPLETE")
    print("=" * 70)
    print(f"Total documents indexed: {len(all_documents)}")
    num_tickets_indexed = len([d for d in all_documents if d.get("doc_type") == "ticket"])
    num_kb_indexed = len([d for d in all_documents if d.get("doc_type") == "kb"])
    print(f"  - Tickets indexed: {num_tickets_indexed} (loaded: {len(ticket_docs)})")
    print(f"  - KB chunks indexed: {num_kb_indexed} (loaded: {len(kb_docs)})")
    if limit:
        print(f"  - Note: Limited to {limit} documents for testing")
    print(f"\nIndex files:")
    print(f"  - BM25: {bm25_file}")
    print(f"  - FAISS: {faiss_file}")
    print(f"  - Embedding data: {embedding_data_file}")
    print(f"  - Metadata: {metadata_path}")
    
    return metadata


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build indexes from processed data (tickets.parquet + kb_chunks.jsonl)"
    )
    parser.add_argument(
        "--tickets",
        type=str,
        help="Path to tickets.parquet (default: data/processed/tickets.parquet)"
    )
    parser.add_argument(
        "--kb",
        type=str,
        help="Path to kb_chunks.jsonl (default: data/processed/kb_chunks.jsonl)"
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        help="Index directory (default: indexes/)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze without building indexes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents (for testing)"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild indexes even if they exist"
    )
    
    args = parser.parse_args()
    
    try:
        result = build_indexes(
            tickets_parquet=args.tickets,
            kb_jsonl=args.kb,
            index_dir=args.index_dir,
            dry_run=args.dry_run,
            limit=args.limit,
            rebuild=args.rebuild
        )
        
        print("\n✓ Index build completed successfully")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

