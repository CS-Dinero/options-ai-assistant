"""
journal/transition_journal.py
Records the full decision snapshot at the moment of each transition recommendation.
Records both the chosen action AND all rejected alternatives for empirical learning.
"""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_transition_journal_entry(
    position_row:      dict[str, Any],
    transition_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "journal_id":              str(uuid.uuid4()),
        "timestamp_utc":           datetime.utcnow().isoformat(),
        "campaign_id":             position_row.get("campaign_id"),
        "position_id":             position_row.get("trade_id") or position_row.get("id"),
        "symbol":                  position_row.get("symbol"),
        "current_structure_type":  position_row.get("strategy_type") or position_row.get("structure_type"),
        "approved_action":         transition_result.get("recommended_action"),
        "approved_rebuild_class":  transition_result.get("rebuild_class","KEEP_LONG"),
        "approved_transition_credit":   float(transition_result.get("transition_net_credit",0)),
        "approved_future_roll_score":   float(transition_result.get("future_roll_score",0)),
        "approved_composite_score":     float(transition_result.get("composite_score",0)),
        "approved_avg_path_score":      float(transition_result.get("avg_path_score",0)),
        "approved_worst_path_score":    float(transition_result.get("worst_path_score",0)),
        "approved_target_width":        (transition_result.get("new_structure") or {}).get("target_width"),
        "campaign_net_basis_before":    float(transition_result.get("campaign_net_basis_before",0)),
        "campaign_net_basis_after":     float(transition_result.get("campaign_net_basis_after",0)),
        "recovered_pct_before":         float(transition_result.get("recovered_pct_before",0)),
        "recovered_pct_after":          float(transition_result.get("recovered_pct_after",0)),
        "approved_new_structure":       transition_result.get("new_structure"),
        "approval_notes":               transition_result.get("why",[]),
        "rejected_candidates":          transition_result.get("rejected_candidates",[]),
        "scenario_results":             transition_result.get("scenario_results",[]),
        "status":                       "PENDING_OUTCOME",
    }

def mark_journal_executed(entry: dict[str,Any], execution_info: dict[str,Any]) -> dict[str,Any]:
    u = dict(entry)
    u["status"] = "EXECUTED"
    u["execution_timestamp_utc"] = execution_info.get("execution_timestamp_utc", datetime.utcnow().isoformat())
    u["execution_fill_credit"]   = float(execution_info.get("execution_fill_credit", entry.get("approved_transition_credit",0)))
    u["execution_notes"]         = execution_info.get("execution_notes",[])
    return u
