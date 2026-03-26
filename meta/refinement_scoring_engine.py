"""meta/refinement_scoring_engine.py — Scores refinements by evidence, safety, urgency."""
from __future__ import annotations
from typing import Any

def score_refinement_candidate(candidate: dict[str,Any]) -> dict[str,Any]:
    sig=candidate.get("signal_type"); ev=candidate.get("evidence",{}) or {}
    es=50.0; sf=70.0; sc=60.0; urg=50.0
    if sig in ("PLAYBOOK_DEGRADATION_SIGNAL","PLAYBOOK_PROMOTION_SIGNAL"):
        es=min(100,30+float(ev.get("count",0))*4); urg=min(100,abs(float(ev.get("avg_outcome_score",70))-70)*3)
    elif sig=="SYMBOL_EXECUTION_FRICTION_SIGNAL": es=75; urg=80; sf=80
    elif sig=="SURFACE_THRESHOLD_SIGNAL":
        fp=float(ev.get("surface_fail_pct",0)); es=min(100,fp*100); urg=min(100,fp*100); sf=55
    elif sig=="OVERRIDE_CONSENSUS_SIGNAL":
        n=float((ev.get("primary_reason_counts") or {}).get("SLIPPAGE_RISK_TOO_HIGH",0))
        es=min(100,40+n*10); urg=min(100,40+n*10); sf=75
    elif sig=="CAPITAL_CHOKE_SIGNAL":
        r=float(ev.get("capital_block_rate",0)); es=min(100,r*100); urg=min(100,r*120); sf=60
    score=round(0.35*es+0.25*sf+0.15*sc+0.25*urg,2)
    return {**candidate,"refinement_score":score,"evidence_strength":round(es,2),
            "safety_score":round(sf,2),"urgency_score":round(urg,2)}
