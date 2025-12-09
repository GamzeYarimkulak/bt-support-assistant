"""
Simple anomaly detection pipeline for ITSM tickets.
Detects semantic drift and volume anomalies over time windows.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
import structlog

from data_pipeline.ingestion import ITSMTicket
from core.anomaly.drift_detector import WindowDriftDetector, DriftScore
from core.anomaly.feature_extractor import FeatureExtractor

logger = structlog.get_logger()


def run_anomaly_pipeline(
    tickets: List[ITSMTicket],
    window_size_hours: int = 24,
    min_reference_windows: int = 5
) -> Dict[str, Any]:
    """
    Run anomaly detection pipeline on ITSM tickets.
    
    Args:
        tickets: List of ITSM tickets
        window_size_hours: Size of time windows in hours
        min_reference_windows: Minimum windows needed for baseline
        
    Returns:
        Dictionary with anomaly detection results
    """
    logger.info("anomaly_pipeline_started",
               num_tickets=len(tickets),
               window_size_hours=window_size_hours)
    
    if len(tickets) < 10:
        logger.warning("insufficient_tickets_for_anomaly_detection", 
                      num_tickets=len(tickets))
        return {
            "windows": [],
            "drift_scores": [],
            "summary": {
                "total_windows": 0,
                "total_tickets": 0,
                "anomalous_windows": 0
            }
        }
    
    # Step 1: Group tickets into time windows
    windows = _create_time_windows(tickets, window_size_hours)
    
    if len(windows) < min_reference_windows:
        logger.warning("insufficient_windows_for_baseline",
                      num_windows=len(windows),
                      min_required=min_reference_windows)
        return {
            "windows": windows,
            "drift_scores": [],
            "summary": {
                "total_windows": len(windows),
                "total_tickets": len(tickets),
                "anomalous_windows": 0
            }
        }
    
    # Step 2: Extract features for each window
    feature_extractor = FeatureExtractor()
    window_stats = []
    
    for window in windows:
        if len(window["tickets"]) == 0:
            continue
            
        # Extract embeddings
        texts = [t.short_description + " " + t.description 
                for t in window["tickets"]]
        embeddings = feature_extractor.extract_embeddings(texts)
        centroid = np.mean(embeddings, axis=0)
        
        # Category counts
        category_counts = {}
        for ticket in window["tickets"]:
            cat = ticket.category or "Unknown"
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        window_stat = type('WindowStats', (), {
            'window_start': window["start"],
            'window_end': window["end"],
            'total_tickets': len(window["tickets"]),
            'counts_by_category': category_counts,
            'centroid_embedding': centroid
        })()
        
        window_stats.append(window_stat)
    
    # Step 3: Fit baseline on first N windows
    detector = WindowDriftDetector(min_reference_windows=min_reference_windows)
    reference_windows = window_stats[:min_reference_windows]
    test_windows = window_stats[min_reference_windows:]
    
    detector.fit_reference(reference_windows)
    
    # Step 4: Score remaining windows
    drift_scores = []
    anomalous_count = 0
    
    for window_stat in test_windows:
        score = detector.score_window(window_stat)
        drift_scores.append(score)
        
        # Flag as anomalous if combined score > threshold
        if score.combined_score > 0.5:
            anomalous_count += 1
            logger.info("anomalous_window_detected",
                       window_start=score.window_start,
                       combined_score=score.combined_score)
    
    # Step 5: Build result
    result = {
        "windows": [
            {
                "window_start": w["start"].isoformat(),
                "window_end": w["end"].isoformat(),
                "total_tickets": len(w["tickets"]),
                "categories": list(set(t.category for t in w["tickets"]))
            }
            for w in windows
        ],
        "drift_scores": [
            {
                "window_start": s.window_start.isoformat(),
                "window_end": s.window_end.isoformat(),
                "volume_zscore": s.volume_zscore,
                "category_divergence": s.category_divergence,
                "embedding_shift": s.embedding_shift,
                "combined_score": s.combined_score
            }
            for s in drift_scores
        ],
        "summary": {
            "total_windows": len(windows),
            "total_tickets": len(tickets),
            "anomalous_windows": anomalous_count,
            "baseline_windows": len(reference_windows),
            "tested_windows": len(test_windows)
        }
    }
    
    logger.info("anomaly_pipeline_completed",
               total_windows=len(windows),
               anomalous_windows=anomalous_count)
    
    return result


def _create_time_windows(
    tickets: List[ITSMTicket],
    window_size_hours: int
) -> List[Dict[str, Any]]:
    """
    Group tickets into time windows.
    
    Args:
        tickets: List of tickets
        window_size_hours: Window size in hours
        
    Returns:
        List of window dictionaries
    """
    if not tickets:
        return []
    
    # Sort by creation time
    sorted_tickets = sorted(tickets, key=lambda t: t.created_at)
    
    # Find time range
    start_time = sorted_tickets[0].created_at
    end_time = sorted_tickets[-1].created_at
    
    # Create windows
    windows = []
    current_start = start_time
    window_delta = timedelta(hours=window_size_hours)
    
    while current_start < end_time:
        current_end = current_start + window_delta
        
        # Get tickets in this window
        window_tickets = [
            t for t in sorted_tickets
            if current_start <= t.created_at < current_end
        ]
        
        windows.append({
            "start": current_start,
            "end": current_end,
            "tickets": window_tickets
        })
        
        current_start = current_end
    
    logger.debug("time_windows_created",
                num_windows=len(windows),
                window_size_hours=window_size_hours)
    
    return windows


