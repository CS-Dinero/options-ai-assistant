"""risk/maturity_weight_engine.py — Converts capability maturity into trust-adjusted sizing."""
from __future__ import annotations

MATURITY_WEIGHTS: dict = {
    "PROTOTYPE": 0.25, "USABLE": 0.50, "STABLE": 0.75, "GOVERNED": 0.95, "SCALABLE": 1.05,
}

def maturity_to_weight(level: str) -> float:
    return float(MATURITY_WEIGHTS.get(str(level), 0.50))
