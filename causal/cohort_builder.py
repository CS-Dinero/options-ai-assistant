"""causal/cohort_builder.py — Builds treated cohorts from intervention scope."""
from __future__ import annotations
from typing import Any

def build_treated_cohort(rows: list[dict[str,Any]], intervention: dict[str,Any]) -> list[dict[str,Any]]:
    scope=intervention.get("target_scope",{}); env=intervention.get("environment")
    eff=intervention.get("effective_utc","")
    return [r for r in rows
            if (not env or r.get("environment")==env)
            and (not eff or str(r.get("timestamp_utc",""))>=eff)
            and all(r.get(k)==v for k,v in scope.items())]

def build_before_cohort(rows: list[dict[str,Any]], intervention: dict[str,Any]) -> list[dict[str,Any]]:
    scope=intervention.get("target_scope",{}); env=intervention.get("environment")
    eff=intervention.get("effective_utc","")
    return [r for r in rows
            if (not env or r.get("environment")==env)
            and (not eff or str(r.get("timestamp_utc",""))<eff)
            and all(r.get(k)==v for k,v in scope.items())]
