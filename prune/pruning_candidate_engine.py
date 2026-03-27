"""prune/pruning_candidate_engine.py — Builds candidates from attribution and usage signals."""
from __future__ import annotations
from typing import Any

def build_pruning_candidates(component_attribution: dict[str,Any],
                              interaction_attribution: dict[str,Any],
                              usage_stats: dict[str,Any]|None=None) -> list[dict[str,Any]]:
    usage_stats=usage_stats or {}; candidates=[]
    for family,items in component_attribution.items():
        for cid,stats in items.items():
            roi=float(stats.get("avg_roi_score",0)); friction=float(stats.get("avg_friction_score",0))
            usage=int((usage_stats.get(family) or {}).get(cid,0))
            if roi<0 and friction>=25:
                candidates.append({"component_family":family,"component_id":cid,"candidate_type":"RETIRE_OR_DEMOTE",
                                    "evidence":stats,"usage_count":usage,"reason":"negative ROI with meaningful friction"})
            elif roi<15 and friction>=15:
                candidates.append({"component_family":family,"component_id":cid,"candidate_type":"SIMPLIFY",
                                    "evidence":stats,"usage_count":usage,"reason":"marginal ROI with persistent friction"})
            elif usage<=2 and roi<10:
                candidates.append({"component_family":family,"component_id":cid,"candidate_type":"OPTIONALIZE",
                                    "evidence":stats,"usage_count":usage,"reason":"low usage and limited value contribution"})
    return candidates
