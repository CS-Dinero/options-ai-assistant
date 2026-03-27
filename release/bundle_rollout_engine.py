"""release/bundle_rollout_engine.py — Defines rollout sequencing across environments."""
from __future__ import annotations
from typing import Any

def build_rollout_plan(bundle_type: str, validation_requirements: dict[str,Any]) -> dict[str,Any]:
    return {"rollout_sequence":[
                {"environment":"DEV","action":"VALIDATE_AND_SIMULATE"},
                {"environment":"SIM","action":"PROMOTE_AND_OBSERVE"},
                {"environment":"LIVE","action":"ACTIVATE_IF_APPROVED"}],
            "requires_live_approval":True,
            "requires_sim_observation":validation_requirements.get("requires_stress_test",False)}
