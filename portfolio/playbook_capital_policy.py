"""portfolio/playbook_capital_policy.py — Maps playbook status to capital rules."""
from __future__ import annotations

PLAYBOOK_CAPITAL_POLICY: dict = {
    "PROMOTED": {
        "size_multiplier":        1.15,
        "max_symbol_concurrency": 3,
        "max_playbook_concurrency": 4,
        "scale_aggression":       "ENHANCED",
        "queue_capital_bias":     8.0,
    },
    "WATCHLIST": {
        "size_multiplier":        1.00,
        "max_symbol_concurrency": 2,
        "max_playbook_concurrency": 3,
        "scale_aggression":       "NORMAL",
        "queue_capital_bias":     0.0,
    },
    "LIMITED_USE": {
        "size_multiplier":        0.65,
        "max_symbol_concurrency": 1,
        "max_playbook_concurrency": 2,
        "scale_aggression":       "REDUCED",
        "queue_capital_bias":     -8.0,
    },
    "DEMOTED": {
        "size_multiplier":        0.35,
        "max_symbol_concurrency": 1,
        "max_playbook_concurrency": 1,
        "scale_aggression":       "MINIMAL",
        "queue_capital_bias":     -15.0,
    },
}

def get_capital_policy(status: str) -> dict:
    return PLAYBOOK_CAPITAL_POLICY.get(status, PLAYBOOK_CAPITAL_POLICY["WATCHLIST"])
