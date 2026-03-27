"""causal/evidence_strength_engine.py — Prevents overclaiming; scores evidence trustworthiness."""
from __future__ import annotations
from typing import Any

HELPFUL_DIRECTION: dict = {
    "outcome_score":True,"fill_score":True,"roi_score":True,
    "slippage_dollars":False,"friction_score":False,
}

def score_evidence_strength(treated_n: int, comparison_n: int,
                              effect_rows: list[dict[str,Any]]) -> dict[str,Any]:
    sample_score=min(100.0,treated_n*4.0+comparison_n*2.0)
    mag=0.0; consistency=0.0
    if effect_rows:
        mag=sum(abs(float(r.get("estimated_effect",0))) for r in effect_rows)/len(effect_rows)
        helpful=sum(1 for r in effect_rows
                    if (HELPFUL_DIRECTION.get(r.get("metric_key"),True) and float(r.get("estimated_effect",0))>0)
                    or (not HELPFUL_DIRECTION.get(r.get("metric_key"),True) and float(r.get("estimated_effect",0))<0))
        consistency=100.0*helpful/len(effect_rows)
    strength=round(0.45*min(100,sample_score)+0.25*min(100,mag*10)+0.30*consistency,2)
    label="STRONG" if strength>=75 else "MODERATE" if strength>=55 else "WEAK"
    return {"evidence_strength_score":strength,"evidence_strength_label":label,
            "treated_n":treated_n,"comparison_n":comparison_n}
