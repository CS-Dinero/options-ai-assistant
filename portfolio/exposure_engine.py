"""portfolio/exposure_engine.py — Converts portfolio state into exposure metrics."""
from __future__ import annotations
from typing import Any

def compute_exposure_metrics(portfolio_state: dict[str,Any]) -> dict[str,Any]:
    n    = max(1, int(portfolio_state.get("position_count",0)))
    syms = portfolio_state.get("symbol_counts",{})
    structs=portfolio_state.get("structure_counts",{})
    bull = int(portfolio_state.get("bullish_count",0))
    bear = int(portfolio_state.get("bearish_count",0))
    neut = int(portfolio_state.get("neutral_count",0))

    sym_conc    = {s:round(c/n,4) for s,c in syms.items()}
    struct_conc = {s:round(c/n,4) for s,c in structs.items()}
    top_sym, top_sym_r   = max(sym_conc.items(),    key=lambda x:x[1], default=("",0.0))
    top_struct, top_str_r= max(struct_conc.items(), key=lambda x:x[1], default=("",0.0))

    return {
        "bullish_ratio":        round(bull/n,4),
        "bearish_ratio":        round(bear/n,4),
        "neutral_ratio":        round(neut/n,4),
        "symbol_concentration": sym_conc,
        "structure_concentration": struct_conc,
        "top_symbol":           top_sym,
        "top_symbol_ratio":     round(top_sym_r,4),
        "top_structure":        top_struct,
        "top_structure_ratio":  round(top_str_r,4),
    }
