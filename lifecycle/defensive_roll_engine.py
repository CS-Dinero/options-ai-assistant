"""lifecycle/defensive_roll_engine.py — Handles defensive repair separately from harvest logic."""
from __future__ import annotations
from dataclasses import dataclass
from scanner.deep_itm_entry_filters import OptionLegQuote

RepairType = str  # ROLL_OUT_TIME | MOVE_STRIKE_AWAY | REDUCE_SIZE | CONVERT_TO_VERTICAL

@dataclass(slots=True)
class DefenseResult:
    defense_candidate: bool; repair_type: RepairType
    repair_cost_est: float; repair_survivability_score: float
    repair_recovery_score: float; reason: str

def score_repair_survivability(em_ratio: float, proposed_dte: int, strike_improvement: float) -> float:
    em_score=min(100.0,em_ratio*100.0); dte_score=min(100.0,proposed_dte*5.0)
    return round(0.40*em_score+0.30*dte_score+0.30*min(100,strike_improvement),2)

def score_repair_recovery(campaign_recovered_pct: float, repair_cost: float, long_value: float) -> float:
    rec_score=min(100.0,campaign_recovered_pct)
    cost_ratio=max(0.0,1.0-repair_cost/max(0.01,long_value))
    return round(0.60*rec_score+0.40*cost_ratio*100,2)

def evaluate_defensive_roll(symbol: str, option_type: str, current_short_strike: float,
                             proposed_short: OptionLegQuote, close_cost: float,
                             proposed_em_clearance: float, proposed_dte: int,
                             campaign_recovered_pct: float, long_value: float,
                             max_defense_debit: float=0.40) -> DefenseResult:
    repair_cost=max(0.0, close_cost-proposed_short.mid)
    strike_imp=(proposed_short.strike-current_short_strike if option_type.upper()=="CALL"
                else current_short_strike-proposed_short.strike)
    surv=score_repair_survivability(proposed_em_clearance,proposed_dte,max(0,strike_imp))
    rec=score_repair_recovery(campaign_recovered_pct,repair_cost,long_value)
    if repair_cost>max_defense_debit and surv<55.0:
        return DefenseResult(False,"ROLL_OUT_TIME",repair_cost,surv,rec,
                             f"Defense cost {repair_cost:.3f} too high without survivability improvement.")
    repair_type=("MOVE_STRIKE_AWAY" if strike_imp>2 else
                 "ROLL_OUT_TIME" if proposed_dte>14 else "REDUCE_SIZE")
    return DefenseResult(True,repair_type,repair_cost,surv,rec,
                         f"Defensive {repair_type}: cost={repair_cost:.3f} surv={surv:.1f}")
