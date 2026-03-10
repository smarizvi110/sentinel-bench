"""Sentinel-Bench source package."""

from .config import MODELS, TARGET_BASELINE_SIZE, TRIALS_PER_PROPOSAL
from .engine import Judiciary
from .ingest import build_scientific_dataset, fetch_agora_proposals, fetch_governance_context

__all__ = [
    "MODELS",
    "TARGET_BASELINE_SIZE",
    "TRIALS_PER_PROPOSAL",
    "Judiciary",
    "build_scientific_dataset",
    "fetch_agora_proposals",
    "fetch_governance_context",
]
