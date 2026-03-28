"""scanner/deep_itm_entry_filters.py — Pure filter and score logic for deep ITM entries."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence

@dataclass(slots=True)
class OptionLegQuote:
    symbol: str; option_type: str; expiry: str; strike: float
    bid: float; ask: float; mid: float; delta: float|None
    open_interest: int|None; volume: int|None

@dataclass(slots=True)
class DeepITMEntryFilterConfig:
    long_delta_min: float=0.70; long_delta_max: float=0.90
    short_dte_min: int=7; short_dte_max: int=14
    long_dte_min: int=30; long_dte_max: int=60
    min_open_interest: int=100; min_volume: int=1; min_short_premium: float=1.00
    max_bid_ask_width_pct: float=0.20
    max_entry_debit_width_ratio: float=0.35; max_long_extrinsic_cost: float=8.00
    min_projected_recovery_ratio: float=1.20; min_future_roll_score: float=60.0

@dataclass(slots=True)
class DeepITMEntryFilterResult:
    passed: bool; entry_debit_width_ratio: float; long_intrinsic_value: float
    long_extrinsic_cost: float; projected_recovery_ratio: float
    entry_cheapness_score: float; future_roll_score: float
    liquidity_score: float; reasons: list[str]=field(default_factory=list)

def _safe_abs_delta(delta: float|None) -> float:
    return abs(delta) if delta is not None else 0.0

def compute_long_intrinsic_value(spot_price: float, option_type: str, long_strike: float) -> float:
    return max(0.0, spot_price-long_strike) if option_type.upper()=="CALL" else max(0.0,long_strike-spot_price)

def compute_long_extrinsic_cost(long_mid: float, long_intrinsic_value: float) -> float:
    return max(0.0, long_mid-long_intrinsic_value)

def compute_entry_debit_width_ratio(net_debit: float, strike_width: float) -> float:
    return float(net_debit)/max(0.01,float(strike_width))

def compute_projected_recovery_ratio(projected_future_roll_credits: float, net_debit: float) -> float:
    return float(projected_future_roll_credits)/max(0.01,float(net_debit))

def _score_inverse(value: float, good_floor: float, bad_ceiling: float) -> float:
    if value<=good_floor: return 100.0
    if value>=bad_ceiling: return 0.0
    return max(0.0,min(100.0,100.0*(bad_ceiling-value)/max(0.0001,bad_ceiling-good_floor)))

def _score_forward(value: float, bad_floor: float, good_target: float) -> float:
    if value<=bad_floor: return 0.0
    if value>=good_target: return 100.0
    return max(0.0,min(100.0,100.0*(value-bad_floor)/max(0.0001,good_target-bad_floor)))

def _bid_ask_width_pct(leg: OptionLegQuote) -> float:
    if leg.mid<=0: return 1.0
    return max(0.0,(leg.ask-leg.bid)/max(0.01,leg.mid))

def compute_liquidity_score(long_leg: OptionLegQuote, short_leg: OptionLegQuote,
                             cfg: DeepITMEntryFilterConfig) -> float:
    lw=_bid_ask_width_pct(long_leg); sw=_bid_ask_width_pct(short_leg)
    width_score=(_score_inverse(lw,0.02,cfg.max_bid_ask_width_pct)*0.50
                 +_score_inverse(sw,0.02,cfg.max_bid_ask_width_pct)*0.50)
    oi_score=min(100.0,((float(long_leg.open_interest or 0)+float(short_leg.open_interest or 0))
                        /max(1.0,2*cfg.min_open_interest))*100.0)
    vol_score=min(100.0,((float(long_leg.volume or 0)+float(short_leg.volume or 0))
                         /max(1.0,2*cfg.min_volume))*100.0)
    return round(0.50*width_score+0.30*oi_score+0.20*vol_score,4)

def compute_entry_cheapness_score(entry_debit_width_ratio: float, long_extrinsic_cost: float,
                                   projected_recovery_ratio: float, future_roll_score: float,
                                   liquidity_score: float, regime_alignment_score: float) -> float:
    return round(0.25*_score_inverse(entry_debit_width_ratio,0.12,0.45)
                 +0.20*_score_inverse(long_extrinsic_cost,1.5,12.0)
                 +0.20*_score_forward(projected_recovery_ratio,0.8,1.8)
                 +0.15*max(0.0,min(100.0,future_roll_score))
                 +0.10*max(0.0,min(100.0,liquidity_score))
                 +0.10*max(0.0,min(100.0,regime_alignment_score)),4)

def passes_long_leg_filter(long_leg: OptionLegQuote, long_dte: int,
                            cfg: DeepITMEntryFilterConfig) -> tuple[bool,list[str]]:
    r=[]
    if long_leg.delta is None: r.append("Long leg delta missing.")
    else:
        d=_safe_abs_delta(long_leg.delta)
        if not(cfg.long_delta_min<=d<=cfg.long_delta_max):
            r.append(f"Long delta {d:.3f} outside [{cfg.long_delta_min:.2f},{cfg.long_delta_max:.2f}].")
    if not(cfg.long_dte_min<=long_dte<=cfg.long_dte_max):
        r.append(f"Long DTE {long_dte} outside [{cfg.long_dte_min},{cfg.long_dte_max}].")
    if (long_leg.open_interest or 0)<cfg.min_open_interest: r.append("Long OI below minimum.")
    if (long_leg.volume or 0)<cfg.min_volume: r.append("Long volume below minimum.")
    if _bid_ask_width_pct(long_leg)>cfg.max_bid_ask_width_pct: r.append("Long bid/ask width too wide.")
    return len(r)==0,r

def passes_short_leg_filter(short_leg: OptionLegQuote, short_dte: int,
                             cfg: DeepITMEntryFilterConfig) -> tuple[bool,list[str]]:
    r=[]
    if not(cfg.short_dte_min<=short_dte<=cfg.short_dte_max):
        r.append(f"Short DTE {short_dte} outside [{cfg.short_dte_min},{cfg.short_dte_max}].")
    if short_leg.mid<cfg.min_short_premium:
        r.append(f"Short premium {short_leg.mid:.2f} below min {cfg.min_short_premium:.2f}.")
    if (short_leg.open_interest or 0)<cfg.min_open_interest: r.append("Short OI below minimum.")
    if (short_leg.volume or 0)<cfg.min_volume: r.append("Short volume below minimum.")
    if _bid_ask_width_pct(short_leg)>cfg.max_bid_ask_width_pct: r.append("Short bid/ask width too wide.")
    return len(r)==0,r

def evaluate_deep_itm_entry_filters(spot_price: float, option_type: str,
                                     long_leg: OptionLegQuote, short_leg: OptionLegQuote,
                                     long_dte: int, short_dte: int, strike_width: float, net_debit: float,
                                     projected_future_roll_credits: float, future_roll_score: float,
                                     liquidity_score: float, regime_alignment_score: float,
                                     cfg: DeepITMEntryFilterConfig) -> DeepITMEntryFilterResult:
    reasons=[]
    long_ok,lr=passes_long_leg_filter(long_leg,long_dte,cfg); reasons.extend(lr)
    short_ok,sr=passes_short_leg_filter(short_leg,short_dte,cfg); reasons.extend(sr)
    intrinsic=compute_long_intrinsic_value(spot_price,option_type,long_leg.strike)
    extrinsic=compute_long_extrinsic_cost(long_leg.mid,intrinsic)
    ratio=compute_entry_debit_width_ratio(net_debit,strike_width)
    rec_ratio=compute_projected_recovery_ratio(projected_future_roll_credits,net_debit)
    if ratio>cfg.max_entry_debit_width_ratio:
        reasons.append(f"Debit/width ratio {ratio:.3f} exceeds {cfg.max_entry_debit_width_ratio:.3f}.")
    if extrinsic>cfg.max_long_extrinsic_cost:
        reasons.append(f"Long extrinsic {extrinsic:.2f} exceeds {cfg.max_long_extrinsic_cost:.2f}.")
    if rec_ratio<cfg.min_projected_recovery_ratio:
        reasons.append(f"Recovery ratio {rec_ratio:.2f} below {cfg.min_projected_recovery_ratio:.2f}.")
    if future_roll_score<cfg.min_future_roll_score:
        reasons.append(f"Future roll score {future_roll_score:.1f} below {cfg.min_future_roll_score:.1f}.")
    cheapness=compute_entry_cheapness_score(ratio,extrinsic,rec_ratio,future_roll_score,
                                            liquidity_score,regime_alignment_score)
    passed=long_ok and short_ok and len(reasons)==0
    return DeepITMEntryFilterResult(passed=passed,entry_debit_width_ratio=round(ratio,6),
        long_intrinsic_value=round(intrinsic,6),long_extrinsic_cost=round(extrinsic,6),
        projected_recovery_ratio=round(rec_ratio,6),entry_cheapness_score=round(cheapness,6),
        future_roll_score=round(float(future_roll_score),6),liquidity_score=round(float(liquidity_score),6),
        reasons=reasons)
