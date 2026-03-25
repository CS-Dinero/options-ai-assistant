"""portfolio/capital_rotation_engine.py — Orchestrates playbook policy → concurrency → sizing → commitment."""
from __future__ import annotations
from typing import Any
from portfolio.playbook_capital_policy import get_capital_policy
from portfolio.concurrency_limits_engine import evaluate_concurrency_limits
from portfolio.position_sizing_engine import compute_position_size_adjustment
from portfolio.capital_commitment_engine import evaluate_capital_commitment

def evaluate_capital_rotation(
    rows: list[dict[str,Any]],
    candidate_row: dict[str,Any],
    policy_bundle: dict|None = None,
) -> dict[str,Any]:
    policy_bundle = policy_bundle or {}
    status = str(candidate_row.get("playbook_status","WATCHLIST"))

    # Allow bundle overrides
    pb_reg  = policy_bundle.get("playbook_policy_registry",{})
    if pb_reg and candidate_row.get("playbook_code") in pb_reg:
        status = pb_reg[candidate_row["playbook_code"]].get("status", status)

    cap_policy = policy_bundle.get("playbook_capital_policy",{}).get(status) or get_capital_policy(status)
    sym_overrides = policy_bundle.get("symbol_concurrency_overrides",{})

    conc = evaluate_concurrency_limits(rows, candidate_row, cap_policy, sym_overrides)
    size = compute_position_size_adjustment(candidate_row, cap_policy)
    comm = evaluate_capital_commitment(candidate_row, cap_policy, conc, size)

    return {"playbook_policy":cap_policy,"effective_status":status,**conc,**size,**comm}
