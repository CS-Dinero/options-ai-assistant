"""command/executive_state_builder.py — Gathers current state into one executive object."""
from __future__ import annotations
from typing import Any

def build_executive_state(environment: str, active_mandate: str,
                           live_policy_version: dict[str,Any]|None, active_risk_envelope: str,
                           capital_budget: dict[str,Any], queue: list[dict[str,Any]],
                           alerts: list[dict[str,Any]], reviews: list[dict[str,Any]],
                           releases: list[dict[str,Any]], maturity_results: dict[str,Any],
                           attribution_summary: dict[str,Any],
                           causal_summary: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"environment":environment,"active_mandate":active_mandate,
            "live_policy_version_id":(live_policy_version or {}).get("policy_version_id"),
            "active_risk_envelope":active_risk_envelope,"capital_budget":capital_budget,
            "queue":queue,"alerts":alerts,"reviews":reviews,"releases":releases,
            "maturity_results":maturity_results,"attribution_summary":attribution_summary,
            "causal_summary":causal_summary or {}}
