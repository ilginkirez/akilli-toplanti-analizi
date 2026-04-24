import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.session_report_generator import SessionReportGenerator


def test_calculate_vad_metrics_perfect_match():
    reference_segments = [
        {"start": 0.0, "end": 1.5},
    ]
    hypothesis_segments = [
        {"start": 0.0, "end": 1.5},
    ]

    metrics = SessionReportGenerator.calculate_vad_metrics(
        hypothesis_segments=hypothesis_segments,
        reference_segments=reference_segments,
        total_duration=2.0,
        resolution_ms=500,
    )

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["accuracy"] == 1.0
    assert metrics["false_alarm_rate"] == 0.0
    assert metrics["miss_rate"] == 0.0


def test_calculate_vad_metrics_partial_overlap():
    reference_segments = [
        {"start": 0.0, "end": 1.0},
    ]
    hypothesis_segments = [
        {"start": 0.5, "end": 1.5},
    ]

    metrics = SessionReportGenerator.calculate_vad_metrics(
        hypothesis_segments=hypothesis_segments,
        reference_segments=reference_segments,
        total_duration=2.0,
        resolution_ms=500,
    )

    assert metrics["tp"] == 1.0
    assert metrics["fp"] == 1.0
    assert metrics["fn"] == 1.0
    assert metrics["tn"] == 2.0
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["accuracy"] == 0.6
    assert metrics["false_alarm_rate"] == 0.3333
    assert metrics["miss_rate"] == 0.5
