"""execution/execution_scheduler.py — Converts timing + stagger policy into actionable schedule."""
from __future__ import annotations
from typing import Any

NEXT_WINDOW = {"OPENING_VOL":"MORNING_TREND","MORNING_TREND":"MIDDAY",
               "MIDDAY":"POWER_HOUR","POWER_HOUR":"NEXT_SESSION_OPEN",
               "LATE_CLOSE":"NEXT_SESSION_OPEN","OUTSIDE_RTH":"NEXT_SESSION_OPEN"}

def build_execution_schedule(candidate_row: dict[str,Any]) -> dict[str,Any]:
    window = str(candidate_row.get("transition_time_window") or candidate_row.get("time_window","OUTSIDE_RTH"))
    policy = str(candidate_row.get("transition_execution_policy") or candidate_row.get("execution_policy","DELAY"))
    next_w = NEXT_WINDOW.get(window,"NEXT_SESSION_OPEN")
    if policy=="FULL_NOW":
        return {"execution_schedule":"EXECUTE_NOW","next_window":None,"notes":["execute in current window"]}
    if policy=="STAGGER":
        return {"execution_schedule":"PARTIAL_NOW_PARTIAL_LATER","next_window":next_w,
                "notes":[f"execute partial now, complete in {next_w}"]}
    return {"execution_schedule":"DEFER","next_window":next_w,"notes":[f"defer until {next_w}"]}
