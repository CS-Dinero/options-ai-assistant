"""
engines/campaign_economics_engine.py
Evaluates whether a transition improves the FULL campaign, not just the current trade.
"""
from __future__ import annotations
from typing import Any
from position_manager.campaign_memory import compute_campaign_net_basis, compute_recovered_pct

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def _improvement_score(basis_reduction, recovered_gain, credit, future_roll):
    basis_s    = max(0.0, min(100.0, basis_reduction*25.0))
    recovered_s= max(0.0, min(100.0, recovered_gain*4.0))
    credit_s   = max(0.0, min(100.0, credit*50.0))
    future_s   = max(0.0, min(100.0, future_roll))
    return round(0.35*basis_s + 0.25*recovered_s + 0.20*credit_s + 0.20*future_s, 2)

def evaluate_campaign_economics(
    current_position:     dict[str, Any],
    campaign_memory:      dict[str, Any],
    transition_candidate: dict[str, Any],
    market_context:       dict[str, Any],
) -> dict[str, Any]:
    basis_before    = compute_campaign_net_basis(campaign_memory)
    recovered_before= compute_recovered_pct(campaign_memory)
    credit          = _sf(transition_candidate.get("transition_net_credit"))
    future_roll     = _sf(transition_candidate.get("future_roll_score", 50.0))
    orig            = _sf(campaign_memory.get("original_entry_cost"))

    basis_after     = round(basis_before - credit, 4)
    if orig > 0:
        recovered_after = round((
            (_sf(campaign_memory.get("cumulative_realized_credit")) + credit
             - _sf(campaign_memory.get("cumulative_realized_debit"))
             - _sf(campaign_memory.get("cumulative_fees"))) / orig
        )*100, 2)
    else:
        recovered_after = recovered_before

    basis_reduction  = round(basis_before - basis_after, 4)
    recovered_gain   = round(recovered_after - recovered_before, 2)
    imp_score        = _improvement_score(basis_reduction, recovered_gain, credit, future_roll)
    improves         = (basis_reduction > 0 and imp_score >= 60.0)

    notes = []
    if basis_reduction > 0: notes.append(f"basis reduced by ${basis_reduction:.2f}")
    if recovered_gain > 0:  notes.append(f"recovery improved by {recovered_gain:.1f}%")
    if basis_after <= 0:    notes.append("campaign basis fully recovered or better")
    if not improves:        notes.append("does not materially improve campaign economics")

    return {
        "campaign_net_basis_before":  basis_before,
        "campaign_net_basis_after":   basis_after,
        "basis_reduction":            basis_reduction,
        "recovered_pct_before":       recovered_before,
        "recovered_pct_after":        recovered_after,
        "campaign_improvement_score": imp_score,
        "transition_improves_campaign": improves,
        "notes": notes,
    }
