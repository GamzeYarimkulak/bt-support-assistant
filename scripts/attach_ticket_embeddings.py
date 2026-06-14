"""
Attach ticket embeddings from the existing FAISS embedding payload to tickets.parquet.

This avoids re-encoding the full ticket dataset when indexes/embedding_data.pkl
already contains vectors for the indexed ticket documents.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TICKETS = PROJECT_ROOT / "data" / "processed" / "tickets.parquet"
DEFAULT_EMBEDDING_DATA = PROJECT_ROOT / "indexes" / "embedding_data.pkl"


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_embedding_payload(path: Path) -> tuple[list[dict[str, Any]], np.ndarray, str]:
    if not path.exists():
        raise FileNotFoundError(f"Embedding data file not found: {path}")

    with path.open("rb") as handle:
        payload = pickle.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("Embedding data payload must be a dictionary")

    documents = payload.get("documents")
    embeddings = payload.get("embeddings")
    model_name = safe_text(payload.get("model_name"))

    if not isinstance(documents, list):
        raise ValueError("Embedding data payload missing list field: documents")
    if not isinstance(embeddings, np.ndarray):
        raise ValueError("Embedding data payload missing numpy field: embeddings")
    if len(documents) != len(embeddings):
        raise ValueError(
            f"Document/embedding count mismatch: {len(documents)} documents, {len(embeddings)} embeddings"
        )

    return documents, embeddings, model_name


def build_ticket_embedding_lookup(
    documents: list[dict[str, Any]],
    embeddings: np.ndarray,
) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            continue
        if safe_text(document.get("doc_type")).casefold() != "ticket":
            continue

        ticket_id = (
            safe_text(document.get("ticket_id"))
            or safe_text(document.get("doc_id"))
            or safe_text(document.get("id"))
        )
        if ticket_id and ticket_id not in lookup:
            lookup[ticket_id] = index

    return lookup


def embedding_to_json(vector: np.ndarray) -> str:
    rounded = np.asarray(vector, dtype=np.float32).round(6).tolist()
    return json.dumps(rounded, ensure_ascii=False, separators=(",", ":"))


def attach_ticket_embeddings(
    tickets_path: Path = DEFAULT_TICKETS,
    embedding_data_path: Path = DEFAULT_EMBEDDING_DATA,
) -> dict[str, Any]:
    if not tickets_path.exists():
        raise FileNotFoundError(f"Processed tickets parquet not found: {tickets_path}")

    documents, embeddings, model_name = load_embedding_payload(embedding_data_path)
    lookup = build_ticket_embedding_lookup(documents, embeddings)

    frame = pd.read_parquet(tickets_path)
    id_column = "ticket_id" if "ticket_id" in frame.columns else "id" if "id" in frame.columns else None
    if id_column is None:
        raise ValueError("tickets.parquet must contain ticket_id or id")

    matched = 0
    missing = 0
    embedding_values: list[str | None] = []

    for value in frame[id_column]:
        ticket_id = safe_text(value)
        embedding_index = lookup.get(ticket_id)
        if embedding_index is None:
            missing += 1
            embedding_values.append(None)
            continue

        matched += 1
        embedding_values.append(embedding_to_json(embeddings[embedding_index]))

    frame = frame.copy()
    frame["embedding"] = embedding_values
    frame.to_parquet(tickets_path, index=False)

    embedding_dim = int(embeddings.shape[1]) if embeddings.ndim == 2 else None
    return {
        "tickets_path": str(tickets_path),
        "embedding_data_path": str(embedding_data_path),
        "model_name": model_name,
        "embedding_dim": embedding_dim,
        "ticket_rows": int(len(frame)),
        "ticket_embeddings_in_index": int(len(lookup)),
        "matched_ticket_rows": int(matched),
        "missing_ticket_rows": int(missing),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Attach indexed ticket embeddings to tickets.parquet.")
    parser.add_argument("--tickets", type=Path, default=DEFAULT_TICKETS)
    parser.add_argument("--embedding-data", type=Path, default=DEFAULT_EMBEDDING_DATA)
    args = parser.parse_args()

    summary = attach_ticket_embeddings(
        tickets_path=args.tickets,
        embedding_data_path=args.embedding_data,
    )

    print("Ticket embedding attachment complete.")
    print(f"Ticket rows: {summary['ticket_rows']}")
    print(f"Matched ticket rows: {summary['matched_ticket_rows']}")
    print(f"Missing ticket rows: {summary['missing_ticket_rows']}")
    print(f"Embedding dimension: {summary['embedding_dim']}")
    print(f"Embedding model: {summary['model_name']}")


if __name__ == "__main__":
    main()
