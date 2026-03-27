"""doctrine/doctrine_guard_engine.py — Inspects proposals for doctrine violations."""
from __future__ import annotations
from typing import Any

def evaluate_doctrine_guard(charter_constraints: dict[str,Any], proposal: dict[str,Any]) -> dict[str,Any]:
    violations=[]
    if charter_constraints.get("block_direct_live_mutation_from_refinement"):
        if proposal.get("source_type")=="REFINEMENT" and proposal.get("target_environment")=="LIVE":
            if proposal.get("bypasses_review",False):
                violations.append("Refinement may not directly mutate LIVE behavior without governance.")
    if charter_constraints.get("block_live_rollout_without_validation"):
        if proposal.get("target_environment")=="LIVE" and not proposal.get("validation_complete",False):
            violations.append("LIVE rollout without required validation is blocked by doctrine.")
    if charter_constraints.get("block_live_size_expansion_under_weak_maturity"):
        if proposal.get("proposal_type")=="CAPITAL_EXPANSION" and proposal.get("maturity_level") in("PROTOTYPE","USABLE"):
            violations.append("Capital expansion under weak maturity violates capital-preservation doctrine.")
    if charter_constraints.get("require_rollback_plan_for_broad_change"):
        if float(proposal.get("blast_radius",0))>=60 and not proposal.get("has_rollback_plan",False):
            violations.append("High-blast-radius change requires rollback plan.")
    if charter_constraints.get("require_human_owner_for_material_live_change"):
        if proposal.get("target_environment")=="LIVE" and not proposal.get("human_owner"):
            violations.append("Material LIVE change requires an explicit human owner.")
    return {"allowed":len(violations)==0,"violations":violations}
