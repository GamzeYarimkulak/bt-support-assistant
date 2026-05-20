"""
Tests for anomaly detection (PHASE 5).
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from data_pipeline.ingestion import ITSMTicket
from core.anomaly.feature_extractor import (
    TicketFeatures,
    WindowStats,
    extract_ticket_features,
    aggregate_time_windows
)
from core.anomaly.drift_detector import WindowDriftDetector, DriftScore
from core.anomaly.anomaly_detector import (
    ThresholdAnomalyDetector,
    AnomalyThresholds,
    AnomalyEvent
)


class MockEmbedder:
    """Mock embedder for testing without loading real model."""
    
    def __init__(self, embedding_dim=384):
        self.embedding_dim = embedding_dim
    
    def encode(self, texts, normalize=True):
        """Return deterministic fake embeddings."""
        # Use hash of text for deterministic but varied embeddings
        embeddings = []
        for text in texts:
            # Simple hash-based embedding
            hash_val = hash(text)
            np.random.seed(abs(hash_val) % (2**32))
            emb = np.random.randn(self.embedding_dim)
            if normalize:
                emb = emb / np.linalg.norm(emb)
            embeddings.append(emb)
        return np.array(embeddings)


class TestFeatureExtraction:
    """Tests for ticket feature extraction."""
    
    def test_extract_ticket_features(self):
        """Test basic feature extraction from tickets."""
        tickets = [
            ITSMTicket(
                ticket_id="T001",
                created_at=datetime(2025, 1, 1, 10, 0),
                category="Hardware",
                priority="High",
                short_description="Laptop broken",
                description="Screen cracked",
                resolution="Replaced screen"
            ),
            ITSMTicket(
                ticket_id="T002",
                created_at=datetime(2025, 1, 1, 11, 0),
                category="Software",
                priority="Medium",
                short_description="VPN issue",
                description="Cannot connect",
                resolution="Reset credentials"
            )
        ]
        
        embedder = MockEmbedder()
        features = extract_ticket_features(tickets, embedder)
        
        assert len(features) == 2
        assert features[0].ticket_id == "T001"
        assert features[0].category == "Hardware"
        assert features[0].priority == "High"
        assert features[0].embedding.shape == (384,)
        
        assert features[1].ticket_id == "T002"
        assert features[1].category == "Software"
    
    def test_extract_features_empty_list(self):
        """Test that empty ticket list returns empty features."""
        embedder = MockEmbedder()
        features = extract_ticket_features([], embedder)
        
        assert features == []


class TestTimeWindowAggregation:
    """Tests for time window aggregation."""
    
    def test_aggregate_time_windows_daily(self):
        """Test aggregation into daily windows."""
        # Create features spanning 3 days
        base_embedding = np.random.randn(384)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)
        
        features = [
            TicketFeatures("T001", datetime(2025, 1, 1, 10, 0), "Hardware", "High", base_embedding),
            TicketFeatures("T002", datetime(2025, 1, 1, 14, 0), "Software", "Medium", base_embedding),
            TicketFeatures("T003", datetime(2025, 1, 2, 9, 0), "Network", "Low", base_embedding),
            TicketFeatures("T004", datetime(2025, 1, 3, 11, 0), "Hardware", "High", base_embedding),
        ]
        
        windows = aggregate_time_windows(features, window="1D")
        
        # Should have 3 windows (one per day)
        assert len(windows) == 3
        
        # Check first window
        assert windows[0].window_start.date() == datetime(2025, 1, 1).date()
        assert windows[0].total_tickets == 2
        assert windows[0].counts_by_category["Hardware"] == 1
        assert windows[0].counts_by_category["Software"] == 1
        
        # Check second window
        assert windows[1].total_tickets == 1
        assert windows[1].counts_by_category["Network"] == 1
        
        # Check third window
        assert windows[2].total_tickets == 1
    
    def test_aggregate_windows_computes_centroid(self):
        """Test that centroid embeddings are computed correctly."""
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([0.0, 1.0, 0.0])
        
        features = [
            TicketFeatures("T001", datetime(2025, 1, 1, 10, 0), "A", "High", emb1),
            TicketFeatures("T002", datetime(2025, 1, 1, 11, 0), "B", "Low", emb2),
        ]
        
        windows = aggregate_time_windows(features, window="1D")
        
        assert len(windows) == 1
        # Centroid should be average of emb1 and emb2
        expected_centroid = np.array([0.5, 0.5, 0.0])
        np.testing.assert_array_almost_equal(windows[0].centroid_embedding, expected_centroid)
    
    def test_aggregate_empty_features(self):
        """Test that empty features list returns empty windows."""
        windows = aggregate_time_windows([], window="1D")
        
        assert windows == []


class TestDriftDetector:
    """Tests for drift detection."""
    
    @pytest.fixture
    def baseline_windows(self):
        """Create baseline windows with stable patterns."""
        windows = []
        base_emb = np.array([1.0, 0.0] + [0.0] * 382)
        
        for i in range(7):  # 7 days of baseline
            ws = WindowStats(
                window_start=datetime(2025, 1, i+1, 0, 0),
                window_end=datetime(2025, 1, i+2, 0, 0),
                total_tickets=10,  # Stable volume
                counts_by_category={"Hardware": 5, "Software": 5},  # Stable distribution
                counts_by_priority={"High": 3, "Medium": 7},
                centroid_embedding=base_emb.copy()
            )
            windows.append(ws)
        
        return windows
    
    def test_drift_detector_fit_reference(self, baseline_windows):
        """Test fitting drift detector on reference windows."""
        detector = WindowDriftDetector(min_reference_windows=5)
        
        # Should fit successfully
        detector.fit_reference(baseline_windows)
        
        # Check that baseline stats were computed
        assert detector.baseline_volume_mean == 10.0
        assert detector.baseline_volume_std >= 0.0
        assert detector.baseline_category_dist is not None
        assert detector.baseline_centroid is not None
    
    def test_drift_detector_insufficient_windows(self):
        """Test that detector raises error with too few windows."""
        detector = WindowDriftDetector(min_reference_windows=5)
        
        with pytest.raises(ValueError, match="at least"):
            detector.fit_reference([])  # Empty list
    
    def test_drift_detector_volume_spike(self, baseline_windows):
        """Test detection of volume spike."""
        detector = WindowDriftDetector(min_reference_windows=5)
        detector.fit_reference(baseline_windows)
        
        # Create window with volume spike (50 tickets vs baseline of 10)
        spike_window = WindowStats(
            window_start=datetime(2025, 1, 8, 0, 0),
            window_end=datetime(2025, 1, 9, 0, 0),
            total_tickets=50,  # Large spike!
            counts_by_category={"Hardware": 25, "Software": 25},
            counts_by_priority={"High": 15, "Medium": 35},
            centroid_embedding=baseline_windows[0].centroid_embedding.copy()
        )
        
        score = detector.score_window(spike_window)
        
        assert isinstance(score, DriftScore)
        assert score.volume_zscore > 2.0  # Should have high z-score
        assert score.combined_score > 0.0
    
    def test_drift_detector_category_shift(self, baseline_windows):
        """Test detection of category distribution shift."""
        detector = WindowDriftDetector(min_reference_windows=5)
        detector.fit_reference(baseline_windows)
        
        # Create window with shifted category distribution
        shifted_window = WindowStats(
            window_start=datetime(2025, 1, 8, 0, 0),
            window_end=datetime(2025, 1, 9, 0, 0),
            total_tickets=10,  # Same volume
            counts_by_category={"Hardware": 1, "Software": 9},  # Shifted distribution!
            counts_by_priority={"High": 3, "Medium": 7},
            centroid_embedding=baseline_windows[0].centroid_embedding.copy()
        )
        
        score = detector.score_window(shifted_window)
        
        assert score.category_divergence > 0.0  # Should detect divergence
    
    def test_drift_detector_embedding_shift(self, baseline_windows):
        """Test detection of semantic/embedding drift."""
        detector = WindowDriftDetector(min_reference_windows=5)
        detector.fit_reference(baseline_windows)
        
        # Create window with different embedding
        shifted_emb = np.array([0.0, 1.0] + [0.0] * 382)  # Orthogonal to baseline
        
        shifted_window = WindowStats(
            window_start=datetime(2025, 1, 8, 0, 0),
            window_end=datetime(2025, 1, 9, 0, 0),
            total_tickets=10,
            counts_by_category={"Hardware": 5, "Software": 5},
            counts_by_priority={"High": 3, "Medium": 7},
            centroid_embedding=shifted_emb  # Different embedding!
        )
        
        score = detector.score_window(shifted_window)
        
        assert score.embedding_shift > 0.0  # Should detect shift


class TestAnomalyDetector:
    """Tests for anomaly event detection."""
    
    def test_threshold_detector_initialization(self):
        """Test detector initialization with custom thresholds."""
        thresholds = AnomalyThresholds(warning=1.0, critical=2.0)
        detector = ThresholdAnomalyDetector(thresholds=thresholds)
        
        assert detector.thresholds.warning == 1.0
        assert detector.thresholds.critical == 2.0
    
    def test_detect_no_anomaly(self):
        """Test that low drift scores produce info-level events."""
        detector = ThresholdAnomalyDetector(
            thresholds=AnomalyThresholds(warning=0.5, critical=0.75)
        )
        
        # Low drift score
        scores = [
            DriftScore(
                window_start=datetime(2025, 1, 1),
                window_end=datetime(2025, 1, 2),
                volume_zscore=0.1,
                category_divergence=0.01,
                embedding_shift=0.01,
                combined_score=0.1  # Below warning threshold
            )
        ]
        
        events = detector.detect(scores)
        
        assert len(events) == 1
        assert events[0].severity == "info"
        assert events[0].score == 0.1
    
    def test_detect_warning_level(self):
        """Test detection of warning-level anomalies."""
        detector = ThresholdAnomalyDetector(
            thresholds=AnomalyThresholds(warning=0.5, critical=0.75)
        )
        
        scores = [
            DriftScore(
                window_start=datetime(2025, 1, 1),
                window_end=datetime(2025, 1, 2),
                volume_zscore=2.5,  # Moderate spike
                category_divergence=0.3,
                embedding_shift=0.1,
                combined_score=0.6  # Between warning and critical
            )
        ]
        
        events = detector.detect(scores)
        
        assert len(events) == 1
        assert events[0].severity == "warning"
        assert len(events[0].reasons) > 0
        assert any("z-score" in r.lower() for r in events[0].reasons)
    
    def test_detect_critical_level(self):
        """Test detection of critical-level anomalies."""
        detector = ThresholdAnomalyDetector(
            thresholds=AnomalyThresholds(warning=0.5, critical=0.75)
        )
        
        scores = [
            DriftScore(
                window_start=datetime(2025, 1, 1),
                window_end=datetime(2025, 1, 2),
                volume_zscore=5.0,  # Large spike
                category_divergence=0.6,
                embedding_shift=0.4,
                combined_score=0.9  # Above critical
            )
        ]
        
        events = detector.detect(scores)
        
        assert len(events) == 1
        assert events[0].severity == "critical"
        assert len(events[0].reasons) >= 2  # Should have multiple reasons
    
    def test_detect_multiple_windows(self):
        """Test detection across multiple windows."""
        # Use thresholds that match the test's combined_score values
        detector = ThresholdAnomalyDetector(
            thresholds=AnomalyThresholds(warning=0.5, critical=0.75)
        )
        
        scores = [
            DriftScore(datetime(2025, 1, 1), datetime(2025, 1, 2), 0.1, 0.01, 0.01, 0.1),
            DriftScore(datetime(2025, 1, 2), datetime(2025, 1, 3), 3.0, 0.5, 0.3, 0.65),
            DriftScore(datetime(2025, 1, 3), datetime(2025, 1, 4), 0.2, 0.02, 0.02, 0.15),
        ]
        
        events = detector.detect(scores)
        
        assert len(events) == 3
        # Second window should be warning (0.65 is between 0.5 and 0.75)
        assert events[1].severity == "warning"
        # First and third should be info
        assert events[0].severity == "info"
        assert events[2].severity == "info"


class TestAnomalyStructures:
    """Tests for anomaly dataclass structures."""
    
    def test_ticket_features_creation(self):
        """Test TicketFeatures dataclass."""
        emb = np.array([0.1, 0.2, 0.3])
        feature = TicketFeatures(
            ticket_id="T001",
            created_at=datetime(2025, 1, 1),
            category="Hardware",
            priority="High",
            embedding=emb
        )
        
        assert feature.ticket_id == "T001"
        assert isinstance(feature.embedding, np.ndarray)
        np.testing.assert_array_equal(feature.embedding, emb)
    
    def test_window_stats_creation(self):
        """Test WindowStats dataclass."""
        centroid = np.array([0.5, 0.5])
        ws = WindowStats(
            window_start=datetime(2025, 1, 1),
            window_end=datetime(2025, 1, 2),
            total_tickets=10,
            counts_by_category={"A": 5, "B": 5},
            counts_by_priority={"High": 3, "Low": 7},
            centroid_embedding=centroid
        )
        
        assert ws.total_tickets == 10
        assert ws.counts_by_category["A"] == 5
        assert isinstance(ws.centroid_embedding, np.ndarray)
    
    def test_drift_score_structure(self):
        """Test DriftScore dataclass."""
        score = DriftScore(
            window_start=datetime(2025, 1, 1),
            window_end=datetime(2025, 1, 2),
            volume_zscore=2.5,
            category_divergence=0.3,
            embedding_shift=0.2,
            combined_score=0.6
        )
        
        assert score.volume_zscore == 2.5
        assert score.combined_score == 0.6
    
    def test_anomaly_event_structure(self):
        """Test AnomalyEvent dataclass."""
        event = AnomalyEvent(
            window_start=datetime(2025, 1, 1),
            window_end=datetime(2025, 1, 2),
            severity="warning",
            score=0.7,
            reasons=["Volume spike detected", "Category shift"]
        )
        
        assert event.severity == "warning"
        assert len(event.reasons) == 2

