"""workspace/blocker_engine.py — Identifies what is preventing action."""
from __future__ import annotations
from typing import Any

def build_workspace_blockers(row: dict[str,Any], environment: str) -> list[dict[str,Any]]:
    blockers=[]
    if row.get("transition_timing_ok") is False:
        blockers.append({"type":"TIMING","summary":"Timing conditions are below acceptable threshold."})
    if row.get("transition_execution_surface_ok") is False:
        blockers.append({"type":"SURFACE","summary":"Execution surface is below acceptable threshold."})
    if row.get("transition_portfolio_fit_ok") is False:
        blockers.append({"type":"PORTFOLIO","summary":"Portfolio-fit gate is blocking this path."})
    if row.get("capital_commitment_ok") is False:
        blockers.append({"type":"CAPITAL","summary":"Capital commitment or concurrency is blocking expansion."})
    if environment!="LIVE":
        blockers.append({"type":"ENVIRONMENT","summary":f"Execution is not enabled in {environment}."})
    return blockers
