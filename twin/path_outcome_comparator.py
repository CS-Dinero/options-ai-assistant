"""twin/path_outcome_comparator.py — Compares actual chosen path vs alternatives."""
from __future__ import annotations
from typing import Any

def compare_realized_vs_counterfactual(realized_outcome: dict[str,Any],
                                        counterfactual_entries: list[dict[str,Any]],
                                        chosen_path_code: str|None) -> dict[str,Any]:
    chosen_score=float(realized_outcome.get("outcome_score",0.0))
    next_best=next((e for e in counterfactual_entries if e.get("path_code")!=chosen_path_code),None)
    nb_score=float(next_best.get("path_score",0)) if next_best else None
    delta=round(chosen_score-nb_score,2) if nb_score is not None else None
    return {"chosen_path_code":chosen_path_code,"chosen_outcome_score":chosen_score,
            "next_best_counterfactual_path":next_best.get("path_code") if next_best else None,
            "next_best_counterfactual_score":nb_score,"chosen_vs_counterfactual_delta":delta}
