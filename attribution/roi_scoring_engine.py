"""attribution/roi_scoring_engine.py — Combines value and friction into ROI."""
from __future__ import annotations
from typing import Any

def compute_component_roi(value_signals: dict[str,Any], friction_signals: dict[str,Any]) -> dict[str,Any]:
    vs=float(value_signals.get("value_score",0)); fs=float(friction_signals.get("friction_score",0))
    roi=round(vs-fs,2)
    label="HIGH_VALUE" if roi>=40 else "POSITIVE" if roi>=15 else "MARGINAL" if roi>=0 else "NEGATIVE"
    return {"value_score":vs,"friction_score":fs,"roi_score":roi,"roi_label":label}
