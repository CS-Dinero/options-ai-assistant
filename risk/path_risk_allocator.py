"""risk/path_risk_allocator.py — Different paths receive different capital trust."""
from __future__ import annotations

PATH_RISK_WEIGHTS: dict = {
    "CONTINUE_HARVEST":  1.00,
    "ROLL_SAME_SIDE":    1.00,
    "COLLAPSE_TO_SPREAD":0.85,
    "BANK_AND_REDUCE":   0.70,
    "DEFER_AND_WAIT":    0.20,
}

def path_to_risk_weight(path_code: str) -> float:
    return float(PATH_RISK_WEIGHTS.get(str(path_code), 0.75))
