"""scanner/deep_itm_calendar_scanner.py — Deep ITM calendar entry candidate discovery."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from scanner.deep_itm_entry_filters import (
    DeepITMEntryFilterConfig, DeepITMEntryFilterResult, OptionLegQuote,
    compute_liquidity_score, evaluate_deep_itm_entry_filters,
)

@dataclass(slots=True)
class MarketContextLite:
    symbol: str; spot_price: float; expected_move: float; iv_percentile: float
    gamma_regime: str; environment: str; regime_alignment_score: float
    as_of_date: str = ""  # YYYY-MM-DD; used for DTE calculation

@dataclass(slots=True)
class DeepITMCalendarCandidate:
    symbol: str; campaign_family: str; entry_family: str; structure: str
    option_type: str; long_leg: dict; short_leg: dict
    short_dte: int; long_dte: int; strike_width: float; entry_net_debit: float
    entry_debit_width_ratio: float; long_intrinsic_value: float; long_extrinsic_cost: float
    projected_recovery_ratio: float; future_roll_score: float; entry_cheapness_score: float
    expected_move_clearance: float; liquidity_score: float; regime_alignment_score: float
    candidate_score: float; notes: list[str]=field(default_factory=list)

def estimate_calendar_entry_net_debit(long_leg_mid: float, short_leg_mid: float) -> float:
    return round(float(long_leg_mid)-float(short_leg_mid),6)

def estimate_expected_move_clearance(spot_price: float, short_strike: float, expected_move: float) -> float:
    if expected_move<=0: return 0.0
    return round(abs(float(short_strike)-float(spot_price))/float(expected_move),6)

def estimate_liquidity_score(long_leg: OptionLegQuote, short_leg: OptionLegQuote,
                              cfg: DeepITMEntryFilterConfig) -> float:
    return compute_liquidity_score(long_leg=long_leg,short_leg=short_leg,cfg=cfg)

def estimate_future_roll_score(symbol: str, option_type: str, current_short_strike: float,
                                current_short_expiry: str,
                                candidate_next_shorts: list[OptionLegQuote]) -> float:
    del symbol, current_short_expiry
    scores=[]
    for q in candidate_next_shorts:
        if q.option_type.upper()!=option_type.upper(): continue
        same_side_distance=abs(q.strike-current_short_strike)
        score=(0.45*min(100.0,q.mid*50.0)
               +0.35*max(0.0,100.0-min(100.0,same_side_distance*5.0))
               +0.20*min(100.0,float(q.open_interest or 0)/5.0))
        scores.append(score)
    if not scores: return 0.0
    scores.sort(reverse=True)
    return round(sum(scores[:5])/len(scores[:5]),6)

def extract_dte(expiry: str, as_of_date: str="") -> int:
    """Convert expiry string YYYY-MM-DD to DTE. Uses as_of_date or today."""
    try:
        exp=datetime.strptime(expiry,"%Y-%m-%d").date()
        ref=datetime.strptime(as_of_date,"%Y-%m-%d").date() if as_of_date else date.today()
        return max(0,(exp-ref).days)
    except Exception:
        # Fallback: if expiry is already an int or something else, return a sentinel
        return int(expiry) if str(expiry).isdigit() else 0

def _estimate_projected_future_roll_credits(current_short_strike: float, option_type: str,
                                             candidate_next_shorts: list[OptionLegQuote]) -> float:
    cands=[q.mid for q in candidate_next_shorts
           if q.option_type.upper()==option_type.upper()
           and abs(q.strike-current_short_strike)<=max(5.0,0.10*abs(current_short_strike))]
    if not cands: return 0.0
    cands.sort(reverse=True)
    return round(sum(cands[:2]),6)

def _candidate_score(filter_result: DeepITMEntryFilterResult, expected_move_clearance: float) -> float:
    em_score=min(100.0,expected_move_clearance*100.0)
    return round(0.45*filter_result.entry_cheapness_score+0.25*filter_result.future_roll_score
                 +0.15*filter_result.liquidity_score+0.15*em_score,6)

def build_deep_itm_calendar_candidate(context: MarketContextLite, option_type: str,
                                       long_leg: OptionLegQuote, short_leg: OptionLegQuote,
                                       long_dte: int, short_dte: int,
                                       projected_future_roll_credits: float, future_roll_score: float,
                                       cfg: DeepITMEntryFilterConfig) -> DeepITMCalendarCandidate|None:
    strike_width=abs(short_leg.strike-long_leg.strike)
    net_debit=estimate_calendar_entry_net_debit(long_leg.mid,short_leg.mid)
    liquidity_score=estimate_liquidity_score(long_leg,short_leg,cfg)
    em_clearance=estimate_expected_move_clearance(context.spot_price,short_leg.strike,context.expected_move)
    result=evaluate_deep_itm_entry_filters(context.spot_price,option_type,long_leg,short_leg,
                                            long_dte,short_dte,strike_width,net_debit,
                                            projected_future_roll_credits,future_roll_score,
                                            liquidity_score,context.regime_alignment_score,cfg)
    if not result.passed: return None
    return DeepITMCalendarCandidate(
        symbol=context.symbol,campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",structure="DEEP_ITM_CALENDAR",
        option_type=option_type.upper(),
        long_leg={"symbol":long_leg.symbol,"option_type":long_leg.option_type,"expiry":long_leg.expiry,
                  "strike":long_leg.strike,"mid":long_leg.mid,"delta":long_leg.delta},
        short_leg={"symbol":short_leg.symbol,"option_type":short_leg.option_type,"expiry":short_leg.expiry,
                   "strike":short_leg.strike,"mid":short_leg.mid,"delta":short_leg.delta},
        short_dte=short_dte,long_dte=long_dte,strike_width=round(strike_width,6),
        entry_net_debit=round(net_debit,6),entry_debit_width_ratio=result.entry_debit_width_ratio,
        long_intrinsic_value=result.long_intrinsic_value,long_extrinsic_cost=result.long_extrinsic_cost,
        projected_recovery_ratio=result.projected_recovery_ratio,future_roll_score=result.future_roll_score,
        entry_cheapness_score=result.entry_cheapness_score,expected_move_clearance=round(em_clearance,6),
        liquidity_score=result.liquidity_score,regime_alignment_score=round(context.regime_alignment_score,6),
        candidate_score=_candidate_score(result,em_clearance),
        notes=[f"Environment={context.environment}",f"Cheapness={result.entry_cheapness_score:.1f}",
               f"FutureRoll={future_roll_score:.1f}",f"EMClearance={em_clearance:.2f}"])

def scan_deep_itm_calendar_candidates(context: MarketContextLite, option_type: str,
                                       long_leg_quotes: list[OptionLegQuote],
                                       short_leg_quotes: list[OptionLegQuote],
                                       candidate_next_shorts: list[OptionLegQuote],
                                       cfg: DeepITMEntryFilterConfig) -> list[DeepITMCalendarCandidate]:
    option_type=option_type.upper(); results=[]
    filtered_longs=[q for q in long_leg_quotes if q.option_type.upper()==option_type]
    filtered_shorts=[q for q in short_leg_quotes if q.option_type.upper()==option_type]
    for ll in filtered_longs:
        for sl in filtered_shorts:
            if ll.expiry==sl.expiry: continue
            long_dte=extract_dte(ll.expiry,context.as_of_date)
            short_dte=extract_dte(sl.expiry,context.as_of_date)
            fut_roll=estimate_future_roll_score(context.symbol,option_type,sl.strike,sl.expiry,candidate_next_shorts)
            proj_credits=_estimate_projected_future_roll_credits(sl.strike,option_type,candidate_next_shorts)
            c=build_deep_itm_calendar_candidate(context,option_type,ll,sl,long_dte,short_dte,
                                                 proj_credits,fut_roll,cfg)
            if c: results.append(c)
    results.sort(key=lambda x: x.candidate_score,reverse=True)
    return results
