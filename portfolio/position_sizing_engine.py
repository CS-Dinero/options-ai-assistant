"""portfolio/position_sizing_engine.py — Converts policy + quality signals into final contract add."""
from __future__ import annotations
from typing import Any
import math

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def compute_position_size_adjustment(
    candidate_row: dict[str,Any],
    playbook_policy: dict[str,Any],
) -> dict[str,Any]:
    base   = _sf(candidate_row.get("recommended_contract_add",1.0)) or 1.0
    sm     = _sf(playbook_policy.get("size_multiplier",1.0))
    qs     = _sf(candidate_row.get("transition_queue_score"))
    alloc  = _sf(candidate_row.get("transition_allocator_score"))
    ts     = _sf(candidate_row.get("transition_timing_score"))
    surf   = _sf(candidate_row.get("transition_execution_surface_score"))
    fill   = _sf(candidate_row.get("transition_latest_fill_score",75))

    qm=1.0
    if qs>=80 and alloc>=75 and ts>=70 and surf>=70: qm+=0.10
    if fill<60: qm-=0.15
    raw = base*sm*qm
    final = math.floor(raw) if raw>=0 else math.ceil(raw)
    return {"base_contract_add":base,"size_multiplier":round(sm,2),
            "quality_multiplier":round(qm,2),"final_contract_add":max(0,int(final)),
            "notes":[f"base={base:.0f} × playbook={sm:.2f} × quality={qm:.2f} = {raw:.2f} → {final}"]}
