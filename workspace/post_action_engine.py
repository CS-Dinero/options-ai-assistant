"""workspace/post_action_engine.py — Builds next follow-up tasks after action."""
from __future__ import annotations
from typing import Any

FOLLOWUP: dict = {
    "EXECUTE_TICKET":   [{"task":"LOG_EXECUTION_OUTCOME","summary":"Capture fill quality and update transition journal."},
                          {"task":"SET_FOLLOWUP_REVIEW","summary":"Schedule next campaign review checkpoint."}],
    "DEFER_PATH":       [{"task":"SET_RECHECK_TRIGGER","summary":"Re-evaluate when timing/surface improves."}],
    "ESCALATE_REVIEW":  [{"task":"LINK_REVIEW_PACKET","summary":"Attach review object to workspace."}],
    "CHANGE_PATH":      [{"task":"REBUILD_FORWARD_PLAN","summary":"Recompute comparative paths for new selection."}],
}

def build_post_action_tasks(workspace: dict[str,Any]) -> list[dict[str,Any]]:
    actions=workspace.get("captured_actions",[])
    if not actions: return []
    return FOLLOWUP.get(actions[-1].get("action_type",""),[])
