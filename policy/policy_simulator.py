"""policy/policy_simulator.py — Re-runs policy-sensitive layers under a scenario override."""
from __future__ import annotations
from typing import Any, Callable
from copy import deepcopy
from policy.policy_override_engine import apply_policy_overrides
from portfolio.capital_rotation_engine import evaluate_capital_rotation
from portfolio.transition_queue_engine import build_transition_queue

def _default_recalc_capital(row: dict, all_rows: list[dict], bundle: dict) -> None:
    try:
        rot = evaluate_capital_rotation(all_rows, row, bundle)
        row["playbook_status"]            = rot.get("effective_status", row.get("playbook_status","WATCHLIST"))
        row["capital_commitment_decision"]= rot.get("capital_commitment_decision","NO_ADD")
        row["capital_commitment_ok"]      = rot.get("capital_commitment_ok",False)
        row["transition_final_contract_add"]=rot.get("final_contract_add",0)
        row["symbol_concurrency_ok"]      = rot.get("symbol_concurrency_ok",True)
        row["playbook_concurrency_ok"]    = rot.get("playbook_concurrency_ok",True)
        # Update playbook_queue_bias from bundle
        pb_reg = bundle.get("playbook_policy_registry",{})
        code   = row.get("playbook_code","")
        if code in pb_reg: row["playbook_queue_bias"] = float(pb_reg[code].get("queue_bias",0.0))
    except Exception: pass

def _default_recalc_execution(row: dict, bundle: dict) -> None:
    overrides = bundle.get("execution_policy_overrides",{})
    rb = row.get("transition_rebuild_class","KEEP_LONG")
    if rb in overrides:
        forced = overrides[rb].get("force_policy")
        if forced: row["transition_execution_policy"] = forced
    thr = bundle.get("surface_threshold_override")
    if thr and float(row.get("transition_execution_surface_score",0)) < thr:
        row["transition_execution_surface_ok"] = False

def simulate_policy_scenario(
    rows: list[dict[str,Any]],
    live_policy_bundle: dict[str,Any],
    scenario_overrides: dict[str,Any],
    recalc_capital_fn: Callable|None = None,
    recalc_execution_fn: Callable|None = None,
) -> dict[str,Any]:
    sim_rows   = deepcopy(rows)
    sim_bundle = apply_policy_overrides(live_policy_bundle, scenario_overrides)
    rcap  = recalc_capital_fn   or _default_recalc_capital
    rexec = recalc_execution_fn or _default_recalc_execution
    for row in sim_rows:
        rcap(row, sim_rows, sim_bundle)
        rexec(row, sim_bundle)
    sim_queue = build_transition_queue(sim_rows)
    return {"simulated_rows":sim_rows,"simulated_queue":sim_queue,"simulated_policy_bundle":sim_bundle}
