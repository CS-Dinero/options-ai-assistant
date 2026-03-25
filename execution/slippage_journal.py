"""execution/slippage_journal.py — Stores per-execution fill observations."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_slippage_entry(position_row, ticket, execution_result, fill_eval) -> dict[str,Any]:
    return {
        "slippage_id":      str(uuid.uuid4()),
        "timestamp_utc":    datetime.utcnow().isoformat(),
        "journal_id":       position_row.get("transition_journal_id"),
        "symbol":           position_row.get("symbol"),
        "action":           position_row.get("transition_action"),
        "rebuild_class":    position_row.get("transition_rebuild_class"),
        "target_width":     position_row.get("transition_target_width"),
        "time_window":      position_row.get("transition_time_window"),
        "execution_policy": position_row.get("transition_execution_policy"),
        "timing_score":     float(position_row.get("transition_timing_score",0)),
        "surface_score":    float(position_row.get("transition_execution_surface_score",0)),
        "liquidity_score":  float(position_row.get("transition_liquidity_score",0)),
        "expected_credit":  fill_eval.get("expected_credit",0),
        "actual_credit":    fill_eval.get("actual_credit",0),
        "slippage_dollars": fill_eval.get("slippage_dollars",0),
        "slippage_pct":     fill_eval.get("slippage_pct",0),
        "fill_score":       fill_eval.get("fill_score",0),
        "notes":            fill_eval.get("notes",[]),
    }

def append_slippage_journal(store, entry):
    return list(store or []) + [entry]
