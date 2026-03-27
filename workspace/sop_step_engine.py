"""workspace/sop_step_engine.py — Breaks the chosen path into concrete actionable steps."""
from __future__ import annotations
from typing import Any

STEPS: dict = {
    "ROLL_SAME_SIDE": [
        "Review current short and confirm same-side rollability.",
        "Verify target roll captures acceptable credit.",
        "Confirm timing/surface remain above minimum execution quality.",
        "Draft or execute same-side roll ticket.",
        "Log execution decision and next review trigger.",
    ],
    "COLLAPSE_TO_SPREAD": [
        "Review campaign basis and confirm simplification is justified.",
        "Select spread structure and width.",
        "Check reduced complexity path against capital and portfolio posture.",
        "Draft collapse-to-spread ticket.",
        "Log simplification and future monitoring plan.",
    ],
    "BANK_AND_REDUCE": [
        "Confirm basis recovery is sufficient to reduce exposure.",
        "Select size reduction / close plan.",
        "Check whether any residual structure should remain open.",
        "Execute or draft reduction ticket.",
        "Log realized progress and archive follow-up rules.",
    ],
    "DEFER_AND_WAIT": [
        "Do not execute path immediately.",
        "Record blocking timing/surface conditions.",
        "Set next re-evaluation trigger.",
        "Escalate to review queue if needed.",
    ],
    "CONTINUE_HARVEST": [
        "Continue managing through current harvest path.",
        "Verify next short harvest remains aligned with policy and mandate.",
        "Prepare next campaign review point.",
    ],
}

def build_workspace_sop_steps(path_code: str, row: dict[str,Any]) -> list[dict[str,Any]]:
    raw=STEPS.get(path_code,STEPS["CONTINUE_HARVEST"])
    return [{"step":i+1,"label":s} for i,s in enumerate(raw)]
