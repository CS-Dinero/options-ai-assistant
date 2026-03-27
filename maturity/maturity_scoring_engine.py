"""maturity/maturity_scoring_engine.py — Converts signals into a 0-100 maturity score."""
from __future__ import annotations
from typing import Any

def compute_maturity_score(signals: dict[str,Any]) -> float:
    score=(0.30*_b(signals.get("avg_roi",0),100)+0.25*signals.get("stability_score",0)+
           0.20*max(0,100-signals.get("avg_friction",0))+
           0.15*max(0,100-signals.get("override_rate",0)*100)+
           0.10*max(0,100-signals.get("failure_rate",0)*100))
    return round(score,2)

def _b(v,cap): return max(0.0,min(float(cap),float(v)))
