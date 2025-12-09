"""
Index building for BM25 and embedding-based retrieval.
"""

from typing import List, Dict, Any, Optional
import os
import json
import pickle
import numpy as np
import structlog

from core.retrieval.bm25_retriever import BM25Retriever
from core.retrieval.embedding_retriever import EmbeddingRetriever
from data_pipeline.ingestion import load_itsm_tickets_from_csv, ITSMTicket
from data_pipeline.anonymize import anonymize_tickets

logger = structlog.get_logger()


class IndexBuilder:
    """
    Builds and manages indexes for retrieval.
    Handles both BM25 (lexical) and embedding (semantic) indexes.
    """
    
    def __init__(
        self,
        index_dir: str = "./indexes",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize index builder.
        
        Args:
            index_dir: Directory for storing indexes
            embedding_model_name: Name of embedding model
        """
        self.index_dir = index_dir
        self.embedding_model_name = embedding_model_name
        
        # Create index directory
        os.makedirs(index_dir, exist_ok=True)
        
        logger.info("index_builder_initialized",
                   index_dir=index_dir,
                   embedding_model=embedding_model_name)
    
    def build_bm25_index(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "text",
        save: bool = True
    ) -> BM25Retriever:
        """
        Build BM25 index from documents.
        
        Args:
            documents: List of documents
            text_field: Field containing text to index
            save: Whether to save the index
            
        Returns:
            BM25Retriever with indexed documents
        """
        logger.info("building_bm25_index", num_documents=len(documents))
        
        retriever = BM25Retriever()
        retriever.index_documents(documents, text_field=text_field)
        
        if save:
            self._save_bm25_index(retriever, documents)
        
        logger.info("bm25_index_built", num_documents=len(documents))
        
        return retriever
    
    def build_embedding_index(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "text",
        save: bool = True
    ) -> EmbeddingRetriever:
        """
        Build embedding index from documents.
        
        Args:
            documents: List of documents
            text_field: Field containing text to embed
            save: Whether to save the index
            
        Returns:
            EmbeddingRetriever with indexed documents
        """
        logger.info("building_embedding_index", num_documents=len(documents))
        
        retriever = EmbeddingRetriever(model_name=self.embedding_model_name)
        retriever.load_model()
        retriever.index_documents(documents, text_field=text_field)
        
        if save:
            self._save_embedding_index(retriever, documents)
        
        logger.info("embedding_index_built", num_documents=len(documents))
        
        return retriever
    
    def build_hybrid_indexes(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "text"
    ) -> tuple[BM25Retriever, EmbeddingRetriever]:
        """
        Build both BM25 and embedding indexes.
        
        Args:
            documents: List of documents
            text_field: Field containing text
            
        Returns:
            Tuple of (BM25Retriever, EmbeddingRetriever)
        """
        logger.info("building_hybrid_indexes", num_documents=len(documents))
        
        bm25_retriever = self.build_bm25_index(documents, text_field, save=True)
        embedding_retriever = self.build_embedding_index(documents, text_field, save=True)
        
        logger.info("hybrid_indexes_built")
        
        return bm25_retriever, embedding_retriever
    
    def prepare_documents_for_indexing(
        self,
        tickets: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prepare ticket documents for indexing.
        Combines relevant fields into a single text field.
        
        Args:
            tickets: List of ticket dictionaries
            
        Returns:
            List of documents ready for indexing
        """
        documents = []
        
        for ticket in tickets:
            # Combine title and description
            text_parts = []
            
            if ticket.get("title"):
                text_parts.append(ticket["title"])
            
            if ticket.get("description"):
                text_parts.append(ticket["description"])
            
            if ticket.get("resolution"):
                text_parts.append(f"Resolution: {ticket['resolution']}")
            
            combined_text = " ".join(text_parts)
            
            # Create document
            doc = {
                "id": ticket.get("id"),
                "doc_id": ticket.get("id"),
                "doc_type": "ticket",
                "title": ticket.get("title", ""),
                "text": combined_text,
                "category": ticket.get("category"),
                "priority": ticket.get("priority"),
                "status": ticket.get("status"),
                "created_at": ticket.get("created_at"),
            }
            
            documents.append(doc)
        
        logger.info("documents_prepared", num_documents=len(documents))
        
        return documents
    
    def _save_bm25_index(self, retriever: BM25Retriever, documents: List[Dict[str, Any]]):
        """
        Save BM25 index to disk.
        
        Args:
            retriever: BM25Retriever instance
            documents: Indexed documents
        """
        # Save documents and metadata
        index_data = {
            "documents": documents,
            "tokenized_corpus": retriever.tokenized_corpus,
            "k1": retriever.k1,
            "b": retriever.b
        }
        
        filepath = os.path.join(self.index_dir, "bm25_index.pkl")
        
        with open(filepath, 'wb') as f:
            pickle.dump(index_data, f)
        
        logger.info("bm25_index_saved", filepath=filepath)
    
    def _save_embedding_index(self, retriever: EmbeddingRetriever, documents: List[Dict[str, Any]]):
        """
        Save embedding index to disk.
        
        Args:
            retriever: EmbeddingRetriever instance
            documents: Indexed documents
        """
        # Save FAISS index
        faiss_path = os.path.join(self.index_dir, "faiss_index.bin")
        retriever.save_index(faiss_path)
        
        # Save documents and embeddings
        data_path = os.path.join(self.index_dir, "embedding_data.pkl")
        
        index_data = {
            "documents": documents,
            "embeddings": retriever.embeddings,
            "model_name": retriever.model_name
        }
        
        with open(data_path, 'wb') as f:
            pickle.dump(index_data, f)
        
        logger.info("embedding_index_saved", 
                   faiss_path=faiss_path,
                   data_path=data_path)
    
    def load_bm25_index(self) -> Optional[BM25Retriever]:
        """
        Load BM25 index from disk.
        
        Returns:
            BM25Retriever instance or None if not found
        """
        filepath = os.path.join(self.index_dir, "bm25_index.pkl")
        
        if not os.path.exists(filepath):
            logger.warning("bm25_index_not_found", filepath=filepath)
            return None
        
        with open(filepath, 'rb') as f:
            index_data = pickle.load(f)
        
        retriever = BM25Retriever(k1=index_data["k1"], b=index_data["b"])
        retriever.documents = index_data["documents"]
        retriever.tokenized_corpus = index_data["tokenized_corpus"]
        
        from rank_bm25 import BM25Okapi
        retriever.bm25 = BM25Okapi(retriever.tokenized_corpus)
        
        logger.info("bm25_index_loaded", 
                   filepath=filepath,
                   num_documents=len(retriever.documents))
        
        return retriever
    
    def load_embedding_index(self) -> Optional[EmbeddingRetriever]:
        """
        Load embedding index from disk.
        
        Returns:
            EmbeddingRetriever instance or None if not found
        """
        faiss_path = os.path.join(self.index_dir, "faiss_index.bin")
        data_path = os.path.join(self.index_dir, "embedding_data.pkl")
        
        if not os.path.exists(faiss_path) or not os.path.exists(data_path):
            logger.warning("embedding_index_not_found")
            return None
        
        # Load data
        with open(data_path, 'rb') as f:
            index_data = pickle.load(f)
        
        # Create retriever
        retriever = EmbeddingRetriever(model_name=index_data["model_name"])
        retriever.load_model()
        retriever.documents = index_data["documents"]
        retriever.embeddings = index_data["embeddings"]
        
        # Load FAISS index
        retriever.load_index(faiss_path)
        
        logger.info("embedding_index_loaded",
                   num_documents=len(retriever.documents))
        
        return retriever


# ============================================================================
# PHASE 3: CSV → Anonymization → Index Building Pipeline
# ============================================================================

def convert_ticket_to_document(ticket: ITSMTicket) -> Dict[str, Any]:
    """
    Convert an ITSMTicket to a document dictionary for indexing.
    
    This function combines relevant text fields (short_description, description,
    resolution) into a single "text" field that can be indexed by BM25 and
    embedding retrievers.
    
    Args:
        ticket: ITSMTicket object (anonymized or not)
        
    Returns:
        Document dictionary with:
        - "text": Combined text from all fields
        - "ticket_id": Original ticket ID
        - "id": Alias for ticket_id (for retriever compatibility)
        - Metadata: category, subcategory, priority, status, etc.
        
    Example:
        >>> ticket = ITSMTicket(ticket_id="TCK-001", ...)
        >>> doc = convert_ticket_to_document(ticket)
        >>> print(doc["text"])
        "Outlook şifremi unuttum Outlook hesabına giriş yapamıyor..."
    """
    # Combine text fields
    text_parts = []
    
    if ticket.short_description:
        text_parts.append(ticket.short_description)
    
    if ticket.description:
        text_parts.append(ticket.description)
    
    if ticket.resolution:
        text_parts.append(f"Çözüm: {ticket.resolution}")
    
    combined_text = " ".join(text_parts)
    
    # Create document with all metadata
    document = {
        # Text field for indexing
        "text": combined_text,
        
        # IDs (both for compatibility with different retriever expectations)
        "ticket_id": ticket.ticket_id,
        "id": ticket.ticket_id,
        "doc_id": ticket.ticket_id,
        
        # Individual fields (preserved for display/filtering)
        "short_description": ticket.short_description,
        "description": ticket.description,
        "resolution": ticket.resolution,
        
        # Metadata
        "category": ticket.category,
        "subcategory": ticket.subcategory,
        "channel": ticket.channel,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        
        # Document type
        "doc_type": "itsm_ticket"
    }
    
    return document


def build_indexes_from_csv(
    csv_path: str,
    index_dir: str,
    *,
    language: str = "tr",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    anonymize: bool = True
) -> tuple[int, Dict[str, Any]]:
    """
    Build BM25 and embedding indexes from ITSM tickets in a CSV file.
    
    This is the main pipeline function for PHASE 3 that integrates:
    1. CSV ingestion (PHASE 1)
    2. Anonymization (PHASE 2)
    3. Index building (PHASE 3)
    
    Process:
    1. Load tickets from CSV using load_itsm_tickets_from_csv()
    2. Anonymize tickets using anonymize_tickets() (optional)
    3. Convert tickets to document format
    4. Build BM25 and embedding indexes
    5. Save indexes to disk
    
    Args:
        csv_path: Path to CSV file containing ITSM tickets
        index_dir: Directory where indexes will be saved
        language: Language code (default: "tr" for Turkish)
        embedding_model: Name of sentence-transformers model to use
        anonymize: Whether to anonymize PII before indexing (default: True)
        
    Returns:
        Tuple of (num_documents, stats_dict) where:
        - num_documents: Number of tickets indexed
        - stats_dict: Dictionary with build statistics
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV is empty or invalid
        
    Example:
        >>> num_docs, stats = build_indexes_from_csv(
        ...     "data/sample_itsm_tickets.csv",
        ...     "indexes/",
        ...     anonymize=True
        ... )
        >>> print(f"Indexed {num_docs} tickets")
        Indexed 3 tickets
    """
    logger.info("starting_index_build_pipeline",
               csv_path=csv_path,
               index_dir=index_dir,
               language=language,
               anonymize=anonymize)
    
    # Step 1: Load tickets from CSV (PHASE 1)
    logger.info("step_1_loading_tickets", csv_path=csv_path)
    tickets = load_itsm_tickets_from_csv(csv_path)
    
    if not tickets:
        raise ValueError(f"No tickets loaded from {csv_path}")
    
    logger.info("tickets_loaded", num_tickets=len(tickets))
    
    # Step 2: Anonymize tickets (PHASE 2)
    if anonymize:
        logger.info("step_2_anonymizing_tickets")
        tickets = anonymize_tickets(tickets)
        logger.info("tickets_anonymized", num_tickets=len(tickets))
    else:
        logger.info("step_2_skipping_anonymization")
    
    # Step 3: Convert tickets to document format
    logger.info("step_3_converting_to_documents")
    documents = [convert_ticket_to_document(ticket) for ticket in tickets]
    logger.info("documents_converted", num_documents=len(documents))
    
    # Step 4: Build indexes
    logger.info("step_4_building_indexes", index_dir=index_dir)
    
    index_builder = IndexBuilder(
        index_dir=index_dir,
        embedding_model_name=embedding_model
    )
    
    bm25_retriever, embedding_retriever = index_builder.build_hybrid_indexes(
        documents=documents,
        text_field="text"
    )
    
    # Step 5: Save metadata
    metadata = {
        "num_documents": len(documents),
        "source_csv": csv_path,
        "language": language,
        "embedding_model": embedding_model,
        "anonymized": anonymize,
        "bm25_stats": bm25_retriever.get_index_stats(),
        "embedding_stats": embedding_retriever.get_index_stats(),
    }
    
    metadata_path = os.path.join(index_dir, "index_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    logger.info("index_build_complete",
               num_documents=len(documents),
               index_dir=index_dir,
               metadata_path=metadata_path)
    
    return len(documents), metadata

