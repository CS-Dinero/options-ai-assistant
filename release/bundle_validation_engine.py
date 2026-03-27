"""release/bundle_validation_engine.py — Determines required validation suites for a bundle."""
from __future__ import annotations
from typing import Any

def build_bundle_validation_requirements(scope: dict[str,Any]) -> dict[str,Any]:
    impacted=set(scope.get("impacted_components",[])); full=bool(scope.get("touches_core_flow",False))
    suites=set()
    if full: suites.update({"engine","workflow","policy","portfolio","execution","research","control_plane"})
    if any("execution" in c for c in impacted): suites.add("execution")
    if any("workflow" in c for c in impacted): suites.add("workflow")
    if any("policy" in c or "mandate" in c for c in impacted): suites.add("policy")
    if any("queue" in c or "capital" in c for c in impacted): suites.add("portfolio")
    return {"required_validation_suites":sorted(suites),
            "requires_policy_simulation":"policy" in suites,
            "requires_stress_test":full or "execution" in suites or "portfolio" in suites}
