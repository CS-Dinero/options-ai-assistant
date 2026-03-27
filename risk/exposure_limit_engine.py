"""risk/exposure_limit_engine.py — Applies symbol/playbook/mandate concentration limits."""
from __future__ import annotations
from typing import Any

def evaluate_exposure_limits(symbol: str, exposure_metrics: dict[str,Any],
                              risk_envelope: dict[str,Any]) -> dict[str,Any]:
    sc=float((exposure_metrics.get("symbol_concentration") or {}).get(symbol,
              exposure_metrics.get("top_symbol_ratio",0.0) if exposure_metrics.get("top_symbol")==symbol else 0.0))
    max_sym=float(risk_envelope.get("max_symbol_exposure",0.30))
    within=sc<=max_sym
    return {"symbol_concentration":round(sc,4),"max_symbol_exposure":round(max_sym,4),"exposure_within_limit":within}
