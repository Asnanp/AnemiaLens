"""
Train all models in the AnemiaLens ensemble pipeline.

Currently delegates to train_archive_model.  As the ensemble grows
(deep-stack, legacy CNN, etc.) this script will orchestrate each
training job in dependency order and produce a combined manifest.

Usage::

    python scripts/train_ensemble.py [--dataset PATH] [--output-dir PATH] [--quiet]
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the scripts directory is on the path so we can import sibling scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_archive_model import main as train_archive


def main(argv: list[str] | None = None) -> int:
    """
    Orchestrate all training jobs.

    Returns the exit code of the last failing job, or 0 if all succeeded.
    """
    exit_code = 0

    print("=== Step 1/1: archive screening model ===")
    rc = train_archive(argv)
    if rc != 0:
        print(f"  FAILED (exit {rc})", file=sys.stderr)
        exit_code = rc
    else:
        print("  Done.")

    # Future steps (uncomment when models are ready):
    # print("=== Step 2/N: deep-stack model ===")
    # rc = train_deep_stack(argv)
    # ...

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
