"""playbooks/playbook_rules.py — Deterministic playbook code assignment."""
from __future__ import annotations
from typing import Any

def match_playbook_code(row: dict[str,Any]) -> str:
    action   = str(row.get("transition_action",""))
    surf_ok  = bool(row.get("transition_execution_surface_ok",True))
    time_ok  = bool(row.get("transition_timing_ok",True))
    port_ok  = bool(row.get("transition_portfolio_fit_ok",True))
    basis    = float(row.get("campaign_net_basis",9999))
    struct   = str(row.get("strategy_type","") or row.get("structure_type","")).lower()

    if not port_ok:  return "PB008"
    if not surf_ok:  return "PB006"
    if not time_ok:  return "PB007"
    if basis<=0.5 and ("diagonal" in struct or "calendar" in struct): return "PB009"
    if action=="FLIP_TO_CALL_DIAGONAL" and "put" in struct: return "PB002"
    if action=="FLIP_TO_PUT_DIAGONAL"  and "call" in struct: return "PB003"
    if action in ("FLIP_TO_CALL_DIAGONAL","FLIP_TO_PUT_DIAGONAL"): return "PB001"
    if action=="CONVERT_TO_BULL_PUT_SPREAD":  return "PB004"
    if action=="CONVERT_TO_BEAR_CALL_SPREAD": return "PB005"
    return "PB001"
