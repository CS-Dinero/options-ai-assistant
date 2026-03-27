"""scanner/deep_itm_calendar_scanner.py — Discovers deep ITM calendar entry candidates."""
from __future__ import annotations
from dataclasses import dataclass, field
from scanner.deep_itm_entry_filters import (
    OptionLegQuote, DeepITMEntryFilterConfig, evaluate_deep_itm_entry_filters,
)

@dataclass(slots=True)
class MarketContextLite:
    symbol: str; spot_price: float; expected_move: float
    iv_percentile: float; gamma_regime: str; environment: str; regime_alignment_score: float

@dataclass(slots=True)
class DeepITMCalendarCandidate:
    symbol: str; campaign_family: str; entry_family: str; structure: str; option_type: str
    long_leg: dict; short_leg: dict; short_dte: int; long_dte: int; strike_width: float
    entry_net_debit: float; entry_debit_width_ratio: float; long_intrinsic_value: float
    long_extrinsic_cost: float; projected_recovery_ratio: float; future_roll_score: float
    entry_cheapness_score: float; expected_move_clearance: float; liquidity_score: float
    regime_alignment_score: float; candidate_score: float; notes: list[str]=field(default_factory=list)

def estimate_entry_net_debit(long_mid: float, short_mid: float) -> float:
    return round(max(0.0, long_mid-short_mid), 4)

def estimate_expected_move_clearance(spot_price: float, short_strike: float,
                                      expected_move: float, option_type: str) -> float:
    if expected_move<=0: return 0.0
    dist=abs(short_strike-spot_price) if option_type.upper()=="CALL" else abs(spot_price-short_strike)
    return round(dist/max(0.01,expected_move),4)

def estimate_liquidity_score(long_leg: OptionLegQuote, short_leg: OptionLegQuote) -> float:
    long_oi=long_leg.open_interest or 0; short_oi=short_leg.open_interest or 0
    oi_score=min(100.0,(long_oi+short_oi)/20.0)
    long_spread=(long_leg.ask-long_leg.bid)/max(0.01,long_leg.mid)
    short_spread=(short_leg.ask-short_leg.bid)/max(0.01,short_leg.mid) if short_leg.mid>0 else 1.0
    spread_score=max(0.0,100.0-(long_spread+short_spread)*100.0)
    return round(0.6*oi_score+0.4*spread_score,2)

def estimate_future_roll_score(next_gen_shorts: list[OptionLegQuote]) -> float:
    if not next_gen_shorts: return 30.0
    avg_mid=sum(s.mid for s in next_gen_shorts)/len(next_gen_shorts)
    avg_oi=sum((s.open_interest or 0) for s in next_gen_shorts)/len(next_gen_shorts)
    score=min(100.0,avg_mid*15+min(50,avg_oi/100))
    return round(score,2)

def _leg_to_dict(leg: OptionLegQuote) -> dict:
    return {"symbol":leg.symbol,"option_type":leg.option_type,"expiry":leg.expiry,
            "strike":leg.strike,"bid":leg.bid,"ask":leg.ask,"mid":leg.mid,
            "delta":leg.delta,"open_interest":leg.open_interest,"volume":leg.volume}

def build_deep_itm_calendar_candidate(context: MarketContextLite, option_type: str,
                                       long_leg: OptionLegQuote, short_leg: OptionLegQuote,
                                       long_dte: int, short_dte: int,
                                       projected_future_roll_credits: float,
                                       next_gen_shorts: list[OptionLegQuote],
                                       cfg: DeepITMEntryFilterConfig) -> DeepITMCalendarCandidate|None:
    net_debit=estimate_entry_net_debit(long_leg.mid,short_leg.mid)
    strike_width=abs(long_leg.strike-short_leg.strike)
    fut_roll=estimate_future_roll_score(next_gen_shorts)
    liquidity=estimate_liquidity_score(long_leg,short_leg)
    em_clearance=estimate_expected_move_clearance(context.spot_price,short_leg.strike,
                                                   context.expected_move,option_type)
    result=evaluate_deep_itm_entry_filters(context.spot_price,option_type,long_leg,short_leg,
                                            long_dte,short_dte,strike_width,net_debit,
                                            projected_future_roll_credits,fut_roll,liquidity,
                                            context.regime_alignment_score,cfg)
    if not result.passed: return None
    candidate_score=round(0.35*result.entry_cheapness_score+0.25*fut_roll
                          +0.20*liquidity+0.20*min(100,em_clearance*100),2)
    return DeepITMCalendarCandidate(
        symbol=context.symbol, campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY", structure="DEEP_ITM_CALENDAR",
        option_type=option_type, long_leg=_leg_to_dict(long_leg), short_leg=_leg_to_dict(short_leg),
        short_dte=short_dte, long_dte=long_dte, strike_width=round(strike_width,2),
        entry_net_debit=net_debit, entry_debit_width_ratio=result.entry_debit_width_ratio,
        long_intrinsic_value=result.long_intrinsic_value, long_extrinsic_cost=result.long_extrinsic_cost,
        projected_recovery_ratio=result.projected_recovery_ratio, future_roll_score=fut_roll,
        entry_cheapness_score=result.entry_cheapness_score, expected_move_clearance=em_clearance,
        liquidity_score=liquidity, regime_alignment_score=context.regime_alignment_score,
        candidate_score=candidate_score)

def scan_deep_itm_calendar_candidates(context: MarketContextLite, option_type: str,
                                       long_leg_quotes: list[OptionLegQuote],
                                       short_leg_quotes: list[OptionLegQuote],
                                       long_dtelist: list[int], short_dtelist: list[int],
                                       next_gen_shorts: list[OptionLegQuote],
                                       cfg: DeepITMEntryFilterConfig|None=None,
                                       projected_credits_per_debit: float=0.5) -> list[DeepITMCalendarCandidate]:
    cfg=cfg or DeepITMEntryFilterConfig(); candidates=[]
    for ll in long_leg_quotes:
        for sl in short_leg_quotes:
            for ld,sd in zip(long_dtelist,short_dtelist):
                net_debit=estimate_entry_net_debit(ll.mid,sl.mid)
                proj_credits=net_debit*projected_credits_per_debit*1.4
                c=build_deep_itm_calendar_candidate(context,option_type,ll,sl,ld,sd,
                                                     proj_credits,next_gen_shorts,cfg)
                if c: candidates.append(c)
    return sorted(candidates,key=lambda x: x.candidate_score,reverse=True)
