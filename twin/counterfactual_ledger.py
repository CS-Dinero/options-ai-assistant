"""twin/counterfactual_ledger.py — Stores the main alternatives not chosen."""
from __future__ import annotations
from typing import Any

def build_counterfactual_entries(twin_id: str, ranked_paths: list[dict[str,Any]], limit: int=3) -> list[dict[str,Any]]:
    return [{"twin_id":twin_id,"path_code":p.get("path_code"),"path_score":p.get("path_total_score"),
             "basis_recovery_score":p.get("basis_recovery_score"),"execution_quality_score":p.get("execution_quality_score"),
             "capital_efficiency_score":p.get("capital_efficiency_score"),
             "review_pressure_score":p.get("review_pressure_score"),"tradeoff_note":p.get("tradeoff_note")}
            for p in ranked_paths[:limit]]
