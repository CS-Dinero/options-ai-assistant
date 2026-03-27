"""campaigns/campaign_state_engine.py — Campaign-native lifecycle state classification."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

CampaignState = Literal[
    "HARVEST_READY","ROLL_READY","DEFENSIVE_ROLL","FLIP_REVIEW",
    "COLLAPSE_CANDIDATE","BANK_REDUCE","DEFER","BROKEN",
]
CampaignAction = Literal[
    "HARVEST","ROLL","DEFEND","FLIP","COLLAPSE","BANK_REDUCE","HOLD","CLOSE",
]

@dataclass(slots=True)
class CampaignStateInput:
    symbol: str; current_structure: str; current_side: str
    short_dte: int; long_dte: int; distance_to_strike: float; expected_move: float
    current_profit_percent: float; execution_surface_score: float; timing_score: float
    regime_alignment_score: float; future_roll_score: float; flip_quality_score: float
    collapse_quality_score: float; campaign_complexity_score: float
    net_campaign_basis: float; campaign_recovered_pct: float
    roll_credit_est: float=0.0; defensive_repair_score: float=0.0

@dataclass(slots=True)
class CampaignStateDecision:
    campaign_state: CampaignState; campaign_action: CampaignAction
    campaign_urgency: int; campaign_reason: str; state_score: float

def score_campaign_state(si: CampaignStateInput) -> float:
    em_ratio=abs(si.distance_to_strike)/max(0.01,si.expected_move)
    strike_pressure=max(0.0,100.0-min(100.0,em_ratio*100.0))
    basis_pressure=min(100.0,max(0.0,100.0-si.campaign_recovered_pct))
    dte_p=90.0 if si.short_dte<=3 else 65.0 if si.short_dte<=5 else 40.0 if si.short_dte<=7 else 0.0
    exec_weak=max(0.0,100.0-((si.execution_surface_score+si.timing_score)/2.0))
    return round(0.22*strike_pressure+0.18*dte_p+0.15*basis_pressure
                 +0.18*min(100,si.future_roll_score)+0.10*min(100,si.collapse_quality_score)
                 +0.07*min(100,si.flip_quality_score)+0.10*exec_weak, 4)

REASONS: dict = {
    "BROKEN":           "Campaign is broken: recovery weak, short-leg risk elevated, repair quality insufficient.",
    "BANK_REDUCE":      "Basis largely recovered; remaining optionality does not justify full complexity.",
    "COLLAPSE_CANDIDATE":"Basis recovery advanced; spread simplification offers better capital efficiency.",
    "FLIP_REVIEW":      "Opposite-side transition merits review; same-side continuation is not clearly dominant.",
    "DEFENSIVE_ROLL":   "Strike/DTE pressure rising; defensive repair preferred to passive hold.",
    "ROLL_READY":       "Harvest threshold and continuation quality support a same-side net-credit roll.",
    "HARVEST_READY":    "Profit threshold met; value should be harvested though superior roll path unclear.",
    "DEFER":            "No immediate campaign transition dominates; defer and re-evaluate.",
}

def classify_campaign_state(si: CampaignStateInput, harvest_min_pct: float=30.0,
                              harvest_target_pct: float=40.0,
                              high_risk_dte: int=3) -> CampaignStateDecision:
    score=score_campaign_state(si)
    em_ratio=abs(si.distance_to_strike)/max(0.01,si.expected_move)
    strike_danger=em_ratio<0.30; strike_threat=em_ratio<0.50
    weak_exec=si.execution_surface_score<60.0 or si.timing_score<60.0
    strong_roll=si.roll_credit_est>0.0 and si.future_roll_score>=65.0
    strong_flip=si.flip_quality_score>=70.0; strong_collapse=si.collapse_quality_score>=70.0

    def _dec(s,a,u): return CampaignStateDecision(s,a,u,REASONS[s],score)

    if ((si.current_profit_percent<=-50.0 and si.future_roll_score<45.0 and si.defensive_repair_score<45.0)
        or (si.short_dte<=high_risk_dte and strike_danger and si.future_roll_score<50.0)):
        return _dec("BROKEN","CLOSE",100)
    if si.campaign_recovered_pct>=85.0 and si.net_campaign_basis<=0.50:
        return _dec("BANK_REDUCE","BANK_REDUCE",35)
    if si.campaign_recovered_pct>=60.0 and strong_collapse and si.campaign_complexity_score>=60.0:
        return _dec("COLLAPSE_CANDIDATE","COLLAPSE",45)
    if (si.short_dte<=high_risk_dte and strike_danger) or (strike_threat and si.defensive_repair_score>=55.0):
        return _dec("DEFENSIVE_ROLL","DEFEND",90)
    if si.current_profit_percent>=harvest_target_pct and strong_roll and not weak_exec:
        return _dec("ROLL_READY","ROLL",75)
    if si.current_profit_percent>=harvest_min_pct:
        return _dec("HARVEST_READY","HARVEST",65)
    if strong_flip and si.regime_alignment_score>=60.0:
        return _dec("FLIP_REVIEW","FLIP",55)
    return _dec("DEFER","HOLD",20)
