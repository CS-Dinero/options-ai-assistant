"""lifecycle/net_credit_roll_engine.py — Core harvest/continuation roll engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from scanner.deep_itm_entry_filters import OptionLegQuote
from scanner.deep_itm_calendar_scanner import estimate_future_roll_score, estimate_liquidity_score

@dataclass(slots=True)
class RollEngineConfig:
    min_same_side_roll_credit: float=0.25; min_future_roll_score: float=60.0
    harvest_min_pct: float=30.0; harvest_target_pct: float=40.0
    early_defense_roll_allowed: bool=True; min_expected_move_clearance: float=0.70

@dataclass(slots=True)
class RollCandidate:
    symbol: str; option_type: str; current_short_strike: float; current_short_expiry: str
    proposed_short_strike: float; proposed_short_expiry: str; proposed_short_mid: float
    close_cost: float; roll_credit_est: float; future_roll_score: float
    strike_improvement_score: float; expected_move_clearance: float; liquidity_score: float
    approved: bool; reason: str

def estimate_roll_credit(close_cost: float, proposed_short_mid: float) -> float:
    return round(proposed_short_mid-close_cost,4)

def estimate_strike_improvement_score(current_strike: float, proposed_strike: float,
                                       option_type: str) -> float:
    if option_type.upper()=="CALL":
        delta=proposed_strike-current_strike
    else:
        delta=current_strike-proposed_strike
    if delta>5:   return 90.0
    if delta>2:   return 75.0
    if delta>0:   return 60.0
    if delta==0:  return 50.0
    return max(0.0, 50.0+delta*5)

def build_roll_candidate(symbol: str, option_type: str, current_short_strike: float,
                          current_short_expiry: str, proposed_short: OptionLegQuote,
                          close_cost: float, expected_move_clearance: float,
                          next_gen_shorts: list[OptionLegQuote]) -> RollCandidate:
    liquidity=estimate_liquidity_score(proposed_short,proposed_short)
    fut_roll=estimate_future_roll_score(next_gen_shorts)
    roll_credit=estimate_roll_credit(close_cost,proposed_short.mid)
    strike_imp=estimate_strike_improvement_score(current_short_strike,proposed_short.strike,option_type)
    return RollCandidate(symbol=symbol,option_type=option_type,
        current_short_strike=current_short_strike,current_short_expiry=current_short_expiry,
        proposed_short_strike=proposed_short.strike,proposed_short_expiry=proposed_short.expiry,
        proposed_short_mid=proposed_short.mid,close_cost=close_cost,roll_credit_est=roll_credit,
        future_roll_score=fut_roll,strike_improvement_score=strike_imp,
        expected_move_clearance=expected_move_clearance,liquidity_score=liquidity,
        approved=False,reason="")

def approve_roll_candidate(rc: RollCandidate, campaign_recovered_pct: float,
                            current_profit_percent: float, cfg: RollEngineConfig,
                            defensive_mode: bool=False) -> RollCandidate:
    reasons=[]
    harvest_ok=defensive_mode or current_profit_percent>=cfg.harvest_min_pct
    if not harvest_ok: reasons.append(f"Profit {current_profit_percent:.1f}% below harvest min {cfg.harvest_min_pct}%")
    if rc.roll_credit_est<cfg.min_same_side_roll_credit:
        reasons.append(f"Roll credit {rc.roll_credit_est:.3f} below min {cfg.min_same_side_roll_credit}")
    if rc.future_roll_score<cfg.min_future_roll_score:
        reasons.append(f"Future roll score {rc.future_roll_score:.1f} below min {cfg.min_future_roll_score}")
    if rc.expected_move_clearance<cfg.min_expected_move_clearance:
        reasons.append(f"EM clearance {rc.expected_move_clearance:.2f} below min {cfg.min_expected_move_clearance}")
    approved=len(reasons)==0
    reason=("Approved: roll credit positive, continuity strong, clearance acceptable." if approved
            else "Rejected: "+"; ".join(reasons))
    from dataclasses import replace
    return replace(rc,approved=approved,reason=reason)

def evaluate_same_side_rolls(symbol: str, option_type: str, current_short_strike: float,
                              current_short_expiry: str, close_cost: float,
                              current_profit_percent: float, campaign_recovered_pct: float,
                              proposed_shorts: list[OptionLegQuote],
                              next_gen_shorts: list[OptionLegQuote],
                              em_clearance_map: dict[float,float],
                              cfg: RollEngineConfig|None=None,
                              defensive_mode: bool=False) -> list[RollCandidate]:
    cfg=cfg or RollEngineConfig(); candidates=[]
    for ps in proposed_shorts:
        em_clear=em_clearance_map.get(ps.strike,0.0)
        rc=build_roll_candidate(symbol,option_type,current_short_strike,current_short_expiry,
                                 ps,close_cost,em_clear,next_gen_shorts)
        rc=approve_roll_candidate(rc,campaign_recovered_pct,current_profit_percent,cfg,defensive_mode)
        candidates.append(rc)
    return sorted(candidates,key=lambda x: (x.approved,x.roll_credit_est+x.future_roll_score*0.3),reverse=True)
