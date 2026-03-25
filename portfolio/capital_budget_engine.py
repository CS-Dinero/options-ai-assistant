"""portfolio/capital_budget_engine.py — Tracks basis-at-risk and capital recycling quality."""
from __future__ import annotations
from typing import Any

DEFAULT_LIMITS = {
    "max_total_campaign_basis": 10000.0,
    "max_symbol_basis_pct":     0.35,
    "max_structure_basis_pct":  0.50,
    "min_recycling_score":      60.0,
}

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def evaluate_capital_budget(
    portfolio_state: dict[str,Any],
    candidate_row:   dict[str,Any],
    limits:          dict[str,Any]|None = None,
) -> dict[str,Any]:
    L=limits or DEFAULT_LIMITS
    total_basis  = _sf(portfolio_state.get("total_campaign_basis"))
    sym_basis    = portfolio_state.get("symbol_basis",{})
    symbol       = str(candidate_row.get("symbol",""))
    basis_before = _sf(candidate_row.get("campaign_net_basis") or candidate_row.get("net_liq"))
    basis_after  = _sf(candidate_row.get("transition_campaign_net_basis_after",basis_before))
    reduction    = basis_before - basis_after
    total_after  = total_basis - reduction
    headroom     = L["max_total_campaign_basis"] - total_after
    cur_sym      = _sf(sym_basis.get(symbol,0))
    proj_sym     = cur_sym - reduction
    sym_pct_after= proj_sym/total_after if total_after>0 else 0.0
    recycling    = max(0.0,min(100.0,(reduction/basis_before)*100)) if basis_before>0 else 0.0
    ok           = (total_after<=L["max_total_campaign_basis"] and sym_pct_after<=L["max_symbol_basis_pct"])
    notes=[]
    if reduction>0: notes.append(f"basis recycled ${reduction:.2f}")
    if sym_pct_after>L["max_symbol_basis_pct"]: notes.append("symbol concentration exceeds limit")
    if recycling<L["min_recycling_score"]: notes.append("capital recycling quality weak")
    return {
        "candidate_basis_before":    round(basis_before,2),
        "candidate_basis_after":     round(basis_after,2),
        "candidate_basis_reduction": round(reduction,2),
        "total_basis_after":         round(total_after,2),
        "basis_headroom_after":      round(headroom,2),
        "symbol_basis_pct_after":    round(sym_pct_after,4),
        "recycling_score":           round(recycling,2),
        "capital_budget_ok":         ok,
        "notes": notes,
    }
