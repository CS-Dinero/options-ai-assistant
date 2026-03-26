"""ops/job_context_builder.py — Builds runtime context for each job."""
from __future__ import annotations
from typing import Any

def build_job_context(environment: str, live_policy_version: dict[str,Any]|None,
                      rows: list[dict[str,Any]], queue: list[dict[str,Any]],
                      metrics: dict[str,Any], diagnostics: dict[str,Any],
                      slippage_model: dict[str,Any], playbook_stats: dict[str,Any],
                      exposure_metrics: dict[str,Any], portfolio_state: dict[str,Any],
                      alerts: list[dict[str,Any]]|None=None,
                      validation_summary: dict[str,Any]|None=None,
                      global_context: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"environment":environment,"live_policy_version":live_policy_version,
            "rows":rows,"queue":queue,"metrics":metrics,"diagnostics":diagnostics,
            "slippage_model":slippage_model,"playbook_stats":playbook_stats,
            "exposure_metrics":exposure_metrics,"portfolio_state":portfolio_state,
            "alerts":alerts or [],"validation_summary":validation_summary or {},
            "global_context":global_context or {}}
