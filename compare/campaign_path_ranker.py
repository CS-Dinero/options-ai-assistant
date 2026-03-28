"""compare/campaign_path_ranker.py — Campaign-aware path ranker for DEEP_ITM_CAMPAIGN family."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal
from campaigns.campaign_transition_engine import TransitionCandidate, normalize_transition_candidate

PathCode = Literal["ROLL_SAME_SIDE","DEFENSIVE_ROLL","FLIP_SELECTIVELY",
                    "COLLAPSE_TO_SPREAD","BANK_AND_REDUCE","DEFER_AND_WAIT"]

@dataclass(slots=True)
class PathRankingContext:
    symbol: str; active_mandate: str; campaign_recovered_pct: float; net_campaign_basis: float
    execution_surface_score: float; timing_score: float; regime_alignment_score: float
    campaign_complexity_score: float; current_profit_percent: float
    risk_envelope: str|None=None; maturity_level: str|None=None

@dataclass(slots=True)
class RankedPath:
    path_code: PathCode; path_total_score: float
    campaign_recovery_score: float; future_roll_score: float
    flip_quality_score: float; collapse_quality_score: float
    campaign_complexity_score: float; execution_quality_score: float
    regime_alignment_score: float; urgency_score: float
    mandate_fit_score: float; simplicity_score: float
    capital_efficiency_score: float; review_pressure_score: float
    projected_credit: float; projected_debit: float; projected_basis_after_action: float
    approved: bool; reason: str; tradeoff_note: str; details: dict[str,Any]

def _c(v): return round(max(0.0,min(100.0,float(v))),6)

SIMPLICITY_MAP = {"ROLL_SAME_SIDE":45.0,"DEFENSIVE_ROLL":40.0,"FLIP_SELECTIVELY":50.0,
                   "COLLAPSE_TO_SPREAD":80.0,"BANK_AND_REDUCE":95.0,"DEFER_AND_WAIT":85.0}

def _simplicity_score(c: TransitionCandidate) -> float:
    base=SIMPLICITY_MAP.get(c.transition_type,50.0)
    if c.transition_type in("ROLL_SAME_SIDE","DEFENSIVE_ROLL","FLIP_SELECTIVELY"):
        base=max(0.0,base-c.campaign_complexity_score*0.15)
    return round(base,6)

def _capital_efficiency_score(c: TransitionCandidate) -> float:
    t=c.transition_type
    if t=="BANK_AND_REDUCE": return 95.0
    if t=="COLLAPSE_TO_SPREAD": return min(100.0,65.0+c.projected_credit*10.0)
    if t=="ROLL_SAME_SIDE": return min(100.0,55.0+c.future_roll_score*0.30)
    if t=="DEFENSIVE_ROLL": return min(100.0,45.0+c.future_roll_score*0.25)
    if t=="FLIP_SELECTIVELY": return min(100.0,50.0+c.flip_quality_score*0.30)
    return 70.0

def _review_pressure_score(c: TransitionCandidate) -> float:
    base={"ROLL_SAME_SIDE":45.0,"DEFENSIVE_ROLL":65.0,"FLIP_SELECTIVELY":60.0,
          "COLLAPSE_TO_SPREAD":35.0,"BANK_AND_REDUCE":20.0,"DEFER_AND_WAIT":30.0}.get(c.transition_type,50.0)
    if not c.approved: base+=15.0
    return _c(base)

MANDATE_FIT: dict = {
    "BASIS_RECOVERY":{"ROLL_SAME_SIDE":90.0,"DEFENSIVE_ROLL":80.0,"FLIP_SELECTIVELY":72.0,
                      "COLLAPSE_TO_SPREAD":58.0,"BANK_AND_REDUCE":45.0,"DEFER_AND_WAIT":40.0},
    "CAPITAL_PRESERVATION":{"BANK_AND_REDUCE":95.0,"COLLAPSE_TO_SPREAD":88.0,"DEFER_AND_WAIT":78.0,
                             "DEFENSIVE_ROLL":72.0,"ROLL_SAME_SIDE":58.0,"FLIP_SELECTIVELY":52.0},
    "EXECUTION_QUALITY":{"DEFER_AND_WAIT":88.0,"BANK_AND_REDUCE":84.0,"COLLAPSE_TO_SPREAD":75.0,
                          "DEFENSIVE_ROLL":70.0,"ROLL_SAME_SIDE":68.0,"FLIP_SELECTIVELY":60.0},
    "QUEUE_HEALTH":{"ROLL_SAME_SIDE":82.0,"DEFENSIVE_ROLL":70.0,"DEFER_AND_WAIT":72.0,
                     "COLLAPSE_TO_SPREAD":68.0,"BANK_AND_REDUCE":62.0,"FLIP_SELECTIVELY":58.0},
}

TRADEOFF_NOTES: dict = {
    "ROLL_SAME_SIDE":"Best for continuing basis recovery, but depends on ongoing roll continuity and execution quality.",
    "DEFENSIVE_ROLL":"Improves survivability under pressure, but can add complexity or debit burden.",
    "FLIP_SELECTIVELY":"May exploit skew and directional shift, but only when same-side continuation is not dominant.",
    "COLLAPSE_TO_SPREAD":"Reduces complexity and frees capital, but gives up some future harvest optionality.",
    "BANK_AND_REDUCE":"Locks in campaign progress fastest, but may sacrifice additional recovery upside.",
    "DEFER_AND_WAIT":"Avoids forcing action in weak conditions, but may reduce capital velocity.",
}

def _mandate_fit_score(c: TransitionCandidate, mandate: str) -> float:
    return round(MANDATE_FIT.get(mandate.upper(),{}).get(c.transition_type,60.0),6)

def _score_candidate(c: TransitionCandidate, ctx: PathRankingContext) -> RankedPath:
    mf=_mandate_fit_score(c,ctx.active_mandate); si=_simplicity_score(c)
    ce=_capital_efficiency_score(c); rp=_review_pressure_score(c)
    af=1.0 if c.approved else 0.80
    total=round((0.22*c.campaign_recovery_score+0.20*c.future_roll_score+0.12*c.execution_quality_score
                 +0.10*c.regime_alignment_score+0.08*c.flip_quality_score+0.08*c.collapse_quality_score
                 +0.08*ce+0.05*si+0.04*mf+0.03*(100.0-rp))*af,6)
    return RankedPath(path_code=c.transition_type,path_total_score=total,
        campaign_recovery_score=round(c.campaign_recovery_score,6),future_roll_score=round(c.future_roll_score,6),
        flip_quality_score=round(c.flip_quality_score,6),collapse_quality_score=round(c.collapse_quality_score,6),
        campaign_complexity_score=round(c.campaign_complexity_score,6),
        execution_quality_score=round(c.execution_quality_score,6),regime_alignment_score=round(c.regime_alignment_score,6),
        urgency_score=round(c.urgency_score,6),mandate_fit_score=round(mf,6),simplicity_score=round(si,6),
        capital_efficiency_score=round(ce,6),review_pressure_score=round(rp,6),
        projected_credit=round(c.projected_credit,6),projected_debit=round(c.projected_debit,6),
        projected_basis_after_action=round(c.projected_basis_after_action,6),
        approved=bool(c.approved),reason=c.reason,tradeoff_note=TRADEOFF_NOTES.get(c.transition_type,""),
        details=c.details)

def rank_campaign_paths(transition_candidates: list[TransitionCandidate],
                         ctx: PathRankingContext) -> list[RankedPath]:
    ranked=[_score_candidate(c,ctx) for c in transition_candidates]
    ranked.sort(key=lambda x:(x.path_total_score,x.approved,x.campaign_recovery_score,
                               x.future_roll_score,x.execution_quality_score,-x.review_pressure_score),
                reverse=True)
    return ranked

def ranked_paths_to_dicts(ranked_paths: list[RankedPath]) -> list[dict[str,Any]]:
    return [{k:round(v,6) if isinstance(v,float) else v for k,v in {
        "path_code":rp.path_code,"path_total_score":rp.path_total_score,
        "campaign_recovery_score":rp.campaign_recovery_score,"future_roll_score":rp.future_roll_score,
        "flip_quality_score":rp.flip_quality_score,"collapse_quality_score":rp.collapse_quality_score,
        "execution_quality_score":rp.execution_quality_score,"mandate_fit_score":rp.mandate_fit_score,
        "simplicity_score":rp.simplicity_score,"capital_efficiency_score":rp.capital_efficiency_score,
        "review_pressure_score":rp.review_pressure_score,"projected_credit":rp.projected_credit,
        "projected_debit":rp.projected_debit,"projected_basis_after_action":rp.projected_basis_after_action,
        "approved":rp.approved,"reason":rp.reason,"tradeoff_note":rp.tradeoff_note,"details":rp.details,
    }.items()} for rp in ranked_paths]

def normalize_and_rank_campaign_paths(raw_candidates: list[TransitionCandidate],
                                       ctx: PathRankingContext) -> list[dict[str,Any]]:
    return ranked_paths_to_dicts(rank_campaign_paths(raw_candidates,ctx))
