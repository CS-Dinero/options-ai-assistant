"""stress/stress_simulator.py — Re-runs queue/capital/alert/refinement under stress."""
from __future__ import annotations
from typing import Any, Callable
from copy import deepcopy
from portfolio.transition_queue_engine import build_transition_queue
from monitoring.metric_engine import compute_operational_metrics
from monitoring.threshold_registry import get_thresholds
from monitoring.alert_rule_engine import build_alerts
from meta.refinement_candidate_engine import build_refinement_candidates
from diagnostics.diagnostics_report_engine import build_diagnostics_report

def simulate_stress_scenario(
    rows: list[dict[str,Any]], queue: list[dict[str,Any]],
    exposure_metrics: dict[str,Any], active_mandate: str, scenario: dict[str,Any],
    environment: str="DEV",
) -> dict[str,Any]:
    stressed_rows=deepcopy(rows); stressed_exp=deepcopy(exposure_metrics)

    for shock in scenario.get("shocks",[]):
        fn=shock.get("fn"); kwargs=shock.get("kwargs",{})
        shock_type=shock.get("type","ROWS")
        if fn:
            if shock_type=="ROWS":    stressed_rows=fn(stressed_rows,**kwargs)
            elif shock_type=="EXPOSURE": stressed_exp=fn(stressed_exp,**kwargs)

    stressed_mandate=scenario.get("effective_mandate",active_mandate)

    try:
        from mandate.mandate_weight_engine import apply_mandate_queue_weights
        stressed_rows=[apply_mandate_queue_weights(r,stressed_mandate) for r in stressed_rows]
    except: pass

    stressed_queue=build_transition_queue(stressed_rows)
    stressed_metrics=compute_operational_metrics(stressed_rows,stressed_queue,{},{},stressed_exp)
    stressed_alerts=builds_alerts=build_alerts(stressed_metrics,get_thresholds(environment),environment)
    stressed_diag=build_diagnostics_report(stressed_rows,stressed_queue,{},{})
    stressed_refinements=build_refinement_candidates(stressed_diag,{},{},{},{},stressed_metrics)

    return {"scenario_name":scenario.get("scenario_name"),"stressed_mandate":stressed_mandate,
            "stressed_rows":stressed_rows,"stressed_queue":stressed_queue,
            "stressed_metrics":stressed_metrics,"stressed_alerts":stressed_alerts,
            "stressed_refinements":stressed_refinements,"stressed_exposure_metrics":stressed_exp}
