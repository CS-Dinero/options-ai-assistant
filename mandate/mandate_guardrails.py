"""mandate/mandate_guardrails.py — Prevents mandates from overriding hard gates."""
from __future__ import annotations
from typing import Any

def enforce_mandate_guardrails(row: dict[str,Any], active_mandate: str) -> dict[str,Any]:
    out=dict(row)
    if row.get("transition_portfolio_fit_ok") is False:
        out["mandate_guardrail_note"]="Portfolio-fit hard gate remains binding."; return out
    if row.get("transition_execution_surface_ok") is False:
        out["mandate_guardrail_note"]="Execution-surface hard gate remains binding."; return out
    if row.get("transition_timing_ok") is False and str(row.get("bot_priority","P6")) not in ("P0","P1","P2"):
        out["mandate_guardrail_note"]="Timing hard gate remains binding for non-urgent actions."; return out
    out["mandate_guardrail_note"]="Mandate applied within normal hard-gate limits."
    return out
