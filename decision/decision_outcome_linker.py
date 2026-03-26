"""decision/decision_outcome_linker.py — Links human decisions to later realized outcomes."""
from __future__ import annotations
from typing import Any

def link_decision_to_outcome(decision_packet: dict[str,Any], outcome_snapshot: dict[str,Any]) -> dict[str,Any]:
    out=dict(decision_packet); out["decision_effect"]=outcome_snapshot; return out
