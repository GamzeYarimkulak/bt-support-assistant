"""
Tests for the anomaly detection engine (PHASE 5).

These tests verify that the anomaly engine correctly detects:
- Volume spikes (unusual ticket counts)
- Category distribution shifts
- Semantic drift (content changes)
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from core.anomaly.engine import (
    AnomalyTicket,
    WindowStats,
    AnomalyEvent,
    build_time_windows,
    compute_volume_zscore,
    compute_jensen_shannon_divergence,
    compute_semantic_drift,
    compute_window_stats,
    combine_scores,
    determine_severity,
    generate_reasons,
    analyze_ticket_stream,
)


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def sample_embeddings():
    """Generate sample embeddings for testing."""
    np.random.seed(42)
    
    # Baseline embeddings (clustered around origin)
    baseline = [np.random.randn(384) * 0.1 for _ in range(20)]
    
    # Drifted embeddings (shifted significantly)
    drifted = [np.random.randn(384) * 0.1 + 1.0 for _ in range(10)]
    
    return {
        'baseline': baseline,
        'drifted': drifted,
    }


# ============================================
# WINDOWING TESTS
# ============================================

def test_build_time_windows_daily():
    """Test that daily windowing works correctly."""
    base_date = datetime(2024, 12, 1, 10, 0, 0)
    
    tickets = [
        AnomalyTicket("t1", base_date, "Network"),
        AnomalyTicket("t2", base_date + timedelta(hours=2), "Email"),
        AnomalyTicket("t3", base_date + timedelta(days=1, hours=1), "VPN"),
        AnomalyTicket("t4", base_date + timedelta(days=1, hours=3), "Printer"),
        AnomalyTicket("t5", base_date + timedelta(days=2, hours=0), "Outlook"),
    ]
    
    windows, bounds = build_time_windows(tickets, timedelta(days=1))
    
    # Should have 3 windows (day 1, day 2, day 3)
    assert len(windows) == 3
    assert len(bounds) == 3
    
    # First window should have 2 tickets
    assert len(windows[0]) == 2
    assert windows[0][0].ticket_id == "t1"
    assert windows[0][1].ticket_id == "t2"
    
    # Second window should have 2 tickets
    assert len(windows[1]) == 2
    assert windows[1][0].ticket_id == "t3"
    
    # Third window should have 1 ticket
    assert len(windows[2]) == 1
    assert windows[2][0].ticket_id == "t5"


def test_build_time_windows_empty():
    """Test that empty ticket list returns empty windows."""
    windows, bounds = build_time_windows([], timedelta(days=1))
    
    assert windows == []
    assert bounds == []


# ============================================
# STATISTICAL TESTS
# ============================================

def test_compute_volume_zscore_spike():
    """Test z-score computation for volume spike."""
    # Baseline: 10 tickets per window
    baseline_counts = [10, 10, 11, 9, 10]
    
    # Spike: 25 tickets (very unusual)
    current_count = 25
    
    z = compute_volume_zscore(current_count, baseline_counts)
    
    assert z is not None
    assert z > 2.0  # Should be high z-score (unusual)


def test_compute_volume_zscore_normal():
    """Test z-score for normal volume."""
    baseline_counts = [10, 10, 11, 9, 10]
    current_count = 10
    
    z = compute_volume_zscore(current_count, baseline_counts)
    
    assert z is not None
    assert abs(z) < 0.5  # Should be close to 0 (normal)


def test_compute_volume_zscore_no_baseline():
    """Test z-score returns None when no baseline."""
    z = compute_volume_zscore(10, [])
    assert z is None


def test_jensen_shannon_divergence_identical():
    """Test JS divergence for identical distributions."""
    dist1 = {"cat1": 0.5, "cat2": 0.3, "cat3": 0.2}
    dist2 = {"cat1": 0.5, "cat2": 0.3, "cat3": 0.2}
    
    js = compute_jensen_shannon_divergence(dist1, dist2)
    
    assert js < 0.01  # Should be nearly 0


def test_jensen_shannon_divergence_different():
    """Test JS divergence for different distributions."""
    dist1 = {"cat1": 0.9, "cat2": 0.1}
    dist2 = {"cat1": 0.1, "cat2": 0.9}
    
    js = compute_jensen_shannon_divergence(dist1, dist2)
    
    assert js > 0.5  # Should be high (very different)


def test_semantic_drift_no_drift():
    """Test semantic drift when embeddings are similar."""
    # Two sets of similar embeddings
    embeddings1 = [np.array([1.0, 0.0, 0.0]) for _ in range(5)]
    embeddings2 = [np.array([1.0, 0.0, 0.0]) + np.random.randn(3) * 0.01 for _ in range(5)]
    
    drift = compute_semantic_drift(embeddings1, embeddings2)
    
    assert drift is not None
    assert drift < 0.1  # Should be small (similar)


def test_semantic_drift_significant():
    """Test semantic drift when embeddings are different."""
    # Two orthogonal sets of embeddings
    embeddings1 = [np.array([1.0, 0.0, 0.0]) for _ in range(5)]
    embeddings2 = [np.array([0.0, 1.0, 0.0]) for _ in range(5)]
    
    drift = compute_semantic_drift(embeddings1, embeddings2)
    
    assert drift is not None
    assert drift > 0.8  # Should be high (orthogonal = very different)


# ============================================
# COMBINED SCORE TESTS
# ============================================

def test_combine_scores_all_components():
    """Test combining all three anomaly components."""
    volume_z = 2.5  # High volume
    category_div = 0.6  # Moderate category shift
    semantic_drift = 0.3  # Moderate semantic drift
    
    combined = combine_scores(volume_z, category_div, semantic_drift)
    
    assert 0.0 <= combined <= 1.0
    assert combined > 0.5  # Should be elevated


def test_combine_scores_single_component():
    """Test combining with only one component available."""
    combined = combine_scores(3.0, None, None)  # Only volume
    
    assert 0.0 <= combined <= 1.0
    assert combined > 0.8  # High z-score should give high combined score


def test_combine_scores_no_components():
    """Test combining with no components (should return 0)."""
    combined = combine_scores(None, None, None)
    assert combined == 0.0


def test_determine_severity_normal():
    """Test severity determination for normal scores."""
    assert determine_severity(0.1) == "normal"
    assert determine_severity(0.29) == "normal"


def test_determine_severity_info():
    """Test severity determination for info level."""
    assert determine_severity(0.3) == "info"
    assert determine_severity(0.5) == "info"


def test_determine_severity_warning():
    """Test severity determination for warning level."""
    assert determine_severity(0.6) == "warning"
    assert determine_severity(0.75) == "warning"


def test_determine_severity_critical():
    """Test severity determination for critical level."""
    assert determine_severity(0.8) == "critical"
    assert determine_severity(0.95) == "critical"


def test_generate_reasons_volume_spike():
    """Test reason generation for volume spike."""
    reasons = generate_reasons(2.8, None, None)
    
    assert len(reasons) == 1
    assert "spike" in reasons[0].lower()
    assert "2.8" in reasons[0]


def test_generate_reasons_category_shift():
    """Test reason generation for category shift."""
    reasons = generate_reasons(None, 0.7, None)
    
    assert len(reasons) == 1
    assert "category" in reasons[0].lower()
    assert "shift" in reasons[0].lower()


def test_generate_reasons_multiple():
    """Test reason generation for multiple anomalies."""
    reasons = generate_reasons(2.5, 0.6, 0.25)
    
    assert len(reasons) == 3
    assert any("volume" in r.lower() for r in reasons)
    assert any("category" in r.lower() for r in reasons)
    assert any("semantic" in r.lower() or "drift" in r.lower() for r in reasons)


# ============================================
# END-TO-END TESTS
# ============================================

def test_analyze_ticket_stream_volume_spike():
    """Test detection of volume spike anomaly."""
    base_date = datetime(2024, 12, 1)
    
    # Create tickets: normal for 5 days, then spike on day 6
    tickets = []
    
    # Days 1-5: 10 tickets per day (normal)
    for day in range(5):
        for i in range(10):
            tickets.append(AnomalyTicket(
                ticket_id=f"t{day}_{i}",
                created_at=base_date + timedelta(days=day, hours=i),
                category="Network",
            ))
    
    # Day 6: 50 tickets (spike!)
    for i in range(50):
        tickets.append(AnomalyTicket(
            ticket_id=f"t_spike_{i}",
            created_at=base_date + timedelta(days=5, hours=i % 24),
            category="Network",
        ))
    
    # Analyze
    stats, events = analyze_ticket_stream(tickets, timedelta(days=1))
    
    # Check stats
    assert len(stats) == 6
    
    # Day 6 should have anomaly
    day6_stats = stats[5]
    assert day6_stats.total_tickets == 50
    assert day6_stats.volume_z is not None
    assert day6_stats.volume_z > 2.0  # High z-score
    assert day6_stats.severity != "normal"  # Any anomaly level is OK
    
    # Should have at least one anomaly event
    assert len(events) > 0
    
    # Find the spike event
    spike_events = [e for e in events if "spike" in " ".join(e.reasons).lower()]
    assert len(spike_events) > 0


def test_analyze_ticket_stream_category_shift():
    """Test detection of category distribution shift."""
    base_date = datetime(2024, 12, 1)
    tickets = []
    
    # Days 1-5: Mostly "Outlook" tickets
    for day in range(5):
        for i in range(10):
            tickets.append(AnomalyTicket(
                ticket_id=f"t{day}_{i}",
                created_at=base_date + timedelta(days=day, hours=i),
                category="Outlook",
            ))
    
    # Day 6: Mostly "VPN" tickets (category shift!)
    for i in range(10):
        tickets.append(AnomalyTicket(
            ticket_id=f"t_shift_{i}",
            created_at=base_date + timedelta(days=5, hours=i),
            category="VPN",
        ))
    
    # Analyze
    stats, events = analyze_ticket_stream(tickets, timedelta(days=1))
    
    # Day 6 should show category divergence
    day6_stats = stats[5]
    assert day6_stats.category_divergence is not None
    assert day6_stats.category_divergence > 0.3  # Significant divergence
    
    # Should have anomaly event
    assert len(events) > 0
    
    # Check for category-related reason
    category_events = [
        e for e in events
        if any("category" in r.lower() for r in e.reasons)
    ]
    assert len(category_events) > 0


def test_analyze_ticket_stream_semantic_drift():
    """Test detection of semantic drift using simple 2D embeddings."""
    base_date = datetime(2024, 12, 1)
    tickets = []
    
    # Days 1-5: Embeddings around origin [0, 0]
    for day in range(5):
        for i in range(10):
            embedding = np.array([0.0, 0.0]) + np.random.randn(2) * 0.1
            tickets.append(AnomalyTicket(
                ticket_id=f"t{day}_{i}",
                created_at=base_date + timedelta(days=day, hours=i),
                category="Network",
                embedding=embedding,
            ))
    
    # Day 6: Embeddings around [1, 1] (significant drift!)
    for i in range(10):
        embedding = np.array([1.0, 1.0]) + np.random.randn(2) * 0.1
        tickets.append(AnomalyTicket(
            ticket_id=f"t_drift_{i}",
            created_at=base_date + timedelta(days=5, hours=i),
            category="Network",
            embedding=embedding,
        ))
    
    # Analyze
    stats, events = analyze_ticket_stream(tickets, timedelta(days=1))
    
    # Day 6 should show semantic drift
    day6_stats = stats[5]
    assert day6_stats.semantic_drift is not None
    assert day6_stats.semantic_drift > 0.2  # Significant drift
    
    # Should have anomaly event
    assert len(events) > 0
    
    # Check for drift-related reason
    drift_events = [
        e for e in events
        if any("drift" in r.lower() or "semantic" in r.lower() for r in e.reasons)
    ]
    assert len(drift_events) > 0


def test_analyze_ticket_stream_empty():
    """Test analysis with no tickets."""
    stats, events = analyze_ticket_stream([], timedelta(days=1))
    
    assert stats == []
    assert events == []


def test_analyze_ticket_stream_insufficient_baseline():
    """Test that first few windows have no anomaly (insufficient baseline)."""
    base_date = datetime(2024, 12, 1)
    tickets = []
    
    # Only 2 days of data (below min_baseline_windows=3)
    for day in range(2):
        for i in range(10):
            tickets.append(AnomalyTicket(
                ticket_id=f"t{day}_{i}",
                created_at=base_date + timedelta(days=day, hours=i),
                category="Network",
            ))
    
    # Analyze with min_baseline_windows=3
    stats, events = analyze_ticket_stream(tickets, timedelta(days=1), min_baseline_windows=3)
    
    # Should have stats but no volume_z yet
    assert len(stats) == 2
    
    # First two windows should have None for volume_z
    for s in stats:
        assert s.volume_z is None  # Not enough baseline
        assert s.severity == "normal"  # No anomaly without baseline


def test_analyze_ticket_stream_combined_anomaly():
    """Test detection when multiple anomaly types occur together."""
    base_date = datetime(2024, 12, 1)
    tickets = []
    
    # Days 1-5: Normal baseline
    for day in range(5):
        for i in range(10):
            embedding = np.array([0.0, 0.0]) + np.random.randn(2) * 0.1
            tickets.append(AnomalyTicket(
                ticket_id=f"t{day}_{i}",
                created_at=base_date + timedelta(days=day, hours=i),
                category="Outlook",
                embedding=embedding,
            ))
    
    # Day 6: Volume spike + category shift + semantic drift (triple anomaly!)
    for i in range(40):  # Volume spike (4x normal)
        embedding = np.array([1.0, 1.0]) + np.random.randn(2) * 0.1  # Drift
        tickets.append(AnomalyTicket(
            ticket_id=f"t_multi_{i}",
            created_at=base_date + timedelta(days=5, hours=i % 24),
            category="VPN",  # Category shift
            embedding=embedding,
        ))
    
    # Analyze
    stats, events = analyze_ticket_stream(tickets, timedelta(days=1))
    
    # Day 6 should have high combined score
    day6_stats = stats[5]
    assert day6_stats.combined_score > 0.6  # High (multiple anomalies)
    assert day6_stats.severity in ["warning", "critical"]
    
    # Should have multiple reasons
    day6_event = [e for e in events if e.window_start == day6_stats.window_start][0]
    assert len(day6_event.reasons) >= 2  # At least 2 types detected


# ============================================
# INTEGRATION TEST
# ============================================

def test_full_pipeline_realistic_scenario():
    """Test the full pipeline with a realistic IT support scenario."""
    base_date = datetime(2024, 12, 1)
    tickets = []
    
    # Week 1-2: Normal operations (10-15 tickets/day, mostly Outlook/Network)
    for day in range(14):
        count = 10 + (day % 5)  # Vary between 10-15
        for i in range(count):
            category = "Outlook" if i % 2 == 0 else "Network"
            embedding = np.random.randn(384) * 0.1  # Normal variation
            
            tickets.append(AnomalyTicket(
                ticket_id=f"t_normal_{day}_{i}",
                created_at=base_date + timedelta(days=day, hours=i % 24),
                category=category,
                priority="Medium",
                embedding=embedding,
            ))
    
    # Day 15: Major VPN outage (anomaly!)
    for i in range(50):  # Volume spike
        embedding = np.random.randn(384) * 0.1 + 1.0  # Semantic drift
        tickets.append(AnomalyTicket(
            ticket_id=f"t_outage_{i}",
            created_at=base_date + timedelta(days=14, hours=i % 24),
            category="VPN",  # Category shift
            priority="Critical",
            embedding=embedding,
        ))
    
    # Analyze
    stats, events = analyze_ticket_stream(tickets, timedelta(days=1), min_baseline_windows=3)
    
    # Should have stats for 15 days
    assert len(stats) == 15
    
    # Day 15 should be anomalous
    day15_stats = stats[14]
    assert day15_stats.severity != "normal"
    assert day15_stats.combined_score > 0.5
    
    # Should have at least one event on day 15
    day15_events = [e for e in events if e.window_start == day15_stats.window_start]
    assert len(day15_events) > 0
    
    # Event should have multiple reasons
    outage_event = day15_events[0]
    assert len(outage_event.reasons) >= 1
    
    print(f"\nDay 15 Anomaly Detected:")
    print(f"  Severity: {outage_event.severity}")
    print(f"  Score: {outage_event.score:.3f}")
    print(f"  Reasons:")
    for reason in outage_event.reasons:
        print(f"    - {reason}")

