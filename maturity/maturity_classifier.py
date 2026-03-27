"""maturity/maturity_classifier.py — Assigns maturity level from score."""
from __future__ import annotations
from maturity.maturity_registry import MATURITY_REGISTRY

def classify_maturity(score: float) -> str:
    for level,meta in sorted(MATURITY_REGISTRY.items(),key=lambda x: x[1]["score_min"],reverse=True):
        if score>=meta["score_min"]: return level
    return "PROTOTYPE"

def maturity_is_sufficient(level: str, minimum_required: str="STABLE") -> bool:
    order=["PROTOTYPE","USABLE","STABLE","GOVERNED","SCALABLE"]
    return order.index(level)>=order.index(minimum_required) if level in order and minimum_required in order else False
