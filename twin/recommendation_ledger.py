"""twin/recommendation_ledger.py — Stores what the system recommended."""
from __future__ import annotations
from typing import Any

def build_system_recommendation_entry(twin_id: str, ranked_paths: list[dict[str,Any]],
                                       capital_decision: dict[str,Any]|None=None,
                                       rationale: str="") -> dict[str,Any]:
    best=ranked_paths[0] if ranked_paths else {}; alt=ranked_paths[1] if len(ranked_paths)>1 else {}
    gap=round(float(best.get("path_total_score",0))-float(alt.get("path_total_score",0)),2) if best and alt else None
    return {"twin_id":twin_id,"recommended_path_code":best.get("path_code"),
            "recommended_path_score":best.get("path_total_score"),
            "alternative_path_code":alt.get("path_code"),"alternative_path_score":alt.get("path_total_score"),
            "score_gap":gap,"capital_deployment_label":(capital_decision or {}).get("capital_deployment_label"),
            "capital_contract_add":(capital_decision or {}).get("final_contract_add"),
            "rationale_snapshot":rationale}
