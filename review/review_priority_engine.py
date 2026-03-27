"""review/review_priority_engine.py — Assigns P0–P3 urgency to review packets."""
from __future__ import annotations
from typing import Any

def assign_review_priority(packet: dict[str,Any]) -> dict[str,Any]:
    rt=packet.get("review_type"); ev=packet.get("evidence",{}) or {}
    p="P3"
    if rt=="ROLLBACK_WATCH_REVIEW":          p="P0" if ev.get("severity")=="CRITICAL" else "P1"
    elif rt=="POLICY_CHANGE_APPROVAL_REVIEW": p="P1"
    elif rt=="SLIPPAGE_HOTSPOT_REVIEW":       p="P1"
    elif rt in ("QUEUE_STARVATION_REVIEW","CAPITAL_CHOKE_REVIEW","PROMOTED_PLAYBOOK_REVIEW"): p="P2"
    out=dict(packet); out["priority"]=p; return out
