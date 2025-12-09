"""
Chat endpoint for user questions and RAG-based answering.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import structlog
from datetime import datetime

from app.config import settings
from core.rag.pipeline import RAGPipeline, RAGResult
from core.retrieval.hybrid_retriever import HybridRetriever
from core.retrieval.bm25_retriever import BM25Retriever
from core.retrieval.embedding_retriever import EmbeddingRetriever
from data_pipeline.build_indexes import IndexBuilder

router = APIRouter()
logger = structlog.get_logger()

# Global RAG pipeline instance (initialized lazily)
_rag_pipeline: Optional[RAGPipeline] = None

# Conversation memory store (session_id -> list of messages)
# Each message: {"role": "user"|"assistant", "content": str, "timestamp": datetime}
_conversation_memory: Dict[str, List[Dict[str, Any]]] = {}
MAX_MEMORY_MESSAGES = 10  # Last 5 user + 5 assistant messages (5 pairs)


class ChatRequest(BaseModel):
    """User chat request model."""
    query: str = Field(..., min_length=1, max_length=1000, description="User question")
    session_id: Optional[str] = Field(None, description="Optional session ID for context")
    language: Optional[str] = Field(None, description="Query language (auto-detected if not provided)")


class Source(BaseModel):
    """Source document used for answering."""
    doc_id: str
    doc_type: str  # "ticket" or "document"
    title: str
    snippet: str
    relevance_score: float


class ChatResponse(BaseModel):
    """Chat response with answer and sources."""
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: List[Source]
    has_answer: bool
    intent: Optional[str] = None
    language: str
    timestamp: datetime


def get_conversation_history(session_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of messages (oldest to newest)
    """
    return _conversation_memory.get(session_id, [])


def add_to_conversation_history(session_id: str, role: str, content: str) -> None:
    """
    Add a message to conversation history.
    
    Args:
        session_id: Session identifier
        role: "user" or "assistant"
        content: Message content
        
    Note:
        Automatically trims history to MAX_MEMORY_MESSAGES
    """
    if session_id not in _conversation_memory:
        _conversation_memory[session_id] = []
    
    _conversation_memory[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Trim to keep only last N messages
    if len(_conversation_memory[session_id]) > MAX_MEMORY_MESSAGES:
        _conversation_memory[session_id] = _conversation_memory[session_id][-MAX_MEMORY_MESSAGES:]
    
    try:
        logger.debug("conversation_updated", 
                    session_id=session_id, 
                    role=role,
                    total_messages=len(_conversation_memory[session_id]))
    except (OSError, UnicodeError):
        pass


def get_rag_pipeline() -> RAGPipeline:
    """
    Get or initialize the global RAG pipeline instance.
    
    This function lazily loads the indexes and creates the RAG pipeline.
    In production, this would be initialized at startup.
    
    Returns:
        RAGPipeline instance
        
    Raises:
        HTTPException: If indexes cannot be loaded
    """
    global _rag_pipeline
    
    if _rag_pipeline is not None:
        return _rag_pipeline
    
    try:
        # Load indexes from disk
        index_builder = IndexBuilder(index_dir="indexes/")
        
        bm25_retriever = index_builder.load_bm25_index()
        embedding_retriever = index_builder.load_embedding_index()
        
        if not bm25_retriever or not embedding_retriever:
            error_msg = "Indexes not found or failed to load"
            print(f"[ERROR] {error_msg}: bm25={bm25_retriever is not None}, embedding={embedding_retriever is not None}")
            raise HTTPException(status_code=503, detail=error_msg)
        
        # Create hybrid retriever
        hybrid_retriever = HybridRetriever(
            bm25_retriever=bm25_retriever,
            embedding_retriever=embedding_retriever,
            alpha=0.5  # Equal weight for BM25 and embeddings
        )
        
        # Create RAG pipeline (PHASE 8: with real LLM support)
        _rag_pipeline = RAGPipeline(
            retriever=hybrid_retriever,
            confidence_threshold=0.6,  # Adjust based on testing
            # PHASE 8: Real LLM settings from config
            use_real_llm=settings.use_real_llm,
            openai_api_key=settings.openai_api_key,
            llm_model_name=settings.llm_model,
            llm_temperature=settings.llm_temperature,
            llm_max_tokens=settings.llm_max_tokens
        )
        
        try:
            logger.info("rag_pipeline_initialized_successfully",
                       use_real_llm=settings.use_real_llm,
                       llm_model=settings.llm_model if settings.use_real_llm else "stub")
        except (OSError, UnicodeError):
            pass
        return _rag_pipeline
        
    except Exception as e:
        try:
            logger.error("rag_pipeline_initialization_failed", error=str(e))
        except (OSError, UnicodeError):
            pass
        raise HTTPException(
            status_code=503,
            detail=f"RAG pipeline not available. Please build indexes first: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Answer user questions using hybrid RAG (PHASE 4 implementation).
    
    Args:
        request: User query and optional context
        
    Returns:
        Answer with sources and confidence score
        
    Process:
        1. Get or initialize RAG pipeline
        2. Call pipeline.answer() with the question
        3. Map RAGResult to ChatResponse
        4. Return structured response
    """
    try:
        # Log with safe encoding (avoid PowerShell Unicode issues)
        try:
            logger.info("chat_request", 
                       query=request.query[:50],  # Truncate to avoid encoding issues
                       session_id=request.session_id,
                       language=request.language)
        except (OSError, UnicodeError):
            pass  # Skip logging if encoding fails
        
        # Get RAG pipeline (initializes if needed)
        pipeline = get_rag_pipeline()
        
        # Get conversation history if session_id provided
        conversation_history = []
        if request.session_id:
            conversation_history = get_conversation_history(request.session_id)
            try:
                logger.info("conversation_history_loaded",
                           session_id=request.session_id,
                           history_length=len(conversation_history))
            except (OSError, UnicodeError):
                pass
        
        # Call RAG pipeline with conversation context
        rag_result: RAGResult = pipeline.answer(
            question=request.query,
            language=request.language,
            session_id=request.session_id,
            conversation_history=conversation_history  # PHASE 9: Add conversation context
        )
        
        # Convert sources from RAGResult to ChatResponse format
        sources = [
            Source(
                doc_id=src["doc_id"],
                doc_type=src["doc_type"],
                title=src["title"],
                snippet=src["snippet"],
                relevance_score=src["relevance_score"]
            )
            for src in rag_result.sources
        ]
        
        # Build response
        response = ChatResponse(
            answer=rag_result.answer,
            confidence=rag_result.confidence,
            sources=sources,
            has_answer=rag_result.has_answer,
            intent=rag_result.intent,
            language=rag_result.language or "tr",
            timestamp=datetime.now()
        )
        
        try:
            logger.info("chat_response",
                       has_answer=response.has_answer,
                       confidence=response.confidence,
                       num_sources=len(sources))
        except (OSError, UnicodeError):
            pass
        
        # Save conversation to memory (PHASE 9: Conversation tracking)
        if request.session_id:
            add_to_conversation_history(request.session_id, "user", request.query)
            add_to_conversation_history(request.session_id, "assistant", rag_result.answer)
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 503 from get_rag_pipeline)
        raise
    except Exception as e:
        try:
            logger.error("chat_error", error=str(e), query=request.query[:50])
        except (OSError, UnicodeError):
            pass
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


