"""
journal/transition_outcome_evaluator.py
Evaluates what happened after a transition was executed.
Compares expected vs actual outcomes across basis, credit, and rollability.
"""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def evaluate_transition_outcome(
    journal_entry:          dict[str, Any],
    latest_position_snapshot: dict[str, Any],
    followup_market_context:  dict[str, Any],
) -> dict[str, Any]:
    expected_credit = _sf(journal_entry.get("approved_transition_credit"))
    actual_credit   = _sf(journal_entry.get("execution_fill_credit", expected_credit))
    exp_basis_after = _sf(journal_entry.get("campaign_net_basis_after"))
    act_basis_now   = _sf(latest_position_snapshot.get("campaign_net_basis", exp_basis_after))
    unrealized      = _sf(latest_position_snapshot.get("unrealized_pnl") or latest_position_snapshot.get("net_liq",0))
    future_roll     = _sf(latest_position_snapshot.get("future_roll_score") or latest_position_snapshot.get("transition_future_roll_score",0))

    # Score components
    basis_imp = exp_basis_after - act_basis_now
    if   basis_imp>=1.0:  basis_s=100.0
    elif basis_imp>=0.5:  basis_s=75.0
    elif basis_imp>=0.0:  basis_s=55.0
    elif basis_imp>=-0.5: basis_s=35.0
    else:                 basis_s=0.0

    credit_s = max(0.0, min(100.0, (actual_credit/expected_credit)*100)) if expected_credit>0 else 0.0

    if   unrealized>=1.0:  pnl_s=100.0
    elif unrealized>=0.0:  pnl_s=70.0
    elif unrealized>=-1.0: pnl_s=40.0
    else:                  pnl_s=15.0

    outcome = round(0.30*basis_s + 0.25*credit_s + 0.25*min(future_roll,100) + 0.20*pnl_s, 2)
    success = outcome>=65.0

    notes=[]
    if basis_s>=75: notes.append("campaign basis progressed favorably")
    if credit_s<70: notes.append("fill quality underperformed expected credit")
    if future_roll>=65: notes.append("follow-on rollability remained intact")
    if pnl_s<40: notes.append("mark-to-market follow-up was weak")

    return {
        "expected_credit": expected_credit, "actual_credit": actual_credit,
        "expected_basis_after": exp_basis_after, "actual_basis_now": act_basis_now,
        "basis_progress_score": basis_s, "credit_realization_score": credit_s,
        "followon_rollability_score": min(future_roll,100), "unrealized_pnl_score": pnl_s,
        "outcome_score": outcome, "success": success, "notes": notes,
    }
