"""diagnostics/gate_failure_engine.py — Measures which gates fail most often."""
from __future__ import annotations
from typing import Any

def analyze_gate_failures(rows: list[dict[str,Any]]) -> dict[str,Any]:
    n=max(1,len(rows))
    sf=sum(1 for r in rows if r.get("transition_execution_surface_ok") is False)
    tf=sum(1 for r in rows if r.get("transition_timing_ok") is False)
    pf=sum(1 for r in rows if r.get("transition_portfolio_fit_ok") is False)
    cf=sum(1 for r in rows if r.get("capital_commitment_ok") is False)
    ccf=sum(1 for r in rows if not r.get("symbol_concurrency_ok",True) or not r.get("playbook_concurrency_ok",True))
    return {"surface_fail_count":sf,"timing_fail_count":tf,"portfolio_fail_count":pf,
            "capital_fail_count":cf,"concurrency_fail_count":ccf,
            "surface_fail_pct":round(sf/n,4),"timing_fail_pct":round(tf/n,4),
            "portfolio_fail_pct":round(pf/n,4),"capital_fail_pct":round(cf/n,4),
            "concurrency_fail_pct":round(ccf/n,4)}
