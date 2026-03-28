"""lifecycle/net_credit_roll_engine.py — Core harvest/continuation roll engine."""
from __future__ import annotations
from dataclasses import dataclass
from scanner.deep_itm_entry_filters import OptionLegQuote

@dataclass(slots=True)
class RollCandidate:
    symbol: str; option_type: str; current_short_strike: float; current_short_expiry: str
    proposed_short_strike: float; proposed_short_expiry: str; proposed_short_mid: float
    close_cost: float; roll_credit_est: float; future_roll_score: float
    strike_improvement_score: float; expected_move_clearance: float; liquidity_score: float
    approved: bool; reason: str

@dataclass(slots=True)
class RollEngineConfig:
    min_same_side_roll_credit: float=0.25; min_future_roll_score: float=60.0
    harvest_min_pct: float=30.0; early_defense_roll_allowed: bool=True
    min_expected_move_clearance: float=0.70; min_liquidity_score: float=50.0

def estimate_roll_credit(close_cost: float, proposed_short_mid: float) -> float:
    return round(float(proposed_short_mid)-float(close_cost),6)

def estimate_strike_improvement_score(current_short_strike: float, proposed_short_strike: float,
                                       option_type: str) -> float:
    delta=(proposed_short_strike-current_short_strike if option_type.upper()=="CALL"
           else current_short_strike-proposed_short_strike)
    if delta<=0: return 25.0
    return round(min(100.0,25.0+delta*12.0),6)

def estimate_future_roll_continuity(symbol: str, option_type: str, proposed_short_strike: float,
                                     proposed_short_expiry: str,
                                     next_generation_shorts: list[OptionLegQuote]) -> float:
    del symbol, proposed_short_expiry
    scores=[]
    for q in next_generation_shorts:
        if q.option_type.upper()!=option_type.upper(): continue
        score=(0.45*min(100.0,q.mid*50.0)
               +0.35*max(0.0,100.0-min(100.0,abs(q.strike-proposed_short_strike)*5.0))
               +0.20*min(100.0,float(q.open_interest or 0)/5.0))
        scores.append(score)
    if not scores: return 0.0
    scores.sort(reverse=True)
    return round(sum(scores[:5])/len(scores[:5]),6)

def build_roll_candidate(symbol: str, option_type: str, current_short_strike: float,
                          current_short_expiry: str, proposed_short: OptionLegQuote,
                          close_cost: float, expected_move_clearance: float, liquidity_score: float,
                          next_generation_shorts: list[OptionLegQuote]) -> RollCandidate:
    return RollCandidate(
        symbol=symbol, option_type=option_type.upper(),
        current_short_strike=current_short_strike, current_short_expiry=current_short_expiry,
        proposed_short_strike=proposed_short.strike, proposed_short_expiry=proposed_short.expiry,
        proposed_short_mid=round(proposed_short.mid,6), close_cost=round(close_cost,6),
        roll_credit_est=estimate_roll_credit(close_cost,proposed_short.mid),
        future_roll_score=estimate_future_roll_continuity(symbol,option_type,proposed_short.strike,
                                                           proposed_short.expiry,next_generation_shorts),
        strike_improvement_score=estimate_strike_improvement_score(current_short_strike,proposed_short.strike,option_type),
        expected_move_clearance=round(expected_move_clearance,6), liquidity_score=round(liquidity_score,6),
        approved=False, reason="Not yet evaluated.")

def approve_roll_candidate(roll_candidate: RollCandidate, campaign_recovered_pct: float,
                            current_profit_percent: float, cfg: RollEngineConfig,
                            defensive_mode: bool=False) -> RollCandidate:
    reasons=[]; approved=True
    if not defensive_mode:
        if current_profit_percent<cfg.harvest_min_pct:
            approved=False; reasons.append(f"Profit {current_profit_percent:.1f}% below harvest min {cfg.harvest_min_pct:.1f}%.")
    else:
        if not cfg.early_defense_roll_allowed:
            approved=False; reasons.append("Early defense roll not allowed by config.")
    if roll_candidate.roll_credit_est<cfg.min_same_side_roll_credit:
        approved=False; reasons.append(f"Roll credit {roll_candidate.roll_credit_est:.2f} below min {cfg.min_same_side_roll_credit:.2f}.")
    if roll_candidate.future_roll_score<cfg.min_future_roll_score:
        approved=False; reasons.append(f"Future roll score {roll_candidate.future_roll_score:.1f} below min {cfg.min_future_roll_score:.1f}.")
    if roll_candidate.expected_move_clearance<cfg.min_expected_move_clearance:
        approved=False; reasons.append(f"EM clearance {roll_candidate.expected_move_clearance:.2f} below min {cfg.min_expected_move_clearance:.2f}.")
    if roll_candidate.liquidity_score<cfg.min_liquidity_score:
        approved=False; reasons.append(f"Liquidity score {roll_candidate.liquidity_score:.1f} below min {cfg.min_liquidity_score:.1f}.")
    if not defensive_mode and campaign_recovered_pct>=90.0:
        approved=False; reasons.append("Campaign already largely recovered; roll continuation not preferred.")
    reason="Approved same-side roll candidate." if not reasons else " | ".join(reasons)
    from dataclasses import replace
    return replace(roll_candidate,approved=approved,reason=reason)

def evaluate_same_side_rolls(symbol: str, option_type: str, current_short_strike: float,
                              current_short_expiry: str, close_cost: float, current_profit_percent: float,
                              campaign_recovered_pct: float, proposed_shorts: list[OptionLegQuote],
                              next_generation_shorts: list[OptionLegQuote],
                              expected_move_clearance_by_strike: dict[float,float],
                              liquidity_score_by_strike: dict[float,float],
                              cfg: RollEngineConfig|None=None,
                              defensive_mode: bool=False) -> list[RollCandidate]:
    cfg=cfg or RollEngineConfig(); results=[]
    for ps in proposed_shorts:
        if ps.option_type.upper()!=option_type.upper(): continue
        rc=build_roll_candidate(symbol,option_type,current_short_strike,current_short_expiry,ps,
                                 close_cost,float(expected_move_clearance_by_strike.get(ps.strike,0.0)),
                                 float(liquidity_score_by_strike.get(ps.strike,0.0)),next_generation_shorts)
        rc=approve_roll_candidate(rc,campaign_recovered_pct,current_profit_percent,cfg,defensive_mode)
        results.append(rc)
    results.sort(key=lambda x:(1.0 if x.approved else 0.0,x.roll_credit_est,
                                x.future_roll_score,x.strike_improvement_score),reverse=True)
    return results
