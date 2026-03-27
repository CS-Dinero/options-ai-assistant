"""workspace/ticket_readiness_engine.py — Determines workspace ticket readiness."""
from __future__ import annotations
from typing import Any

def evaluate_ticket_readiness(workspace: dict[str,Any], row: dict[str,Any], environment: str) -> dict[str,Any]:
    blockers=workspace.get("blockers",[]); hp=str(row.get("bot_priority","P6")) in ("P0","P1","P2")
    if environment!="LIVE":
        return {"status":"BLOCKED","summary":f"Live execution not enabled in {environment}."}
    if not blockers:
        return {"status":"READY","summary":"Workspace is ready for execution ticket drafting."}
    types={b["type"] for b in blockers}
    if types<={"TIMING","SURFACE"} and hp:
        return {"status":"READY_WITH_CAUTION","summary":"Urgency overrides some execution weakness; caution required."}
    if "PORTFOLIO" in types or "CAPITAL" in types:
        return {"status":"REVIEW_REQUIRED","summary":"Portfolio or capital blockers require resolution first."}
    return {"status":"BLOCKED","summary":"Workspace is not ticket-ready under current conditions."}
