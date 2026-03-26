"""meta/refinement_policy_mapper.py — Maps refinement candidates to concrete policy overrides."""
from __future__ import annotations
from typing import Any

def map_refinement_to_policy_change(candidate: dict[str,Any]) -> dict[str,Any]:
    rt=candidate.get("refinement_type"); p=candidate.get("proposed_change",{}) or {}
    if rt=="REVIEW_PLAYBOOK_STATUS_DOWN":
        return {"playbook_status_overrides":{p.get("playbook_code"):p.get("suggested_status","WATCHLIST")}}
    if rt=="REVIEW_PLAYBOOK_STATUS_UP":
        return {"playbook_status_overrides":{p.get("playbook_code"):p.get("suggested_status","PROMOTED")}}
    if rt=="TIGHTEN_EXECUTION_POLICY":
        return {"execution_policy_overrides":{p.get("symbol","?"):{"force_policy":"STAGGER","note":p.get("action")}}}
    if rt=="REVIEW_STAGGER_RULES":
        return {"execution_policy_overrides":{"REPLACE_LONG":{"force_policy":"STAGGER"}}}
    if rt=="REVIEW_SURFACE_THRESHOLD":
        return {"surface_threshold_override":68.0}
    if rt=="REVIEW_CAPITAL_CONSTRAINTS":
        return {"status_policy_overrides":{"LIMITED_USE":{"size_multiplier":0.55}}}
    return {}
