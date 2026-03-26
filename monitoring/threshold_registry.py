"""monitoring/threshold_registry.py — Warning and critical thresholds per environment profile."""
from __future__ import annotations

# Base thresholds (LIVE-equivalent)
_BASE: dict = {
    "avg_fill_score_recent":       {"warning_below":65.0,"critical_below":55.0},
    "avg_slippage_recent":         {"warning_below":-0.20,"critical_below":-0.40},
    "blocked_candidate_rate":      {"warning_above":0.40,"critical_above":0.60},
    "surface_block_rate":          {"warning_above":0.25,"critical_above":0.40},
    "timing_block_rate":           {"warning_above":0.25,"critical_above":0.40},
    "queue_depth":                 {"warning_below":2,"critical_below":1},
    "queue_compression_rate":      {"warning_above":0.70,"critical_above":0.85},
    "top_symbol_concentration":    {"warning_above":0.30,"critical_above":0.40},
    "capital_block_rate":          {"warning_above":0.20,"critical_above":0.35},
    "delay_rate":                  {"warning_above":0.35,"critical_above":0.50},
}

# Per-environment profiles (DEV loosened, SIM realistic, LIVE strict)
THRESHOLD_PROFILES: dict = {
    "DEV":  {k: {kk: (vv*1.5 if "above" in kk else vv*0.7) for kk,vv in v.items()} for k,v in _BASE.items()},
    "SIM":  _BASE,
    "LIVE": _BASE,
}
# Flat registry for backward compat
THRESHOLD_REGISTRY: dict = _BASE

def get_thresholds(environment: str="LIVE") -> dict:
    return THRESHOLD_PROFILES.get(str(environment).upper(), _BASE)
