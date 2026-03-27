"""workspace/path_workspace_builder.py — Builds the main execution workspace."""
from __future__ import annotations
from typing import Any
from workspace.workspace_state_builder import build_workspace_state

def build_path_execution_workspace(environment: str, row: dict[str,Any],
                                    ranked_paths: list[dict[str,Any]],
                                    forward_plan: dict[str,Any]|None=None) -> dict[str,Any]:
    selected=ranked_paths[0] if ranked_paths else {}; alt=ranked_paths[1] if len(ranked_paths)>1 else None
    ws=build_workspace_state(environment,"PATH_EXECUTION_WORKSPACE",str(row.get("symbol","?")),selected,
                              {"position_id":row.get("id"),"campaign_id":row.get("campaign_id"),
                               "playbook_code":row.get("playbook_code")})
    ws["primary_rationale"]=row.get("transition_winner_summary","")
    ws["alternative_path"]=alt; ws["forward_plan"]=forward_plan or {}
    ws["knowledge_context_summaries"]=row.get("knowledge_context_summaries",[])
    ws["review_links"]=row.get("linked_review_ids",[])
    return ws
