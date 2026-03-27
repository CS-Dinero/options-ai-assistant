"""doctrine/constraint_engine.py — Converts principles into enforceable constraints."""
from __future__ import annotations
from typing import Any

def build_doctrine_constraints(charter: dict[str,Any]) -> dict[str,Any]:
    p=set(charter.get("active_principles",[]))
    return {
        "block_live_size_expansion_under_weak_maturity": "CAPITAL_PRESERVATION_FIRST" in p,
        "block_live_rollout_without_validation":         "LIVE_SAFETY_OVER_SPEED" in p,
        "block_direct_live_mutation_from_refinement":    "GOVERNANCE_OVER_CONVENIENCE" in p,
        "block_execution_integrity_compromise":          "EXECUTION_INTEGRITY_OVER_QUEUE_VOLUME" in p,
        "require_human_owner_for_material_live_change":  "HUMAN_ACCOUNTABILITY_FOR_LIVE_CHANGES" in p,
        "require_rollback_plan_for_broad_change":        "REVERSIBILITY_FOR_HIGH_BLAST_RADIUS" in p,
    }
