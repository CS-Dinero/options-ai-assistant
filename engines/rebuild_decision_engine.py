"""
engines/rebuild_decision_engine.py
Anti-churn comparator: only approve long replacement when it is MATERIALLY better.

Default bias: KEEP the current long.
Replacement wins only when it clears REPLACE_LONG_MIN_ADVANTAGE score threshold
AND improves either credit by MIN_CREDIT_IMPROVEMENT or efficiency by MIN_EFF_IMPROVEMENT.
"""
from __future__ import annotations
from typing import Any

REPLACE_LONG_MIN_ADVANTAGE    = 5.0   # search_rank points
MIN_CREDIT_IMPROVEMENT        = 0.20  # per-share credit improvement
MIN_EFF_IMPROVEMENT           = 8.0   # long efficiency score improvement

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def _safe_mid(c):
    m=_sf(c.get("mid")); return m if m>0 else round((_sf(c.get("bid"))+_sf(c.get("ask")))/2,4)

def _intrinsic(opt,spot,k):
    return max(0.0,spot-k) if opt=="call" else max(0.0,k-spot)

def _extrinsic_burden(c,spot):
    mid=_safe_mid(c); opt=str(c.get("option_type","")).lower(); k=_sf(c.get("strike"))
    return max(0.0, mid-_intrinsic(opt,spot,k))

def _long_efficiency(c,spot):
    mid=_safe_mid(c)
    if mid<=0: return 0.0
    ext=_extrinsic_burden(c,spot)
    da=abs(_sf(c.get("delta"))); dte=int(_sf(c.get("dte")))
    s=100-(ext/mid)*100
    if 0.65<=da<=0.90: s+=10
    elif 0.50<=da<=0.95: s+=5
    if 35<=dte<=90: s+=10
    elif 28<=dte<=120: s+=5
    return round(max(0,min(100,s)),2)

def compare_keep_vs_replace(
    keep_candidate:    dict[str, Any],
    replace_candidate: dict[str, Any],
    market_context:    dict[str, Any],
) -> dict[str, Any]:
    """
    Compare two candidates (same short leg, different long legs).
    Returns chosen candidate with rebuild_class and decision_notes.
    """
    spot = _sf(market_context.get("spot") or market_context.get("spot_price"))

    keep_long    = keep_candidate.get("long_leg",{}) or {}
    replace_long = replace_candidate.get("long_leg",{}) or {}

    keep_eff    = _long_efficiency(keep_long, spot)
    replace_eff = _long_efficiency(replace_long, spot)
    keep_credit = _sf(keep_candidate.get("transition_net_credit"))
    repl_credit = _sf(replace_candidate.get("transition_net_credit"))
    keep_score  = _sf(keep_candidate.get("search_rank_score"))
    repl_score  = _sf(replace_candidate.get("search_rank_score"))

    eff_adv    = replace_eff - keep_eff
    credit_adv = repl_credit - keep_credit
    score_adv  = repl_score  - keep_score

    replace_ok = (
        score_adv  >= REPLACE_LONG_MIN_ADVANTAGE and
        (credit_adv >= MIN_CREDIT_IMPROVEMENT or eff_adv >= MIN_EFF_IMPROVEMENT)
    )

    chosen      = replace_candidate if replace_ok else keep_candidate
    chosen_class= "REPLACE_LONG"    if replace_ok else "KEEP_LONG"

    notes = []
    if replace_ok:
        notes.append(f"replacement long materially better (score+{score_adv:.1f}, credit+{credit_adv:.2f})")
    else:
        notes.append(f"keeping original long (advantage {score_adv:.1f} below {REPLACE_LONG_MIN_ADVANTAGE} threshold)")
    if eff_adv > 0:
        notes.append(f"replacement long efficiency +{eff_adv:.1f}")

    return {
        "chosen_candidate":       chosen,
        "chosen_rebuild_class":   chosen_class,
        "keep_candidate_score":   keep_score,
        "replace_candidate_score":repl_score,
        "keep_long_efficiency":   keep_eff,
        "replace_long_efficiency":replace_eff,
        "decision_notes":         notes,
    }
