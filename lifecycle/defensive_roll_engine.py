"""lifecycle/defensive_roll_engine.py — Defensive repair logic, separate from harvest continuation."""
from __future__ import annotations
from dataclasses import dataclass
from scanner.deep_itm_entry_filters import OptionLegQuote

@dataclass(slots=True)
class DefensiveRepairCandidate:
    symbol: str; option_type: str; repair_type: str
    current_short_strike: float; current_short_expiry: str
    proposed_short_strike: float|None; proposed_short_expiry: str|None
    close_cost: float; new_credit: float; repair_cost_est: float
    strike_relief_score: float; time_extension_score: float
    survivability_score: float; recovery_score: float
    liquidity_score: float; expected_move_clearance: float
    approved: bool; reason: str

@dataclass(slots=True)
class DefensiveRollConfig:
    max_defensive_repair_debit: float=0.40; min_survivability_score: float=55.0
    min_recovery_score: float=50.0; min_liquidity_score: float=45.0
    min_expected_move_clearance: float=0.50; high_risk_dte: int=3; threatened_em_ratio: float=0.50

def estimate_repair_cost(close_cost: float, new_credit: float) -> float:
    return round(float(close_cost)-float(new_credit),6)

def estimate_strike_relief_score(current_short_strike: float, proposed_short_strike: float|None,
                                  option_type: str) -> float:
    if proposed_short_strike is None: return 0.0
    relief=(proposed_short_strike-current_short_strike if option_type.upper()=="CALL"
            else current_short_strike-proposed_short_strike)
    if relief<=0: return 20.0
    return round(min(100.0,25.0+relief*12.0),6)

def estimate_time_extension_score(current_short_expiry: str, proposed_short_expiry: str|None) -> float:
    if proposed_short_expiry is None: return 0.0
    if proposed_short_expiry==current_short_expiry: return 20.0
    return 85.0

def score_repair_survivability(strike_relief_score: float, time_extension_score: float,
                                expected_move_clearance: float, liquidity_score: float) -> float:
    em_score=min(100.0,max(0.0,expected_move_clearance)*100.0)
    return round(0.35*strike_relief_score+0.30*time_extension_score+0.20*em_score+0.15*liquidity_score,6)

def score_repair_recovery(repair_cost_est: float, future_roll_score: float,
                           campaign_recovered_pct: float) -> float:
    debit_penalty=max(0.0,100.0-repair_cost_est*100.0) if repair_cost_est>0 else 100.0
    return round(0.45*debit_penalty+0.40*future_roll_score+0.15*min(100.0,max(0.0,campaign_recovered_pct)),6)

def build_defensive_roll_candidate(symbol: str, option_type: str, repair_type: str,
                                    current_short_strike: float, current_short_expiry: str,
                                    proposed_short: OptionLegQuote|None, close_cost: float, new_credit: float,
                                    expected_move_clearance: float, liquidity_score: float,
                                    future_roll_score: float, campaign_recovered_pct: float) -> DefensiveRepairCandidate:
    pss=proposed_short.strike if proposed_short else None
    pse=proposed_short.expiry if proposed_short else None
    repair_cost=estimate_repair_cost(close_cost,new_credit)
    srs=estimate_strike_relief_score(current_short_strike,pss,option_type)
    tes=estimate_time_extension_score(current_short_expiry,pse)
    surv=score_repair_survivability(srs,tes,expected_move_clearance,liquidity_score)
    rec=score_repair_recovery(repair_cost,future_roll_score,campaign_recovered_pct)
    return DefensiveRepairCandidate(
        symbol=symbol, option_type=option_type.upper(), repair_type=repair_type,
        current_short_strike=current_short_strike, current_short_expiry=current_short_expiry,
        proposed_short_strike=pss, proposed_short_expiry=pse, close_cost=round(close_cost,6),
        new_credit=round(new_credit,6), repair_cost_est=round(repair_cost,6),
        strike_relief_score=srs, time_extension_score=tes, survivability_score=surv, recovery_score=rec,
        liquidity_score=round(liquidity_score,6), expected_move_clearance=round(expected_move_clearance,6),
        approved=False, reason="Not yet evaluated.")

def approve_defensive_roll_candidate(candidate: DefensiveRepairCandidate,
                                      cfg: DefensiveRollConfig) -> DefensiveRepairCandidate:
    reasons=[]; approved=True
    if candidate.repair_cost_est>cfg.max_defensive_repair_debit:
        approved=False; reasons.append(f"Repair debit {candidate.repair_cost_est:.2f} exceeds max {cfg.max_defensive_repair_debit:.2f}.")
    if candidate.survivability_score<cfg.min_survivability_score:
        approved=False; reasons.append(f"Survivability {candidate.survivability_score:.1f} below min {cfg.min_survivability_score:.1f}.")
    if candidate.recovery_score<cfg.min_recovery_score:
        approved=False; reasons.append(f"Recovery {candidate.recovery_score:.1f} below min {cfg.min_recovery_score:.1f}.")
    if candidate.liquidity_score<cfg.min_liquidity_score:
        approved=False; reasons.append(f"Liquidity {candidate.liquidity_score:.1f} below min {cfg.min_liquidity_score:.1f}.")
    if candidate.expected_move_clearance<cfg.min_expected_move_clearance:
        approved=False; reasons.append(f"EM clearance {candidate.expected_move_clearance:.2f} below min {cfg.min_expected_move_clearance:.2f}.")
    reason="Approved defensive repair candidate." if not reasons else " | ".join(reasons)
    from dataclasses import replace
    return replace(candidate,approved=approved,reason=reason)

def evaluate_defensive_rolls(symbol: str, option_type: str, current_short_strike: float,
                              current_short_expiry: str, close_cost: float, campaign_recovered_pct: float,
                              proposed_shorts: list[OptionLegQuote],
                              future_roll_score_by_strike: dict[float,float],
                              expected_move_clearance_by_strike: dict[float,float],
                              liquidity_score_by_strike: dict[float,float],
                              cfg: DefensiveRollConfig|None=None) -> list[DefensiveRepairCandidate]:
    cfg=cfg or DefensiveRollConfig(); results=[]
    for ps in proposed_shorts:
        if ps.option_type.upper()!=option_type.upper(): continue
        cand=build_defensive_roll_candidate(symbol,option_type,"ROLL_OUT_TIME",current_short_strike,
             current_short_expiry,ps,close_cost,float(ps.mid),
             float(expected_move_clearance_by_strike.get(ps.strike,0.0)),
             float(liquidity_score_by_strike.get(ps.strike,0.0)),
             float(future_roll_score_by_strike.get(ps.strike,0.0)),campaign_recovered_pct)
        cand=approve_defensive_roll_candidate(cand,cfg)
        results.append(cand)
    results.sort(key=lambda x:(1.0 if x.approved else 0.0,x.survivability_score,
                                x.recovery_score,-max(0.0,x.repair_cost_est)),reverse=True)
    return results
