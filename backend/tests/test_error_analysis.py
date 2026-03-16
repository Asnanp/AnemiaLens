from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "scripts"))

from analyze_efficientnet_errors import _mistakes, _source_breakdown


@dataclass(frozen=True)
class _Record:
    subject_id: str
    source: str
    image_path: str


def test_source_breakdown_counts_errors_by_source() -> None:
    records = [
        _Record("s1", "roi_original", "a.jpg"),
        _Record("s2", "roi_original", "b.jpg"),
        _Record("s3", "palpebral", "c.png"),
    ]

    result = _source_breakdown(
        records,
        labels=[0, 1, 0],
        predictions=[1, 1, 0],
        probabilities=[0.8, 0.9, 0.1],
        hb_predictions=[10.5, 8.8, 12.4],
        hb_targets=[12.6, 9.1, 12.1],
    )

    assert result["roi_original"]["count"] == 2
    assert result["roi_original"]["false_positives"] == 1
    assert result["roi_original"]["false_negatives"] == 0
    assert result["palpebral"]["errors"] == 0


def test_mistakes_splits_false_positives_and_false_negatives() -> None:
    records = [
        _Record("s1", "roi_original", "a.jpg"),
        _Record("s2", "palpebral", "b.png"),
    ]

    false_positives, false_negatives = _mistakes(
        records,
        labels=[0, 1],
        predictions=[1, 0],
        probabilities=[0.91, 0.12],
        hb_predictions=[10.2, 12.8],
        hb_targets=[13.1, 8.9],
    )

    assert len(false_positives) == 1
    assert false_positives[0]["subject_id"] == "s1"
    assert len(false_negatives) == 1
    assert false_negatives[0]["subject_id"] == "s2"
