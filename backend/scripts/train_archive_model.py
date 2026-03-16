"""
Train the archive conjunctiva screening model.

Usage::

    python scripts/train_archive_model.py [--dataset PATH] [--output-dir PATH] [--quiet]

The script trains the model, writes the artefact and a human-readable
training report, then exits with code 0 on success or 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import DEFAULT_ARCHIVE_MODEL_PATH, DEFAULT_TRAINING_REPORT_PATH  # noqa: E402
from app.ml.archive_model import save_archive_model, train_archive_model  # noqa: E402

DEFAULT_DATASET = ROOT / "archive" / "dataset anemia"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Train the AnemiaLens archive conjunctiva screening model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Root directory of the labelled anemia dataset.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_ARCHIVE_MODEL_PATH.parent,
        help="Directory where the model artefact and report are written.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output (report still written to disk).",
    )
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if not args.dataset.exists():
        print(
            f"ERROR: Dataset directory not found: {args.dataset}\n"
            "       Download the anemia dataset and place it there, or pass --dataset PATH.",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(f"Dataset : {args.dataset}")
        print(f"Output  : {args.output_dir}")
        print()

    t0 = time.perf_counter()

    try:
        artifact, report = train_archive_model(args.dataset)
    except Exception as exc:
        print(f"ERROR: Training failed — {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - t0

    # --- Write artefacts ---------------------------------------------------
    args.output_dir.mkdir(parents=True, exist_ok=True)

    model_path = args.output_dir / DEFAULT_ARCHIVE_MODEL_PATH.name
    report_path = args.output_dir / DEFAULT_TRAINING_REPORT_PATH.name

    save_archive_model(artifact, model_path)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Summary -----------------------------------------------------------
    if not args.quiet:
        metrics = report.get("metrics", {})
        print(json.dumps(report, indent=2))
        print()
        print("=" * 56)
        print(f"  Model      : {report.get('primary_model', '?')}")
        print(f"  Subjects   : {report.get('subject_count', '?')}")
        print(f"  Records    : {report.get('record_count', '?')}")
        print(f"  Accuracy   : {metrics.get('accuracy', 0):.3f}")
        print(f"  F1         : {metrics.get('f1', 0):.3f}")
        print(f"  Val size   : {metrics.get('validation_size', '?')}")
        print(f"  Elapsed    : {elapsed:.1f}s")
        print("=" * 56)
        print(f"  Saved model  → {model_path}")
        print(f"  Saved report → {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
