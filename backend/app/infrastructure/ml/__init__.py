"""
Infrastructure layer for ML concerns: model loading, inference, calibration.

This layer isolates framework-level ML concerns (file I/O, model artifacts,
tensor operations) from domain services so that business logic remains
framework-agnostic.

Sub-packages:
- models/      : Model artifact loading and management
- inference/   : Inference pipeline orchestration
- calibration/ : Risk calibration, hemoglobin calibration, refinement
"""

from __future__ import annotations
