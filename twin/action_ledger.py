"""twin/action_ledger.py — Stores what humans approved and what was actually executed."""
from __future__ import annotations
from typing import Any
from datetime import datetime

def build_approved_action_entry(twin_id: str, actor: str, chosen_path_code: str,
                                 decision_type: str, rationale: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"twin_id":twin_id,"actor":actor,"approved_utc":datetime.utcnow().isoformat(),
            "chosen_path_code":chosen_path_code,"decision_type":decision_type,"rationale":rationale or {}}

def build_executed_action_entry(twin_id: str, execution_status: str,
                                 executed_path_code: str|None=None, execution_note: str="") -> dict[str,Any]:
    return {"twin_id":twin_id,"executed_utc":datetime.utcnow().isoformat(),"execution_status":execution_status,
            "executed_path_code":executed_path_code,"execution_note":execution_note}
