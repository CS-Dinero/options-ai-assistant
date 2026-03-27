"""twin/twin_snapshot_builder.py — Captures a decision moment in full context."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_decision_moment_snapshot(environment: str, row: dict[str,Any], ranked_paths: list[dict[str,Any]],
                                    active_mandate: str, live_policy_version_id: str|None,
                                    risk_envelope: str="NORMAL",
                                    forecast_confidence: dict[str,Any]|None=None) -> dict[str,Any]:
    best=ranked_paths[0] if ranked_paths else {}; fc=forecast_confidence or {}
    return {"twin_id":str(uuid.uuid4()),"environment":environment,
            "timestamp_utc":datetime.utcnow().isoformat(),
            "symbol":row.get("symbol"),"campaign_id":row.get("campaign_id"),"position_id":row.get("id"),
            "playbook_code":row.get("playbook_code"),"active_mandate":active_mandate,
            "live_policy_version_id":live_policy_version_id,"risk_envelope":risk_envelope,
            "forecast_confidence_score":fc.get("forecast_confidence_score"),
            "forecast_confidence_label":fc.get("forecast_confidence_label"),
            "best_path_code":best.get("path_code"),"ranked_paths":ranked_paths,
            "constraints":{"timing_ok":row.get("transition_timing_ok"),
                           "surface_ok":row.get("transition_execution_surface_ok"),
                           "portfolio_fit_ok":row.get("transition_portfolio_fit_ok"),
                           "capital_commitment_ok":row.get("capital_commitment_ok")}}
