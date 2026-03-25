"""
execution/transition_ticket_builder.py
Generates manual execution tickets from approved transition results.
No orders are placed — tickets are operator-readable close/open sequences.

build_transition_ticket(current_position, approved_transition) → ticket dict
"""
from __future__ import annotations

from typing import Any


def _expiry_key(leg: dict) -> str:
    return str(leg.get("expiry") or leg.get("expiration",""))


def _leg_label(leg: dict) -> str:
    return (f'{str(leg.get("option_type","")).upper()} '
            f'{_expiry_key(leg)} '
            f'${float(leg.get("strike",0)):.1f}')


def _build_diagonal_ticket(position: dict, transition: dict) -> dict:
    """Roll short leg only — keep long anchor. One close + one open."""
    qty          = int(position.get("contracts", 1))
    cur_short    = position.get("short_leg", {})
    new_struct   = transition.get("new_structure", {})
    new_short    = new_struct.get("short_leg", {})
    long_leg     = new_struct.get("long_leg", {})

    return {
        "ticket_type":    "TRANSITION_TICKET",
        "action":         transition.get("recommended_action"),
        "transition_class": "DIAGONAL_ROLL",
        "close_orders": [{
            "action":      "BUY_TO_CLOSE",
            "leg_role":    "current_short",
            "description": _leg_label(cur_short),
            "option_type": cur_short.get("option_type"),
            "expiry":      _expiry_key(cur_short),
            "strike":      float(cur_short.get("strike", 0)),
            "quantity":    qty,
            "fill_note":   "Buy near ask (conservative)",
        }],
        "open_orders": [{
            "action":      "SELL_TO_OPEN",
            "leg_role":    "new_short",
            "description": _leg_label(new_short),
            "option_type": new_short.get("option_type"),
            "expiry":      _expiry_key(new_short),
            "strike":      float(new_short.get("strike", 0)),
            "quantity":    qty,
            "fill_note":   "Sell near bid (conservative)",
        }],
        "long_leg_unchanged": _leg_label(long_leg) if long_leg else "unchanged",
        "estimated_net_credit":  round(float(transition.get("transition_net_credit", 0)), 4),
        "expected_post_structure": {
            "type":      new_struct.get("type",""),
            "long_leg":  _leg_label(long_leg) if long_leg else "—",
            "short_leg": _leg_label(new_short),
        },
        "future_roll_score": transition.get("future_roll_score", 0),
        "notes": transition.get("why", []),
    }


def _build_credit_spread_ticket(position: dict, transition: dict) -> dict:
    """Close both legs, open new defined-risk spread. Two closes + two opens."""
    qty        = int(position.get("contracts", 1))
    cur_long   = position.get("long_leg", {})
    cur_short  = position.get("short_leg", {})
    new_struct = transition.get("new_structure", {})
    new_long   = new_struct.get("long_leg", {})
    new_short  = new_struct.get("short_leg", {})

    return {
        "ticket_type":    "TRANSITION_TICKET",
        "action":         transition.get("recommended_action"),
        "transition_class": "CREDIT_SPREAD_CONVERSION",
        "close_orders": [
            {"action": "SELL_TO_CLOSE", "leg_role": "current_long",
             "description": _leg_label(cur_long),
             "option_type": cur_long.get("option_type"), "expiry": _expiry_key(cur_long),
             "strike": float(cur_long.get("strike",0)), "quantity": qty,
             "fill_note": "Sell near bid"},
            {"action": "BUY_TO_CLOSE",  "leg_role": "current_short",
             "description": _leg_label(cur_short),
             "option_type": cur_short.get("option_type"), "expiry": _expiry_key(cur_short),
             "strike": float(cur_short.get("strike",0)), "quantity": qty,
             "fill_note": "Buy near ask"},
        ],
        "open_orders": [
            {"action": "BUY_TO_OPEN",  "leg_role": "new_long",
             "description": _leg_label(new_long),
             "option_type": new_long.get("option_type"), "expiry": _expiry_key(new_long),
             "strike": float(new_long.get("strike",0)), "quantity": qty,
             "fill_note": "Buy near ask"},
            {"action": "SELL_TO_OPEN", "leg_role": "new_short",
             "description": _leg_label(new_short),
             "option_type": new_short.get("option_type"), "expiry": _expiry_key(new_short),
             "strike": float(new_short.get("strike",0)), "quantity": qty,
             "fill_note": "Sell near bid"},
        ],
        "estimated_net_credit": round(float(transition.get("transition_net_credit", 0)), 4),
        "expected_post_structure": {
            "type":      new_struct.get("type",""),
            "long_leg":  _leg_label(new_long),
            "short_leg": _leg_label(new_short),
        },
        "future_roll_score": transition.get("future_roll_score", 0),
        "notes": transition.get("why", []),
    }


def build_transition_ticket(
    current_position:   dict[str, Any],
    approved_transition: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a manually-executable transition ticket.
    No orders are placed. Output is for operator review.
    """
    action = str(approved_transition.get("recommended_action","HOLD_CURRENT_HARVEST"))

    if "DIAGONAL" in action:
        return _build_diagonal_ticket(current_position, approved_transition)

    if "SPREAD" in action:
        return _build_credit_spread_ticket(current_position, approved_transition)

    return {
        "ticket_type":          "TRANSITION_TICKET",
        "action":               action,
        "transition_class":     "HOLD",
        "close_orders":         [],
        "open_orders":          [],
        "estimated_net_credit": 0.0,
        "notes":                approved_transition.get("why", ["No transition recommended"]),
    }
