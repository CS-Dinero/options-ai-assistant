"""portfolio/capital_commitment_engine.py — Final ALLOW_FULL/ALLOW_NORMAL/ALLOW_REDUCED/BLOCK decision."""
from __future__ import annotations
from typing import Any

def evaluate_capital_commitment(
    candidate_row: dict[str,Any],
    playbook_policy: dict[str,Any],
    concurrency_eval: dict[str,Any],
    sizing_eval: dict[str,Any],
) -> dict[str,Any]:
    cap_ok  = bool(candidate_row.get("transition_capital_budget_ok",True))
    port_ok = bool(candidate_row.get("transition_portfolio_fit_ok",True))
    conc_ok = bool(concurrency_eval.get("concurrency_ok",True))
    final   = int(sizing_eval.get("final_contract_add",0))
    status  = str(candidate_row.get("playbook_status","WATCHLIST"))

    if not cap_ok or not port_ok or not conc_ok:
        decision="BLOCK_EXPANSION"
    elif final<=0: decision="NO_ADD"
    elif status=="PROMOTED":   decision="ALLOW_FULL"
    elif status=="WATCHLIST":  decision="ALLOW_NORMAL"
    else:                      decision="ALLOW_REDUCED"

    notes={
        "BLOCK_EXPANSION":["capital, portfolio, or concurrency gate blocked scaling"],
        "ALLOW_FULL":["playbook status and portfolio conditions support full allocation"],
        "ALLOW_NORMAL":["baseline capital commitment approved"],
        "ALLOW_REDUCED":["capital commitment reduced due to cautious playbook status"],
        "NO_ADD":["no add recommended"],
    }.get(decision,["unknown decision"])

    return {"capital_commitment_decision":decision,
            "capital_commitment_ok":decision in("ALLOW_FULL","ALLOW_NORMAL","ALLOW_REDUCED"),
            "notes":notes}
