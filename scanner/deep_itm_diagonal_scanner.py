"""scanner/deep_itm_diagonal_scanner.py — Direct diagonal entries when regime/skew favors them."""
from __future__ import annotations
from dataclasses import dataclass, field
from scanner.deep_itm_entry_filters import (
    OptionLegQuote, DeepITMEntryFilterConfig, evaluate_deep_itm_entry_filters,
)
from scanner.deep_itm_calendar_scanner import (
    MarketContextLite, estimate_entry_net_debit, estimate_expected_move_clearance,
    estimate_liquidity_score, estimate_future_roll_score, _leg_to_dict,
)

@dataclass(slots=True)
class DeepITMDiagonalConfig(DeepITMEntryFilterConfig):
    long_delta_min: float=0.60; long_delta_max: float=0.85

@dataclass(slots=True)
class DeepITMDiagonalCandidate:
    symbol: str; campaign_family: str; entry_family: str; structure: str; option_type: str
    long_leg: dict; short_leg: dict; short_dte: int; long_dte: int; strike_width: float
    entry_net_debit: float; entry_cheapness_score: float; future_roll_score: float
    expected_move_clearance: float; liquidity_score: float; regime_alignment_score: float
    directional_alignment_score: float; candidate_score: float; notes: list[str]=field(default_factory=list)

def estimate_directional_alignment(option_type: str, gamma_regime: str, iv_percentile: float) -> float:
    dir_ok=(("TRENDING" in gamma_regime and option_type.upper()=="CALL")
            or ("PREMIUM_SELLING" in gamma_regime and iv_percentile>=60))
    return 80.0 if dir_ok else 45.0

def build_deep_itm_diagonal_candidate(context: MarketContextLite, option_type: str,
                                       long_leg: OptionLegQuote, short_leg: OptionLegQuote,
                                       long_dte: int, short_dte: int,
                                       next_gen_shorts: list[OptionLegQuote],
                                       cfg: DeepITMDiagonalConfig) -> DeepITMDiagonalCandidate|None:
    net_debit=estimate_entry_net_debit(long_leg.mid,short_leg.mid)
    strike_width=abs(long_leg.strike-short_leg.strike)
    fut_roll=estimate_future_roll_score(next_gen_shorts)
    liquidity=estimate_liquidity_score(long_leg,short_leg)
    em_clear=estimate_expected_move_clearance(context.spot_price,short_leg.strike,context.expected_move,option_type)
    proj_credits=net_debit*1.5
    result=evaluate_deep_itm_entry_filters(context.spot_price,option_type,long_leg,short_leg,
                                            long_dte,short_dte,strike_width,net_debit,
                                            proj_credits,fut_roll,liquidity,context.regime_alignment_score,cfg)
    if not result.passed: return None
    dir_score=estimate_directional_alignment(option_type,context.gamma_regime,context.iv_percentile)
    cs=round(0.30*result.entry_cheapness_score+0.20*fut_roll+0.15*liquidity
             +0.20*dir_score+0.15*min(100,em_clear*100),2)
    return DeepITMDiagonalCandidate(
        symbol=context.symbol,campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_DIAGONAL_ENTRY",structure="DEEP_ITM_DIAGONAL",
        option_type=option_type,long_leg=_leg_to_dict(long_leg),short_leg=_leg_to_dict(short_leg),
        short_dte=short_dte,long_dte=long_dte,strike_width=round(strike_width,2),
        entry_net_debit=net_debit,entry_cheapness_score=result.entry_cheapness_score,
        future_roll_score=fut_roll,expected_move_clearance=em_clear,liquidity_score=liquidity,
        regime_alignment_score=context.regime_alignment_score,
        directional_alignment_score=dir_score,candidate_score=cs)

def scan_deep_itm_diagonal_candidates(context: MarketContextLite, option_type: str,
                                       long_legs: list[OptionLegQuote], short_legs: list[OptionLegQuote],
                                       long_dtelist: list[int], short_dtelist: list[int],
                                       next_gen_shorts: list[OptionLegQuote],
                                       cfg: DeepITMDiagonalConfig|None=None) -> list[DeepITMDiagonalCandidate]:
    cfg=cfg or DeepITMDiagonalConfig(); out=[]
    for ll in long_legs:
        for sl in short_legs:
            for ld,sd in zip(long_dtelist,short_dtelist):
                c=build_deep_itm_diagonal_candidate(context,option_type,ll,sl,ld,sd,next_gen_shorts,cfg)
                if c: out.append(c)
    return sorted(out,key=lambda x: x.candidate_score,reverse=True)
