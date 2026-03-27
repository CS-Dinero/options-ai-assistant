"""stress/stress_variable_engine.py — Applies deterministic shocks to rows/metrics."""
from __future__ import annotations
from typing import Any
from copy import deepcopy

def _sf(v, d=0.0):
    try: return float(v) if v not in (None,"") else d
    except: return d

def apply_fill_quality_shock(rows: list[dict[str,Any]], points: float=15.0) -> list[dict[str,Any]]:
    shocked=deepcopy(rows)
    for r in shocked: r["transition_latest_fill_score"]=max(0.0,_sf(r.get("transition_latest_fill_score",75))-points)
    return shocked

def apply_surface_compression_shock(rows: list[dict[str,Any]], points: float=8.0, floor_ok: float=65.0) -> list[dict[str,Any]]:
    shocked=deepcopy(rows)
    for r in shocked:
        ns=max(0.0,_sf(r.get("transition_execution_surface_score",70))-points)
        r["transition_execution_surface_score"]=ns; r["transition_execution_surface_ok"]=ns>=floor_ok
    return shocked

def apply_timing_friction_shock(rows: list[dict[str,Any]], points: float=10.0, floor_ok: float=60.0) -> list[dict[str,Any]]:
    shocked=deepcopy(rows)
    for r in shocked:
        ns=max(0.0,_sf(r.get("transition_timing_score",70))-points)
        r["transition_timing_score"]=ns; r["transition_timing_ok"]=ns>=floor_ok
    return shocked

def apply_symbol_concentration_shock(exposure_metrics: dict[str,Any], symbol: str, new_ratio: float) -> dict[str,Any]:
    shocked=deepcopy(exposure_metrics)
    shocked["top_symbol"]=symbol; shocked["top_symbol_ratio"]=new_ratio
    conc=dict(shocked.get("symbol_concentration",{})); conc[symbol]=new_ratio
    shocked["symbol_concentration"]=conc; return shocked

def apply_capital_choke_shock(rows: list[dict[str,Any]]) -> list[dict[str,Any]]:
    shocked=deepcopy(rows)
    for r in shocked:
        r["capital_commitment_ok"]=False
        r["capital_commitment_decision"]="BLOCK_EXPANSION"
    return shocked
