"""risk/confidence_weight_engine.py — Converts forecast/path confidence into capital weight."""
from __future__ import annotations

def confidence_to_weight(confidence_score: float) -> float:
    s=float(confidence_score)
    if s>=85: return 1.10
    if s>=75: return 1.00
    if s>=65: return 0.85
    if s>=55: return 0.65
    return 0.40
