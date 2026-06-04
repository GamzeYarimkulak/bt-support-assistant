"""
PHASE 5: Anomaly Detection API Endpoints

This module provides REST API endpoints for monitoring ticket distributions
and detecting anomalies over time windows.

Endpoints:
- GET /api/v1/anomaly/stats - Get window statistics and drift scores
- GET /api/v1/anomaly/detect - Detect anomaly events
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
import structlog
import os

from app.config import settings
from core.anomaly.engine import (
    AnomalyTicket,
    WindowStats,
    AnomalyEvent,
    analyze_ticket_stream,
)
from data_pipeline.ingestion import load_itsm_tickets_from_csv
from data_pipeline.anonymize import DataAnonymizer
from data_pipeline.build_indexes import IndexBuilder
import pandas as pd

router = APIRouter()
logger = structlog.get_logger()


# Global cache for anomaly results (simple in-memory cache)
_anomaly_cache: Dict[str, Any] = {}


# ============================================
# RESPONSE MODELS
# ============================================

class WindowStatsResponse(BaseModel):
    """Statistics for a time window."""
    window_start: datetime
    window_end: datetime
    total_tickets: int
    volume_zscore: float | None = None
    category_divergence: float | None = None
    semantic_drift: float | None = None
    combined_score: float
    severity: str


class AnomalyEventResponse(BaseModel):
    """Anomaly event detected."""
    window_start: datetime
    window_end: datetime
    severity: str
    score: float
    reasons: List[str]


class AnomalyStatsResponse(BaseModel):
    """Anomaly statistics and drift metrics."""
    windows: List[WindowStatsResponse]
    summary: Dict[str, Any]


class AnomalyDetectResponse(BaseModel):
    """Anomaly detection response."""
    events: List[AnomalyEventResponse]
    total_windows: int
    anomalous_windows: int
    severity_distribution: Dict[str, int]


# ============================================
# HELPER FUNCTIONS
# ============================================

def _load_chat_logs_for_anomaly(chat_logs_path: str) -> List[AnomalyTicket]:
    """
    Load chat logs (chat_tickets.csv) and convert to AnomalyTicket format.
    
    Args:
        chat_logs_path: Path to chat_tickets.csv
        
    Returns:
        List of AnomalyTicket objects
    """
    import pandas as pd
    
    if not os.path.exists(chat_logs_path):
        return []
    
    # Load chat tickets CSV
    df = pd.read_csv(chat_logs_path)
    
    if len(df) == 0:
        return []
    
    # Load embedding model
    embedding_retriever = None
    try:
        index_builder = IndexBuilder(index_dir="indexes/")
        embedding_retriever = index_builder.load_embedding_index()
    except Exception as e:
        logger.warning("failed_to_load_embeddings_for_chat_logs", error=str(e))
    
    # Convert to AnomalyTicket format
    anomaly_tickets = []
    
    for _, row in df.iterrows():
        # Get embedding
        embedding = None
        if embedding_retriever:
            try:
                text = f"{row.get('short_description', '')} {row.get('description', '')}"
                text = text.strip()
                
                if text:
                    embedding_result = embedding_retriever.model.encode([text])[0]
                    embedding = embedding_result
            except Exception as e:
                logger.debug("failed_to_embed_chat_ticket", ticket_id=row.get('ticket_id'), error=str(e))
        
        # Parse created_at
        created_at = datetime.now()
        try:
            if pd.notna(row.get('created_at')):
                created_at = pd.to_datetime(row['created_at']).to_pydatetime()
        except:
            pass
        
        anomaly_ticket = AnomalyTicket(
            ticket_id=row.get('ticket_id', 'unknown'),
            created_at=created_at,
            category=row.get('category', 'General'),
            subcategory=row.get('subcategory', ''),
            priority=row.get('priority', 'Medium'),
            embedding=embedding,
        )
        
        anomaly_tickets.append(anomaly_ticket)
    
    logger.info("chat_logs_loaded_for_anomaly", 
                path=chat_logs_path,
                num_tickets=len(anomaly_tickets))
    
    return anomaly_tickets


def _load_tickets_for_anomaly_analysis(
    csv_path: str = "data/raw/tickets/sample_itsm_tickets.csv",
    anonymize: bool = True,
) -> List[AnomalyTicket]:
    """
    Load tickets from CSV and convert to AnomalyTicket format.
    
    Args:
        csv_path: Path to CSV file
        anonymize: Whether to anonymize PII
    
    Returns:
        List of AnomalyTicket objects with embeddings
    """
    # Load raw tickets
    raw_tickets = load_itsm_tickets_from_csv(csv_path)
    
    if not raw_tickets:
        raise ValueError(f"No tickets found in {csv_path}")
    
    # Anonymize if requested
    if anonymize:
        anonymizer = DataAnonymizer(anonymization_enabled=True)
        raw_tickets = anonymizer.anonymize_tickets(raw_tickets)
    
    # Load embedding model
    try:
        index_builder = IndexBuilder(index_dir="indexes/")
        embedding_retriever = index_builder.load_embedding_index()
        
        if not embedding_retriever:
            logger.warning("embedding_index_not_found", msg="Embeddings will be None")
            embedding_retriever = None
    except Exception as e:
        logger.warning("failed_to_load_embeddings", error=str(e))
        embedding_retriever = None
    
    # Convert to AnomalyTicket format
    anomaly_tickets = []
    
    for ticket in raw_tickets:
        # Get embedding for this ticket's content
        embedding = None
        if embedding_retriever:
            try:
                # Combine text fields for embedding
                # ITSMTicket is a Pydantic model, access attributes directly
                text = f"{ticket.short_description or ''} {ticket.resolution or ''}"
                text = text.strip()
                
                if text:
                    # Get embedding using the model
                    embedding_result = embedding_retriever.model.encode([text])[0]
                    embedding = embedding_result
            except Exception as e:
                logger.debug("failed_to_embed_ticket", ticket_id=ticket.ticket_id, error=str(e))
        
        anomaly_ticket = AnomalyTicket(
            ticket_id=ticket.ticket_id or 'unknown',
            created_at=ticket.created_at or datetime.now(),
            category=ticket.category,
            subcategory=ticket.subcategory,
            priority=ticket.priority,
            embedding=embedding,
        )
        
        anomaly_tickets.append(anomaly_ticket)
    
    return anomaly_tickets


def _run_anomaly_analysis_cached(
    csv_path: str = "data/raw/tickets/sample_itsm_tickets.csv",
    window_size_days: int = 1,
) -> tuple[List[WindowStats], List[AnomalyEvent]]:
    """
    Run anomaly analysis with caching.
    
    Args:
        csv_path: Path to ticket CSV
        window_size_days: Window size in days
    
    Returns:
        Tuple of (all_stats, events)
    """
    cache_key = f"{csv_path}_{window_size_days}D"
    
    # Check cache (expires after 5 minutes)
    if cache_key in _anomaly_cache:
        cached = _anomaly_cache[cache_key]
        age_seconds = (datetime.now() - cached['timestamp']).seconds
        
        if age_seconds < 300:  # 5 minutes
            logger.debug("using_cached_anomaly_results", age_seconds=age_seconds)
            return cached['stats'], cached['events']
    
    # Load tickets
    logger.info("loading_tickets_for_anomaly_analysis", csv_path=csv_path)
    tickets = _load_tickets_for_anomaly_analysis(csv_path, anonymize=True)
    
    logger.info("analyzing_ticket_stream", 
                total_tickets=len(tickets),
                window_size_days=window_size_days)
    
    # Run analysis
    window_size = timedelta(days=window_size_days)
    stats, events = analyze_ticket_stream(
        tickets=tickets,
        window_size=window_size,
        min_baseline_windows=3,
    )
    
    logger.info("anomaly_analysis_complete",
                total_windows=len(stats),
                anomaly_events=len(events))
    
    # Cache results
    _anomaly_cache[cache_key] = {
        'timestamp': datetime.now(),
        'stats': stats,
        'events': events,
    }
    
    return stats, events


# ============================================
# API ENDPOINTS
# ============================================

@router.get("/stats", response_model=AnomalyStatsResponse)
async def get_anomaly_stats(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze"),
    use_chat_logs: bool = Query(
        default=False,
        description="Use chat logs (chat_tickets.csv) instead of sample_itsm_tickets.csv"
    ),
) -> AnomalyStatsResponse:
    """
    Get anomaly statistics and drift metrics for recent time windows.
    
    This endpoint analyzes ticket distribution over the specified number of days,
    computing volume spikes, category shifts, and semantic drift for each window.
    
    Args:
        days: Number of days to analyze (1-30)
        
    Returns:
        Window statistics including:
        - Per-window ticket counts
        - Volume z-scores
        - Category divergence scores
        - Semantic drift scores
        - Combined anomaly scores and severity levels
    
    Example:
        GET /api/v1/anomaly/stats?days=7
    """
    try:
        logger.info("anomaly_stats_requested", days=days, use_chat_logs=use_chat_logs)
        
        # Determine data source
        if use_chat_logs:
            # Use chat logs for anomaly detection
            chat_logs_path = os.path.join(settings.chat_logs_dir, "chat_tickets.csv")
            if not os.path.exists(chat_logs_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Chat logs not found: {chat_logs_path}. Start using the chat interface to generate logs."
                )
            
            # Load chat logs and run analysis
            tickets = _load_chat_logs_for_anomaly(chat_logs_path)
            if not tickets:
                raise HTTPException(
                    status_code=400,
                    detail="No chat tickets found. Start using the chat interface to generate logs."
                )
            
            # Run analysis on chat logs
            window_size = timedelta(days=1)
            stats, events = analyze_ticket_stream(
                tickets=tickets,
                window_size=window_size,
                min_baseline_windows=3,
            )
        else:
            # Use default CSV
            stats, events = _run_anomaly_analysis_cached(
                csv_path="data/raw/tickets/sample_itsm_tickets.csv",
                window_size_days=1,
            )
        
        # Convert to response format
        window_responses = [
            WindowStatsResponse(
                window_start=s.window_start,
                window_end=s.window_end,
                total_tickets=s.total_tickets,
                volume_zscore=s.volume_z,
                category_divergence=s.category_divergence,
                semantic_drift=s.semantic_drift,
                combined_score=s.combined_score,
                severity=s.severity,
            )
            for s in stats
        ]
        
        # Compute summary
        total_tickets = sum(s.total_tickets for s in stats)
        anomalous_windows = sum(1 for s in stats if s.severity != "normal")
        
        severity_counts = {}
        for s in stats:
            severity_counts[s.severity] = severity_counts.get(s.severity, 0) + 1
        
        summary = {
            "total_windows": len(stats),
            "total_tickets": total_tickets,
            "anomalous_windows": anomalous_windows,
            "severity_distribution": severity_counts,
        }
        
        return AnomalyStatsResponse(
            windows=window_responses,
            summary=summary,
        )
        
    except Exception as e:
        logger.error("anomaly_stats_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute anomaly stats: {str(e)}"
        )


@router.get("/detect", response_model=AnomalyDetectResponse)
async def detect_anomalies(
    min_severity: str = Query(
        default="info",
        regex="^(info|warning|critical)$",
        description="Minimum severity to include"
    ),
    use_chat_logs: bool = Query(
        default=False,
        description="Use chat logs (chat_tickets.csv) instead of sample_itsm_tickets.csv"
    ),
) -> AnomalyDetectResponse:
    """
    Detect anomaly events in recent ticket streams.
    
    This endpoint identifies time windows with anomalous behavior based on:
    - Volume spikes (unusual ticket counts)
    - Category distribution shifts (changes in issue types)
    - Semantic drift (changes in content meaning)
    
    Args:
        min_severity: Minimum severity level to include ("info", "warning", "critical")
        
    Returns:
        List of detected anomaly events with:
        - Time window
        - Severity level
        - Combined anomaly score
        - Detailed reasons for the anomaly
    
    Example:
        GET /api/v1/anomaly/detect?min_severity=warning
    """
    try:
        logger.info("anomaly_detect_requested", min_severity=min_severity, use_chat_logs=use_chat_logs)
        
        # Determine data source
        if use_chat_logs:
            # Use chat logs for anomaly detection
            chat_logs_path = os.path.join(settings.chat_logs_dir, "chat_tickets.csv")
            if not os.path.exists(chat_logs_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Chat logs not found: {chat_logs_path}. Start using the chat interface to generate logs."
                )
            
            # Load chat logs and run analysis
            tickets = _load_chat_logs_for_anomaly(chat_logs_path)
            if not tickets:
                raise HTTPException(
                    status_code=400,
                    detail="No chat tickets found. Start using the chat interface to generate logs."
                )
            
            # Run analysis on chat logs
            window_size = timedelta(days=1)
            stats, events = analyze_ticket_stream(
                tickets=tickets,
                window_size=window_size,
                min_baseline_windows=3,
            )
        else:
            # Use default CSV
            stats, events = _run_anomaly_analysis_cached(
                csv_path="data/raw/tickets/sample_itsm_tickets.csv",
                window_size_days=1,
            )
        
        # Filter by severity
        severity_order = {"info": 0, "warning": 1, "critical": 2}
        min_level = severity_order.get(min_severity, 0)
        
        filtered_events = [
            e for e in events
            if severity_order.get(e.severity, 0) >= min_level
        ]
        
        # Convert to response format
        event_responses = [
            AnomalyEventResponse(
                window_start=e.window_start,
                window_end=e.window_end,
                severity=e.severity,
                score=e.score,
                reasons=e.reasons,
            )
            for e in filtered_events
        ]
        
        # Compute severity distribution
        severity_dist = {}
        for e in filtered_events:
            severity_dist[e.severity] = severity_dist.get(e.severity, 0) + 1
        
        return AnomalyDetectResponse(
            events=event_responses,
            total_windows=len(stats),
            anomalous_windows=len(filtered_events),
            severity_distribution=severity_dist,
        )
        
    except Exception as e:
        logger.error("anomaly_detect_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect anomalies: {str(e)}"
        )
