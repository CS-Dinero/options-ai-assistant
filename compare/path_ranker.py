"""compare/path_ranker.py — Ranks paths and merges decomposition + score + tradeoff."""
from __future__ import annotations
from typing import Any
from compare.path_candidate_builder import build_path_candidates
from compare.path_decomposition_engine import decompose_path
from compare.path_scoring_engine import score_path
from compare.path_tradeoff_engine import explain_path_tradeoffs

def rank_paths(row: dict[str,Any], active_mandate: str) -> list[dict[str,Any]]:
    scored=[{**decompose_path(c["path_code"],row),**score_path(c["path_code"],row,active_mandate)}
            for c in build_path_candidates(row)]
    scored.sort(key=lambda x: x["path_total_score"],reverse=True)
    tradeoffs={t["path_code"]:t["tradeoff_note"] for t in explain_path_tradeoffs(scored)}
    for item in scored: item["tradeoff_note"]=tradeoffs.get(item["path_code"],"")
    return scored
