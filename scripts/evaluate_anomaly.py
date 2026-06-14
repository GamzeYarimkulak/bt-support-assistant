"""
Evaluate anomaly detection output against curated ground truth windows.

Inputs:
- data/evaluation/anomaly/anomaly_ground_truth.csv
- data/evaluation/anomaly/synthetic_bt_anomaly_dataset_codex.csv
- data/processed/tickets.parquet

Output:
- data/evaluation/anomaly/anomaly_metrics.json

This script does not modify the anomaly engine. It converts processed tickets
to the engine input model, runs daily-window detection, and compares detected
events with the curated ground-truth windows.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.anomaly.engine import AnomalyTicket, analyze_ticket_stream


DEFAULT_GROUND_TRUTH = PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "anomaly_ground_truth.csv"
DEFAULT_SYNTHETIC = PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "synthetic_bt_anomaly_dataset_codex.csv"
DEFAULT_TICKETS = PROJECT_ROOT / "data" / "processed" / "tickets.parquet"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "anomaly_metrics.json"
DEFAULT_DAY_LABELS = PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "anomaly_day_labels.csv"
DEFAULT_FALSE_POSITIVES = (
    PROJECT_ROOT / "data" / "evaluation" / "anomaly" / "anomaly_false_positive_candidates.csv"
)


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def as_iso(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def parse_embedding(value: Any) -> np.ndarray | None:
    """Parse an embedding stored as a parquet list/array or JSON string."""
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        return value.astype(np.float32)
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return np.asarray(value, dtype=np.float32)
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text or text.casefold() in {"nan", "none", "null"}:
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, list) or not parsed:
        return None

    try:
        return np.asarray(parsed, dtype=np.float32)
    except (TypeError, ValueError):
        return None


def load_ground_truth(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"window_start", "window_end", "anomaly_type", "expected_severity"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Ground-truth file missing columns: {sorted(missing)}")

    frame = frame.copy()
    frame["window_start"] = pd.to_datetime(frame["window_start"], errors="coerce")
    frame["window_end"] = pd.to_datetime(frame["window_end"], errors="coerce")
    if frame["window_start"].isna().any() or frame["window_end"].isna().any():
        raise ValueError("Ground-truth file contains invalid window_start/window_end values")

    return frame.sort_values("window_start").reset_index(drop=True)


def load_day_labels(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()

    frame = pd.read_csv(path)
    required = {"date", "is_anomaly", "expected_severity"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Day-label file missing columns: {sorted(missing)}")

    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    if frame["date"].isna().any():
        raise ValueError("Day-label file contains invalid date values")

    frame["is_anomaly"] = frame["is_anomaly"].map(
        lambda value: str(value).strip().casefold() in {"true", "1", "yes", "y"}
    )
    frame["expected_severity"] = frame["expected_severity"].map(safe_text).str.casefold()
    return frame.sort_values("date").reset_index(drop=True)


def load_synthetic_summary(path: Path, ground_truth: pd.DataFrame) -> dict[str, Any]:
    if not path.exists():
        return {"available": False, "reason": f"File not found: {path}"}

    frame = pd.read_csv(path)
    summary: dict[str, Any] = {
        "available": True,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
    }

    if {"date", "category", "anomaly_type", "severity"}.issubset(frame.columns):
        frame = frame.copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
        summary["anomaly_type_distribution"] = frame["anomaly_type"].value_counts(dropna=False).to_dict()
        summary["severity_distribution"] = frame["severity"].value_counts(dropna=False).to_dict()

        rows_on_ground_truth_dates = []
        for _, gt in ground_truth.iterrows():
            gt_date = gt["window_start"].date()
            matching_rows = frame[frame["date"] == gt_date]
            rows_on_ground_truth_dates.append(
                {
                    "ground_truth_date": gt_date.isoformat(),
                    "ground_truth_type": safe_text(gt.get("anomaly_type")),
                    "synthetic_rows": matching_rows[
                        ["date", "category", "ticket_count", "anomaly_type", "severity"]
                    ].astype(str).to_dict(orient="records"),
                }
            )
        summary["rows_on_ground_truth_dates"] = rows_on_ground_truth_dates
        summary["alignment_note"] = (
            "Synthetic aggregate rows are daily category/count labels. They are not "
            "a one-to-one output format match for the current ticket-stream engine."
        )

    return summary


def load_tickets_for_engine(path: Path, start: datetime, end: datetime) -> list[AnomalyTicket]:
    frame = pd.read_parquet(path)
    required = {"ticket_id", "created_at", "category"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Processed tickets parquet missing columns: {sorted(missing)}")

    frame = frame.copy()
    frame["created_at"] = pd.to_datetime(frame["created_at"], errors="coerce")
    frame = frame[
        frame["created_at"].notna()
        & (frame["created_at"] >= start)
        & (frame["created_at"] <= end)
    ].copy()

    embedding_column = None
    if "embedding" in frame.columns:
        embedding_column = "embedding"
    elif "embedding_vector" in frame.columns:
        embedding_column = "embedding_vector"

    tickets: list[AnomalyTicket] = []
    for _, row in frame.iterrows():
        tickets.append(
            AnomalyTicket(
                ticket_id=safe_text(row.get("ticket_id")) or safe_text(row.get("id")),
                created_at=row["created_at"].to_pydatetime(),
                category=safe_text(row.get("category")),
                subcategory=safe_text(row.get("subcategory")),
                priority=safe_text(row.get("priority")),
                embedding=parse_embedding(row.get(embedding_column)) if embedding_column else None,
            )
        )

    return tickets


def windows_overlap(
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> bool:
    # Treat time windows as half-open intervals: [start, end).
    # Adjacent daily windows that only touch at midnight should not match.
    return left_start < right_end and right_start < left_end


def event_to_dict(event: Any) -> dict[str, Any]:
    data = asdict(event)
    data["window_start"] = as_iso(data.get("window_start"))
    data["window_end"] = as_iso(data.get("window_end"))
    return data


def stat_to_dict(stat: Any) -> dict[str, Any]:
    data = asdict(stat)
    data["window_start"] = as_iso(data.get("window_start"))
    data["window_end"] = as_iso(data.get("window_end"))
    return data


def evaluate_matches(ground_truth: pd.DataFrame, detected_events: list[Any]) -> dict[str, Any]:
    matched_detection_indexes: set[int] = set()
    matches: list[dict[str, Any]] = []

    for gt_index, gt in ground_truth.iterrows():
        gt_start = gt["window_start"].to_pydatetime()
        gt_end = gt["window_end"].to_pydatetime()
        candidate_index = None

        for event_index, event in enumerate(detected_events):
            if event_index in matched_detection_indexes:
                continue
            if windows_overlap(gt_start, gt_end, event.window_start, event.window_end):
                candidate_index = event_index
                break

        if candidate_index is None:
            matches.append(
                {
                    "ground_truth_index": int(gt_index),
                    "ground_truth_window_start": gt_start.isoformat(),
                    "ground_truth_window_end": gt_end.isoformat(),
                    "ground_truth_type": safe_text(gt.get("anomaly_type")),
                    "expected_severity": safe_text(gt.get("expected_severity")),
                    "matched": False,
                    "note": "No detected engine event overlapped this ground-truth window.",
                }
            )
            continue

        matched_detection_indexes.add(candidate_index)
        event = detected_events[candidate_index]
        expected_severity = safe_text(gt.get("expected_severity")).casefold()
        detected_severity = safe_text(event.severity).casefold()
        reasons_text = " ".join(event.reasons).casefold()
        gt_type = safe_text(gt.get("anomaly_type")).casefold()

        if "semantic" in gt_type:
            type_compatible = "semantic" in reasons_text
        elif "category" in gt_type or "shift" in gt_type:
            type_compatible = "category" in reasons_text
        elif "volume" in gt_type:
            type_compatible = "volume" in reasons_text
        else:
            type_compatible = True

        matches.append(
            {
                "ground_truth_index": int(gt_index),
                "ground_truth_window_start": gt_start.isoformat(),
                "ground_truth_window_end": gt_end.isoformat(),
                "ground_truth_type": safe_text(gt.get("anomaly_type")),
                "expected_severity": safe_text(gt.get("expected_severity")),
                "matched": True,
                "detected_event_index": int(candidate_index),
                "detected_window_start": event.window_start.isoformat(),
                "detected_window_end": event.window_end.isoformat(),
                "detected_severity": event.severity,
                "detected_score": float(event.score),
                "detected_reasons": list(event.reasons),
                "severity_matches_exactly": expected_severity == detected_severity,
                "type_compatible_from_reason_text": bool(type_compatible),
            }
        )

    true_positives = sum(1 for match in matches if match["matched"])
    false_positives = len(detected_events) - true_positives
    false_negatives = len(ground_truth) - true_positives

    precision = true_positives / len(detected_events) if detected_events else 0.0
    recall = true_positives / len(ground_truth) if len(ground_truth) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "true_positives": int(true_positives),
        "false_positives": int(false_positives),
        "false_negatives": int(false_negatives),
        "detected_events": int(len(detected_events)),
        "ground_truth_events": int(len(ground_truth)),
        "matched_detection_indexes": sorted(matched_detection_indexes),
        "matches": matches,
    }


def calculate_date_level_recall(ground_truth: pd.DataFrame, detected_events: list[Any]) -> float:
    """Measure whether each ground-truth event date has at least one detected event date."""
    if len(ground_truth) == 0:
        return 0.0

    detected_dates = {event.window_start.date() for event in detected_events}
    matched_dates = 0
    for _, gt in ground_truth.iterrows():
        if gt["window_start"].date() in detected_dates:
            matched_dates += 1

    return float(matched_dates / len(ground_truth))


def stats_by_date(stats: list[Any]) -> dict[Any, Any]:
    return {stat.window_start.date(): stat for stat in stats}


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def severity_rank(value: str) -> int:
    return {"normal": 0, "info": 1, "warning": 2, "critical": 3}.get(value.casefold(), 0)


def build_day_level_metrics(
    day_labels: pd.DataFrame,
    stats: list[Any],
    score_threshold: float = 0.3,
) -> dict[str, Any] | None:
    if day_labels.empty:
        return None

    by_date = stats_by_date(stats)
    rows: list[dict[str, Any]] = []
    tp = fp = fn = tn = 0
    severity_exact = 0
    positive_count = 0

    for _, label in day_labels.iterrows():
        date_value = label["date"]
        expected_positive = bool(label["is_anomaly"])
        expected_severity = safe_text(label.get("expected_severity")).casefold() or "normal"
        stat = by_date.get(date_value)
        score = float(getattr(stat, "combined_score", 0.0)) if stat is not None else 0.0
        engine_severity = safe_text(getattr(stat, "severity", "normal")) if stat is not None else "normal"
        predicted_positive = score >= score_threshold

        if expected_positive and predicted_positive:
            tp += 1
        elif expected_positive and not predicted_positive:
            fn += 1
        elif not expected_positive and predicted_positive:
            fp += 1
        else:
            tn += 1

        if expected_positive:
            positive_count += 1
            if severity_rank(engine_severity) == severity_rank(expected_severity):
                severity_exact += 1

        rows.append(
            {
                "date": date_value.isoformat(),
                "expected_is_anomaly": expected_positive,
                "predicted_is_anomaly": predicted_positive,
                "expected_severity": expected_severity,
                "engine_severity": engine_severity,
                "combined_score": score,
                "volume_zscore": getattr(stat, "volume_z", None) if stat is not None else None,
                "category_divergence": getattr(stat, "category_divergence", None) if stat is not None else None,
                "semantic_drift": getattr(stat, "semantic_drift", None) if stat is not None else None,
                "anomaly_type": safe_text(label.get("anomaly_type")),
                "event_id": safe_text(label.get("event_id")),
            }
        )

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    specificity = safe_divide(tn, tn + fp)
    accuracy = safe_divide(tp + tn, tp + fp + fn + tn)
    f1 = safe_divide(2 * precision * recall, precision + recall)

    return {
        "score_threshold": float(score_threshold),
        "label_count": int(len(day_labels)),
        "positive_day_count": int(day_labels["is_anomaly"].sum()),
        "negative_day_count": int((~day_labels["is_anomaly"]).sum()),
        "true_positive_days": int(tp),
        "false_positive_days": int(fp),
        "false_negative_days": int(fn),
        "true_negative_days": int(tn),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "specificity": float(specificity),
        "accuracy": float(accuracy),
        "balanced_accuracy": float((recall + specificity) / 2),
        "severity_exact_match_rate_on_positive_days": safe_divide(severity_exact, positive_count),
        "false_positive_dates": [
            row["date"]
            for row in rows
            if not row["expected_is_anomaly"] and row["predicted_is_anomaly"]
        ],
        "false_negative_dates": [
            row["date"]
            for row in rows
            if row["expected_is_anomaly"] and not row["predicted_is_anomaly"]
        ],
        "rows": rows,
    }


def build_day_threshold_sweep(day_labels: pd.DataFrame, stats: list[Any]) -> dict[str, Any] | None:
    if day_labels.empty:
        return None

    rows: list[dict[str, Any]] = []
    thresholds = [round(value, 2) for value in np.arange(0.15, 0.81, 0.05)]
    for threshold in thresholds:
        metrics = build_day_level_metrics(day_labels, stats, score_threshold=float(threshold))
        if metrics is None:
            continue
        rows.append(
            {
                "score_threshold": float(threshold),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "specificity": metrics["specificity"],
                "accuracy": metrics["accuracy"],
                "balanced_accuracy": metrics["balanced_accuracy"],
                "true_positive_days": metrics["true_positive_days"],
                "false_positive_days": metrics["false_positive_days"],
                "false_negative_days": metrics["false_negative_days"],
                "true_negative_days": metrics["true_negative_days"],
            }
        )

    best_row = max(
        rows,
        key=lambda row: (row["f1"], row["balanced_accuracy"], row["precision"]),
        default=None,
    )
    target_rows = [
        row
        for row in rows
        if row["precision"] >= 0.8 and row["recall"] >= 0.75
    ]
    best_target_row = max(
        target_rows,
        key=lambda row: (row["balanced_accuracy"], row["recall"], row["f1"]),
        default=None,
    )
    return {
        "rows": rows,
        "best_by_f1": best_row,
        "target_constraints": {
            "min_precision": 0.8,
            "min_recall": 0.75,
        },
        "best_meeting_target_constraints": best_target_row,
        "note": "Threshold sweep uses day-level positive and negative labels.",
    }


def predict_calibrated_severity(
    score: float,
    warning_threshold: float,
    critical_threshold: float,
) -> str:
    if score >= critical_threshold:
        return "critical"
    if score >= warning_threshold:
        return "warning"
    return "normal"


def build_severity_calibration(day_labels: pd.DataFrame, stats: list[Any]) -> dict[str, Any] | None:
    if day_labels.empty:
        return None

    by_date = stats_by_date(stats)
    rows: list[dict[str, Any]] = []
    warning_thresholds = [round(value, 2) for value in np.arange(0.2, 0.66, 0.05)]
    critical_thresholds = [round(value, 2) for value in np.arange(0.45, 0.91, 0.05)]

    for warning_threshold in warning_thresholds:
        for critical_threshold in critical_thresholds:
            if critical_threshold <= warning_threshold:
                continue

            exact_all = 0
            exact_positive = 0
            positive_count = 0
            for _, label in day_labels.iterrows():
                stat = by_date.get(label["date"])
                score = float(getattr(stat, "combined_score", 0.0)) if stat is not None else 0.0
                expected = safe_text(label.get("expected_severity")).casefold() or "normal"
                predicted = predict_calibrated_severity(score, warning_threshold, critical_threshold)
                if severity_rank(predicted) == severity_rank(expected):
                    exact_all += 1
                    if bool(label["is_anomaly"]):
                        exact_positive += 1
                if bool(label["is_anomaly"]):
                    positive_count += 1

            rows.append(
                {
                    "warning_threshold": float(warning_threshold),
                    "critical_threshold": float(critical_threshold),
                    "severity_accuracy_all_days": safe_divide(exact_all, len(day_labels)),
                    "severity_accuracy_positive_days": safe_divide(exact_positive, positive_count),
                }
            )

    best_row = max(
        rows,
        key=lambda row: (
            row["severity_accuracy_positive_days"],
            row["severity_accuracy_all_days"],
        ),
        default=None,
    )
    return {
        "best_thresholds": best_row,
        "rows": rows,
        "note": (
            "Calibration is evaluation-only. It recommends alert severity thresholds "
            "without changing the anomaly engine defaults."
        ),
    }


def build_label_coverage_report(
    ground_truth: pd.DataFrame,
    detected_events: list[Any],
    eval_start: datetime,
    eval_end: datetime,
    day_labels: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Describe how much of the evaluation calendar is actually labeled."""
    evaluation_days = (eval_end.date() - eval_start.date()).days + 1
    ground_truth_dates = sorted({row["window_start"].date() for _, row in ground_truth.iterrows()})
    detected_dates = sorted({event.window_start.date() for event in detected_events})
    matched_dates = sorted(set(ground_truth_dates) & set(detected_dates))
    unlabeled_detected_dates = sorted(set(detected_dates) - set(ground_truth_dates))

    labeled_positive_day_count = len(ground_truth_dates)
    coverage_ratio = (
        labeled_positive_day_count / evaluation_days
        if evaluation_days > 0
        else 0.0
    )

    coverage = {
        "evaluation_days": int(evaluation_days),
        "labeled_positive_day_count": int(labeled_positive_day_count),
        "labeled_positive_day_coverage_ratio": float(coverage_ratio),
        "detected_day_count": int(len(detected_dates)),
        "matched_positive_day_count": int(len(matched_dates)),
        "detected_unlabeled_day_count": int(len(unlabeled_detected_dates)),
        "ground_truth_dates": [day.isoformat() for day in ground_truth_dates],
        "detected_dates": [day.isoformat() for day in detected_dates],
        "detected_unlabeled_dates": [day.isoformat() for day in unlabeled_detected_dates],
        "date_level_recall_scope": "curated_positive_dates_only",
        "date_level_recall_denominator": int(len(ground_truth)),
        "full_calendar_date_metrics_evaluable": False,
        "full_calendar_date_metrics_reason": (
            "The evaluation file labels only selected positive anomaly windows. "
            "It does not provide an independent label for every calendar day, "
            "so calendar-wide recall/specificity cannot be claimed."
        ),
    }

    if day_labels is not None and not day_labels.empty:
        labeled_days = set(day_labels["date"])
        positive_days = set(day_labels[day_labels["is_anomaly"]]["date"])
        negative_days = set(day_labels[~day_labels["is_anomaly"]]["date"])
        coverage.update(
            {
                "day_label_count": int(len(day_labels)),
                "labeled_positive_day_count": int(len(positive_days)),
                "labeled_negative_day_count": int(len(negative_days)),
                "full_calendar_date_metrics_evaluable": True,
                "full_calendar_date_metrics_reason": (
                    "The day-label file contains positive and negative labels for "
                    "the validation calendar."
                ),
                "labeled_day_coverage_ratio": safe_divide(len(labeled_days), evaluation_days),
                "labeled_negative_dates_sample": [
                    day.isoformat()
                    for day in sorted(negative_days)[:10]
                ],
            }
        )

    return coverage


def build_metric_quality_report(
    ground_truth: pd.DataFrame,
    label_coverage: dict[str, Any],
    day_labels: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Flag whether the metric set is strong enough for final project claims."""
    event_count = int(len(ground_truth))
    has_negative_labels = (
        day_labels is not None
        and not day_labels.empty
        and bool((~day_labels["is_anomaly"]).any())
    )
    sufficient_for_final_claims = event_count >= 30 and has_negative_labels

    return {
        "ground_truth_event_count": event_count,
        "minimum_recommended_ground_truth_events": 30,
        "has_negative_day_labels": bool(has_negative_labels),
        "ground_truth_sufficient_for_final_claims": bool(sufficient_for_final_claims),
        "recall_interpretation": (
            "Event recall is measured over the positive anomaly windows in the "
            "ground-truth file. If day labels are available, use day_level_metrics "
            "for a fuller positive/negative validation view."
        ),
        "date_level_recall_interpretation": (
            "date_level_recall is positive-date recall. Calendar-wide behavior is "
            "reported under day_level_metrics when negative day labels are present."
        ),
        "false_positive_interpretation": (
            "Unmatched detections are reported as false_positive_candidates because "
            "event-level matching is window-based. Day-level false positives are "
            "reported separately when negative labels are available."
        ),
        "recommended_next_step": (
            "Use the recommended score and severity thresholds from the validation "
            "set before presenting final anomaly performance claims."
        ),
    }


def build_score_threshold_sweep(
    ground_truth: pd.DataFrame,
    detected_events: list[Any],
) -> dict[str, Any]:
    """Show how evaluation metrics change with an operational score threshold."""
    thresholds = [0.0, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
    rows: list[dict[str, Any]] = []

    for threshold in thresholds:
        filtered_events = [
            event
            for event in detected_events
            if float(getattr(event, "score", 0.0)) >= threshold
        ]
        metrics = evaluate_matches(ground_truth, filtered_events)
        rows.append(
            {
                "score_threshold": float(threshold),
                "detected_event_count": int(metrics["detected_events"]),
                "matched_event_count": int(metrics["true_positives"]),
                "false_positive_count": int(metrics["false_positives"]),
                "precision": float(metrics["precision"]),
                "recall": float(metrics["recall"]),
                "f1": float(metrics["f1"]),
            }
        )

    best_row = max(
        rows,
        key=lambda row: (row["f1"], row["precision"], row["recall"]),
        default=None,
    )
    return {
        "rows": rows,
        "best_by_f1": best_row,
        "note": (
            "Primary metrics use all engine events. Threshold rows are an evaluation-only "
            "view for choosing an operational alert threshold."
        ),
    }


def infer_primary_signal(reasons: list[str]) -> str:
    reasons_text = " ".join(reasons).casefold()
    signals = []
    if "volume" in reasons_text:
        signals.append("volume")
    if "category" in reasons_text:
        signals.append("category")
    if "semantic" in reasons_text:
        signals.append("semantic")
    return "+".join(signals) if signals else "score_only"


def nearest_ground_truth_context(
    event: Any,
    ground_truth: pd.DataFrame,
) -> tuple[str, int | None, str]:
    if ground_truth.empty:
        return "", None, ""

    event_date = event.window_start.date()
    nearest_row = None
    nearest_delta = None
    for _, row in ground_truth.iterrows():
        gt_date = row["window_start"].date()
        delta = abs((event_date - gt_date).days)
        if nearest_delta is None or delta < nearest_delta:
            nearest_delta = delta
            nearest_row = row

    if nearest_row is None:
        return "", None, ""
    return (
        nearest_row["window_start"].date().isoformat(),
        int(nearest_delta),
        safe_text(nearest_row.get("anomaly_type")),
    )


def explain_false_positive_candidate(
    event: Any,
    nearest_delta_days: int | None,
    primary_signal: str,
) -> str:
    severity = safe_text(event.severity).casefold()
    if nearest_delta_days is not None and nearest_delta_days <= 1:
        return "adjacent_to_labeled_event_review_as_possible_spillover"
    if severity == "info":
        return "low_score_info_signal_review_not_confirmed_incident"
    if primary_signal == "category":
        return "category_distribution_shift_without_matching_label"
    if primary_signal == "semantic":
        return "semantic_drift_signal_without_matching_label"
    if "+" in primary_signal:
        return "multi_signal_candidate_not_covered_by_labels"
    return "score_threshold_candidate_without_matching_label"


def build_false_positive_candidates(
    detected_events: list[Any],
    matched_detection_indexes: set[int],
    ground_truth: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Return detected engine events that were not matched to a ground-truth window."""
    candidates: list[dict[str, Any]] = []
    for event_index, event in enumerate(detected_events):
        if event_index in matched_detection_indexes:
            continue
        primary_signal = infer_primary_signal(event.reasons)
        nearest_date, nearest_delta, nearest_type = nearest_ground_truth_context(
            event,
            ground_truth,
        )
        candidates.append(
            {
                "detected_event_index": int(event_index),
                "event_date": event.window_start.date().isoformat(),
                "window_start": event.window_start.isoformat(),
                "window_end": event.window_end.isoformat(),
                "severity": safe_text(event.severity),
                "score": float(event.score),
                "primary_signal": primary_signal,
                "nearest_ground_truth_date": nearest_date,
                "days_from_nearest_ground_truth": nearest_delta,
                "nearest_ground_truth_type": nearest_type,
                "interpretation": explain_false_positive_candidate(
                    event,
                    nearest_delta,
                    primary_signal,
                ),
                "reasons": " | ".join(event.reasons),
            }
        )
    return candidates


def build_adjacent_event_groups(detected_events: list[Any], max_gap_days: int = 1) -> list[dict[str, Any]]:
    """Group daily detections that are close enough to describe one operational incident."""
    if not detected_events:
        return []

    sorted_events = sorted(detected_events, key=lambda event: event.window_start)
    groups: list[list[Any]] = []
    current_group = [sorted_events[0]]

    for event in sorted_events[1:]:
        previous = current_group[-1]
        gap = event.window_start - previous.window_end
        if gap <= timedelta(days=max_gap_days):
            current_group.append(event)
        else:
            groups.append(current_group)
            current_group = [event]
    groups.append(current_group)

    grouped_rows: list[dict[str, Any]] = []
    severity_order = {"info": 1, "warning": 2, "critical": 3}
    for group_index, group in enumerate(groups, start=1):
        max_severity = max(
            (safe_text(event.severity) for event in group),
            key=lambda severity: severity_order.get(severity.casefold(), 0),
        )
        grouped_rows.append(
            {
                "group_id": f"G-{group_index:03d}",
                "window_start": min(event.window_start for event in group).isoformat(),
                "window_end": max(event.window_end for event in group).isoformat(),
                "event_count": int(len(group)),
                "max_score": float(max(event.score for event in group)),
                "max_severity": max_severity,
                "event_dates": [event.window_start.date().isoformat() for event in group],
            }
        )

    return grouped_rows


def evaluate_anomaly(
    ground_truth_path: Path = DEFAULT_GROUND_TRUTH,
    synthetic_path: Path = DEFAULT_SYNTHETIC,
    tickets_path: Path = DEFAULT_TICKETS,
    day_labels_path: Path | None = None,
    output_path: Path = DEFAULT_OUTPUT,
    false_positive_output_path: Path = DEFAULT_FALSE_POSITIVES,
    baseline_days: int = 90,
) -> dict[str, Any]:
    ground_truth = load_ground_truth(ground_truth_path)

    eval_start = ground_truth["window_start"].min().to_pydatetime()
    eval_end = ground_truth["window_end"].max().to_pydatetime()
    analysis_start = eval_start - timedelta(days=baseline_days)
    analysis_end = eval_end
    day_labels = load_day_labels(day_labels_path)
    if not day_labels.empty:
        day_labels = day_labels[
            (day_labels["date"] >= eval_start.date())
            & (day_labels["date"] <= eval_end.date())
        ].reset_index(drop=True)

    tickets = load_tickets_for_engine(tickets_path, start=analysis_start, end=analysis_end)
    embedding_ticket_count = sum(1 for ticket in tickets if ticket.embedding is not None)
    embedding_dim = next(
        (int(ticket.embedding.shape[0]) for ticket in tickets if ticket.embedding is not None),
        None,
    )
    stats, all_events = analyze_ticket_stream(
        tickets=tickets,
        window_size=timedelta(days=1),
        min_baseline_windows=3,
    )

    detected_events = [
        event
        for event in all_events
        if windows_overlap(event.window_start, event.window_end, eval_start, eval_end)
    ]

    matching_metrics = evaluate_matches(ground_truth, detected_events)
    threshold_sweep = build_score_threshold_sweep(ground_truth, detected_events)
    synthetic_summary = load_synthetic_summary(synthetic_path, ground_truth)
    matched_detection_indexes = set(matching_metrics["matched_detection_indexes"])
    false_positive_candidates = build_false_positive_candidates(
        detected_events,
        matched_detection_indexes,
        ground_truth,
    )
    adjacent_event_groups = build_adjacent_event_groups(detected_events)
    day_level_metrics = build_day_level_metrics(day_labels, stats)
    day_threshold_sweep = build_day_threshold_sweep(day_labels, stats)
    severity_calibration = build_severity_calibration(day_labels, stats)
    label_coverage = build_label_coverage_report(
        ground_truth,
        detected_events,
        eval_start,
        eval_end,
        day_labels=day_labels,
    )
    metric_quality = build_metric_quality_report(
        ground_truth,
        label_coverage,
        day_labels=day_labels,
    )
    matched_rows = [match for match in matching_metrics["matches"] if match.get("matched")]
    severity_exact_matches = sum(
        1
        for match in matched_rows
        if match.get("severity_matches_exactly")
    )
    type_compatible_matches = sum(
        1
        for match in matched_rows
        if match.get("type_compatible_from_reason_text")
    )

    matching_metrics.update(
        {
            "curated_event_recall": float(matching_metrics["recall"]),
            "curated_event_recall_denominator": int(len(ground_truth)),
            "recall_scope": "curated_positive_windows_only",
            "recall_is_final_model_claim": False,
            "ground_truth_event_count": int(len(ground_truth)),
            "detected_event_count": int(len(detected_events)),
            "matched_event_count": int(matching_metrics["true_positives"]),
            "date_level_recall": calculate_date_level_recall(ground_truth, detected_events),
            "date_level_recall_scope": "curated_positive_dates_only",
            "date_level_recall_is_final_model_claim": False,
            "severity_exact_match_count": int(severity_exact_matches),
            "severity_exact_match_rate": (
                float(severity_exact_matches / len(matched_rows))
                if matched_rows
                else 0.0
            ),
            "type_compatible_match_count": int(type_compatible_matches),
            "type_compatible_match_rate": (
                float(type_compatible_matches / len(matched_rows))
                if matched_rows
                else 0.0
            ),
            "severity_distribution": dict(Counter(event.severity for event in detected_events)),
            "false_positive_candidates": false_positive_candidates,
            "false_positive_candidate_count": int(len(false_positive_candidates)),
            "adjacent_event_groups": adjacent_event_groups,
            "adjacent_event_group_count": int(len(adjacent_event_groups)),
            "label_coverage": label_coverage,
            "day_level_metrics": day_level_metrics,
            "day_level_threshold_sweep": day_threshold_sweep,
            "severity_calibration": severity_calibration,
            "score_threshold_sweep": threshold_sweep,
        }
    )

    semantic_drift_available = any(stat.semantic_drift is not None for stat in stats)
    semantic_drift_reason = ""
    if not semantic_drift_available:
        semantic_drift_reason = (
            "processed/tickets.parquet does not contain embeddings"
            if embedding_ticket_count == 0
            else "processed/tickets.parquet contains embeddings, but evaluated windows did not have enough embedding baseline/current data"
        )

    compatibility_notes = [
        "Current engine emits window-level events with severity/score/reasons, not explicit anomaly_type labels.",
        "Matching is therefore based on time-window overlap; type compatibility is reported separately from reason text.",
        "Synthetic aggregate anomaly CSV is summarized and checked against ground-truth dates, but it is not a one-to-one engine output format.",
    ]
    if not semantic_drift_available:
        compatibility_notes.append(
            "Semantic drift is not directly evaluated in this run: " + semantic_drift_reason
        )

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "ground_truth": str(ground_truth_path),
            "synthetic_anomaly_dataset": str(synthetic_path),
            "processed_tickets": str(tickets_path),
            "day_labels": str(day_labels_path) if day_labels_path else None,
        },
        "engine_type_available": False,
        "semantic_drift_evaluable": bool(semantic_drift_available),
        "semantic_drift_reason": semantic_drift_reason,
        "analysis_window": {
            "baseline_days": baseline_days,
            "analysis_start": analysis_start.isoformat(),
            "analysis_end": analysis_end.isoformat(),
            "evaluation_start": eval_start.isoformat(),
            "evaluation_end": eval_end.isoformat(),
        },
        "engine_run": {
            "tickets_loaded": len(tickets),
            "tickets_with_embeddings": int(embedding_ticket_count),
            "embedding_dim": embedding_dim,
            "total_windows": len(stats),
            "all_detected_events": len(all_events),
            "detected_events_in_evaluation_window": len(detected_events),
            "semantic_drift_available": semantic_drift_available,
        },
        "metric_quality": metric_quality,
        "metrics": matching_metrics,
        "detected_events": [event_to_dict(event) for event in detected_events],
        "ground_truth_events": [
            {
                "window_start": row["window_start"].isoformat(),
                "window_end": row["window_end"].isoformat(),
                "anomaly_type": safe_text(row.get("anomaly_type")),
                "expected_severity": safe_text(row.get("expected_severity")),
                "description": safe_text(row.get("description")),
            }
            for _, row in ground_truth.iterrows()
        ],
        "window_stats_in_evaluation_window": [
            stat_to_dict(stat)
            for stat in stats
            if windows_overlap(stat.window_start, stat.window_end, eval_start, eval_end)
        ],
        "synthetic_anomaly_dataset_summary": synthetic_summary,
        "compatibility_notes": compatibility_notes,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)

    false_positive_output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        false_positive_candidates,
        columns=[
            "detected_event_index",
            "event_date",
            "window_start",
            "window_end",
            "severity",
            "score",
            "primary_signal",
            "nearest_ground_truth_date",
            "days_from_nearest_ground_truth",
            "nearest_ground_truth_type",
            "interpretation",
            "reasons",
        ],
    ).to_csv(false_positive_output_path, index=False, encoding="utf-8")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate anomaly detection against ground truth windows.")
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--synthetic", type=Path, default=DEFAULT_SYNTHETIC)
    parser.add_argument("--tickets", type=Path, default=DEFAULT_TICKETS)
    parser.add_argument("--day-labels", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--false-positives-output", type=Path, default=DEFAULT_FALSE_POSITIVES)
    parser.add_argument("--baseline-days", type=int, default=90)
    args = parser.parse_args()

    result = evaluate_anomaly(
        ground_truth_path=args.ground_truth,
        synthetic_path=args.synthetic,
        tickets_path=args.tickets,
        day_labels_path=args.day_labels,
        output_path=args.output,
        false_positive_output_path=args.false_positives_output,
        baseline_days=args.baseline_days,
    )

    metrics = result["metrics"]
    print("Anomaly evaluation complete.")
    print(f"Tickets loaded: {result['engine_run']['tickets_loaded']}")
    print(f"Tickets with embeddings: {result['engine_run']['tickets_with_embeddings']}")
    print(f"Ground-truth events: {metrics['ground_truth_event_count']}")
    print(f"Detected events: {metrics['detected_event_count']}")
    print(f"Matched events: {metrics['matched_event_count']}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall (curated-positive windows only): {metrics['recall']:.4f}")
    print(f"F1: {metrics['f1']:.4f}")
    print(f"Date-level recall (curated-positive dates only): {metrics['date_level_recall']:.4f}")
    print(f"Severity exact match rate: {metrics['severity_exact_match_rate']:.4f}")
    print(f"False-positive candidates: {metrics['false_positive_candidate_count']}")
    if metrics.get("day_level_metrics"):
        day_metrics = metrics["day_level_metrics"]
        print("Day-level validation metrics:")
        print(f"  Precision: {day_metrics['precision']:.4f}")
        print(f"  Recall: {day_metrics['recall']:.4f}")
        print(f"  F1: {day_metrics['f1']:.4f}")
        print(f"  Specificity: {day_metrics['specificity']:.4f}")
        print(
            "  Confusion: "
            f"TP={day_metrics['true_positive_days']} "
            f"FP={day_metrics['false_positive_days']} "
            f"FN={day_metrics['false_negative_days']} "
            f"TN={day_metrics['true_negative_days']}"
        )
    if metrics.get("day_level_threshold_sweep") and metrics["day_level_threshold_sweep"].get("best_by_f1"):
        best_threshold = metrics["day_level_threshold_sweep"]["best_by_f1"]
        print(
            "Recommended score threshold: "
            f"{best_threshold['score_threshold']:.2f} "
            f"(F1={best_threshold['f1']:.4f}, precision={best_threshold['precision']:.4f}, "
            f"recall={best_threshold['recall']:.4f})"
        )
        target_threshold = metrics["day_level_threshold_sweep"].get("best_meeting_target_constraints")
        if target_threshold:
            print(
                "Target-constrained score threshold: "
                f"{target_threshold['score_threshold']:.2f} "
                f"(precision={target_threshold['precision']:.4f}, "
                f"recall={target_threshold['recall']:.4f}, "
                f"F1={target_threshold['f1']:.4f})"
            )
    if metrics.get("severity_calibration") and metrics["severity_calibration"].get("best_thresholds"):
        best_severity = metrics["severity_calibration"]["best_thresholds"]
        print(
            "Recommended severity thresholds: "
            f"warning={best_severity['warning_threshold']:.2f}, "
            f"critical={best_severity['critical_threshold']:.2f}"
        )
    print(f"Output: {args.output}")
    print(f"False-positive CSV: {args.false_positives_output}")

    metric_quality = result["metric_quality"]
    if not metric_quality["ground_truth_sufficient_for_final_claims"]:
        print("Warning: anomaly recall is not a final field-quality claim.")
        print(metric_quality["recall_interpretation"])

    if not result["engine_run"]["semantic_drift_available"]:
        print(f"Note: semantic_drift was not available: {result['semantic_drift_reason']}")


if __name__ == "__main__":
    main()
