"""scanner/deep_itm_entry_filters.py — Pure filter and score logic for deep ITM entries."""
from __future__ import annotations
from dataclasses import dataclass, field

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
    min_open_interest: int=100; min_premium: float=1.00
    max_entry_debit_width_ratio: float=0.35
    max_long_extrinsic_cost: float=8.00
    min_projected_recovery_ratio: float=1.20
    min_future_roll_score: float=60.0

@dataclass(slots=True)
class DeepITMEntryFilterResult:
    passed: bool; entry_debit_width_ratio: float; long_intrinsic_value: float
    long_extrinsic_cost: float; projected_recovery_ratio: float
    entry_cheapness_score: float; future_roll_score: float; reasons: list[str]=field(default_factory=list)

def compute_long_intrinsic_value(spot_price: float, option_type: str, long_strike: float) -> float:
    return max(0.0, spot_price-long_strike) if option_type.upper()=="CALL" else max(0.0,long_strike-spot_price)

def compute_long_extrinsic_cost(long_mid: float, long_intrinsic: float) -> float:
    return max(0.0, long_mid-long_intrinsic)

def compute_entry_debit_width_ratio(net_debit: float, strike_width: float) -> float:
    return round(net_debit/max(0.01,strike_width),4)

def compute_projected_recovery_ratio(projected_future_roll_credits: float, net_debit: float) -> float:
    return round(projected_future_roll_credits/max(0.01,net_debit),4)

def compute_entry_cheapness_score(entry_debit_width_ratio: float, long_extrinsic_cost: float,
                                   projected_recovery_ratio: float, future_roll_score: float,
                                   liquidity_score: float, regime_alignment_score: float) -> float:
    ratio_score  =max(0.0,100.0-entry_debit_width_ratio*200.0)   # lower ratio → better
    extr_score   =max(0.0,100.0-long_extrinsic_cost*8.0)          # lower extrinsic → better
    rec_score    =min(100.0,max(0.0,(projected_recovery_ratio-1.0)*100.0))
    roll_score   =min(100.0,max(0.0,future_roll_score))
    return round(0.25*ratio_score+0.20*extr_score+0.25*rec_score+
                 0.15*roll_score+0.10*min(100,liquidity_score)+0.05*min(100,regime_alignment_score),2)

def passes_long_leg_filter(long_leg: OptionLegQuote, long_dte: int,
                            cfg: DeepITMEntryFilterConfig) -> tuple[bool,list[str]]:
    reasons=[]
    if long_leg.delta is not None and not (cfg.long_delta_min<=long_leg.delta<=cfg.long_delta_max):
        reasons.append(f"Long delta {long_leg.delta:.2f} outside [{cfg.long_delta_min},{cfg.long_delta_max}]")
    if not (cfg.long_dte_min<=long_dte<=cfg.long_dte_max):
        reasons.append(f"Long DTE {long_dte} outside [{cfg.long_dte_min},{cfg.long_dte_max}]")
    if long_leg.open_interest is not None and long_leg.open_interest<cfg.min_open_interest:
        reasons.append(f"Long OI {long_leg.open_interest} below min {cfg.min_open_interest}")
    if long_leg.mid<cfg.min_premium:
        reasons.append(f"Long premium {long_leg.mid:.2f} below min {cfg.min_premium}")
    return len(reasons)==0, reasons

def passes_short_leg_filter(short_leg: OptionLegQuote, short_dte: int,
                             cfg: DeepITMEntryFilterConfig) -> tuple[bool,list[str]]:
    reasons=[]
    if not (cfg.short_dte_min<=short_dte<=cfg.short_dte_max):
        reasons.append(f"Short DTE {short_dte} outside [{cfg.short_dte_min},{cfg.short_dte_max}]")
    if short_leg.mid<cfg.min_premium*0.25:
        reasons.append(f"Short premium {short_leg.mid:.2f} too low")
    if short_leg.open_interest is not None and short_leg.open_interest<cfg.min_open_interest//2:
        reasons.append(f"Short OI {short_leg.open_interest} below min")
    return len(reasons)==0, reasons

def evaluate_deep_itm_entry_filters(spot_price: float, option_type: str, long_leg: OptionLegQuote,
                                     short_leg: OptionLegQuote, long_dte: int, short_dte: int,
                                     strike_width: float, net_debit: float,
                                     projected_future_roll_credits: float, future_roll_score: float,
                                     liquidity_score: float, regime_alignment_score: float,
                                     cfg: DeepITMEntryFilterConfig) -> DeepITMEntryFilterResult:
    all_reasons=[]
    long_ok,lr=passes_long_leg_filter(long_leg,long_dte,cfg); all_reasons.extend(lr)
    short_ok,sr=passes_short_leg_filter(short_leg,short_dte,cfg); all_reasons.extend(sr)
    intrinsic=compute_long_intrinsic_value(spot_price,option_type,long_leg.strike)
    extrinsic=compute_long_extrinsic_cost(long_leg.mid,intrinsic)
    ratio=compute_entry_debit_width_ratio(net_debit,strike_width)
    rec_ratio=compute_projected_recovery_ratio(projected_future_roll_credits,net_debit)
    cheapness=compute_entry_cheapness_score(ratio,extrinsic,rec_ratio,future_roll_score,
                                            liquidity_score,regime_alignment_score)
    if ratio>cfg.max_entry_debit_width_ratio:
        all_reasons.append(f"Debit/width ratio {ratio:.3f} > max {cfg.max_entry_debit_width_ratio}")
    if extrinsic>cfg.max_long_extrinsic_cost:
        all_reasons.append(f"Long extrinsic {extrinsic:.2f} > max {cfg.max_long_extrinsic_cost}")
    if rec_ratio<cfg.min_projected_recovery_ratio:
        all_reasons.append(f"Recovery ratio {rec_ratio:.2f} < min {cfg.min_projected_recovery_ratio}")
    if future_roll_score<cfg.min_future_roll_score:
        all_reasons.append(f"Future roll score {future_roll_score:.1f} < min {cfg.min_future_roll_score}")
    passed=len(all_reasons)==0
    return DeepITMEntryFilterResult(passed=passed,entry_debit_width_ratio=ratio,
                                     long_intrinsic_value=intrinsic,long_extrinsic_cost=extrinsic,
                                     projected_recovery_ratio=rec_ratio,entry_cheapness_score=cheapness,
                                     future_roll_score=future_roll_score,reasons=all_reasons)
