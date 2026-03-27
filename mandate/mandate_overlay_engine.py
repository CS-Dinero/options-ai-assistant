"""mandate/mandate_overlay_engine.py — Applies mandate-specific capital overlays."""
from __future__ import annotations
from typing import Any
from mandate.mandate_policy import get_mandate_policy

def _sf(v, d=1.0):
    try: return float(v) if v not in (None,"") else d
    except: return d

def apply_mandate_overlays(row: dict[str,Any], active_mandate: str) -> dict[str,Any]:
    cap = get_mandate_policy(active_mandate).get("capital_bias",{})
    sm  = _sf(cap.get("size_multiplier",1.0)); pb_sm = _sf(row.get("playbook_size_multiplier",1.0))
    pb_bonus = _sf(cap.get("promoted_bonus",1.0)) if row.get("playbook_status")=="PROMOTED" else 1.0
    out = dict(row)
    out["mandate_size_multiplier"]   = round(sm,2)
    out["mandate_promoted_bonus"]    = round(pb_bonus,2)
    out["effective_size_multiplier"] = round(pb_sm*sm*pb_bonus,2)
    out["active_mandate"]            = active_mandate
    return out
