"""
execution/execution_engine.py
Execution assist — walk-limit logic and roll ticket generation.

Not full auto-trading. Assists with:
  - Walk-limit credit path simulation
  - Roll ticket drafting for operator review
  - Tradier-ready structure (wires in later)
"""
from __future__ import annotations

import time
from typing import Any

from config.vh_config import (
    WALK_LIMIT_STEP, WALK_LIMIT_INTERVAL, WALK_LIMIT_TIMEOUT,
    MIN_ROLL_NET_CREDIT,
)


def simulate_walk_limit(
    max_credit:   float,
    floor_credit: float = None,
    steps:        int   = None,
) -> dict[str, Any]:
    """
    Simulate a walk-limit credit path.

    Starts at max_credit, walks down by WALK_LIMIT_STEP until floor_credit.
    Returns the simulated fill path and recommended entry point.
    """
    floor   = floor_credit if floor_credit is not None else MIN_ROLL_NET_CREDIT
    n_steps = steps if steps is not None else int((max_credit - floor) / WALK_LIMIT_STEP) + 1
    path    = [round(max_credit - i * WALK_LIMIT_STEP, 4) for i in range(n_steps)]
    path    = [p for p in path if p >= floor]

    return {
        "start_credit":       max_credit,
        "floor_credit":       floor,
        "step":               WALK_LIMIT_STEP,
        "interval_seconds":   WALK_LIMIT_INTERVAL,
        "estimated_duration": WALK_LIMIT_INTERVAL * len(path),
        "credit_path":        path,
        "recommended_entry":  path[0] if path else max_credit,
        "note": (
            f"Start at ${max_credit:.2f}, walk down ${WALK_LIMIT_STEP:.2f} every "
            f"{WALK_LIMIT_INTERVAL}s to floor ${floor:.2f}."
        ),
    }


def draft_roll_ticket(
    position:        dict[str, Any],
    harvest_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a draft roll ticket for operator review.

    Returns a structured dict ready for display or broker API.
    Does NOT submit anything.
    """
    roll_credit = harvest_summary.get("proposed_roll_credit", 0.0)
    target_k    = harvest_summary.get("target_strike")
    target_exp  = harvest_summary.get("target_expiration", "")
    action      = harvest_summary.get("roll_action", "WAIT")

    if action == "WAIT" or roll_credit < MIN_ROLL_NET_CREDIT:
        return {
            "status":   "NOT_READY",
            "reason":   f"Roll credit ${roll_credit:.2f} below minimum ${MIN_ROLL_NET_CREDIT:.2f}.",
            "ticket":   None,
        }

    walk_sim = simulate_walk_limit(max_credit=roll_credit)

    ticket = {
        "symbol":          position.get("symbol", ""),
        "action":          "ROLL",
        "close_leg":       {
            "strike":      position.get("short_strike"),
            "expiration":  position.get("short_expiration", ""),
            "option_type": position.get("option_side", position.get("option_type", "")),
            "side":        "BUY_TO_CLOSE",
        },
        "open_leg":        {
            "strike":      target_k,
            "expiration":  target_exp,
            "option_type": position.get("option_side", position.get("option_type", "")),
            "side":        "SELL_TO_OPEN",
        },
        "net_credit_target": roll_credit,
        "walk_limit":      walk_sim,
        "harvest_badge":   harvest_summary.get("harvest_badge", "—"),
        "contracts":       position.get("contracts", 1),
        "note":            harvest_summary.get("roll_notes", ""),
        "status":          "DRAFT",
        "broker_ready":    False,   # True once Tradier credentials wired
    }

    return {"status": "READY", "ticket": ticket, "walk_limit": walk_sim}
