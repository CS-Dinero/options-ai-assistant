"""engine/roll_advisor.py — Live roll advisor using Tradier chain data.

Given an open campaign (logged trade), fetches current short leg price and
next-expiry candidates to determine whether a net-credit roll is available.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any

@dataclass
class RollAdvice:
    symbol: str
    current_short_strike: float
    current_short_expiry: str
    current_short_mid: float        # cost to close
    option_type: str

    # Best roll candidate
    proposed_short_strike: float
    proposed_short_expiry: str
    proposed_short_mid: float       # premium received

    roll_credit_est: float          # proposed - close = net credit (positive = good)
    net_credit_positive: bool

    # Forward continuity
    next_gen_avg_premium: float     # avg premium of following expiry (viability check)
    continuity_score: float         # 0-100

    # Campaign state
    campaign_basis_before: float
    campaign_basis_after: float
    basis_reduction: float
    recovery_pct_before: float
    recovery_pct_after: float
    excess_harvest_after: float
    spread_funding_unlocked: bool

    recommendation: str
    action: str                     # ROLL | HARVEST | HOLD | WAIT

def get_roll_advice(
    symbol: str,
    option_type: str,
    current_short_strike: float,
    current_short_expiry: str,
    long_expiry: str,
    entry_debit: float,
    total_credits_so_far: float,
    total_costs_so_far: float,
    contracts: int = 1,
    session=None,
) -> RollAdvice | dict:
    """
    Fetch live chain data and compute roll recommendation.
    Returns RollAdvice or dict with "error" key on failure.
    """
    from data_sources.tradier_api import (
        get_expirations, get_option_chain, get_spot_price,
        pick_short_expiration, TradierAPIError,
    )

    ot = option_type.upper()
    today = date.today().isoformat()

    # ── Current campaign state ─────────────────────────────────────────────────
    basis_before = round(entry_debit - total_credits_so_far + total_costs_so_far, 4)
    base_outlay  = max(0.01, entry_debit)
    rec_before   = round(max(0.0, (entry_debit - basis_before) / base_outlay * 100), 2)

    try:
        spot = get_spot_price(symbol, session=session)
        expirations = get_expirations(symbol, session=session)
    except TradierAPIError as e:
        return {"error": str(e)}

    # ── Find next expiries after current short ────────────────────────────────
    future_exps = sorted([e for e in expirations if e > current_short_expiry and e < long_expiry])
    if not future_exps:
        return {"error": f"No future expirations available between {current_short_expiry} and {long_expiry}"}

    next_exp  = future_exps[0]
    gen2_exp  = future_exps[1] if len(future_exps) > 1 else None

    # ── Current short leg price (cost to close) ───────────────────────────────
    try:
        current_chain = get_option_chain(symbol, current_short_expiry, session=session)
    except TradierAPIError as e:
        return {"error": f"Current chain fetch failed: {e}"}

    current_rows = [r for r in current_chain
                    if r["option_type"] == ot.lower()
                    and abs(r["strike"] - current_short_strike) < 0.01]
    if not current_rows:
        return {"error": f"Could not find {current_short_strike} {ot} in current chain"}

    close_mid = current_rows[0]["mid"]

    # ── Next expiry candidates ────────────────────────────────────────────────
    try:
        next_chain = get_option_chain(symbol, next_exp, session=session)
    except TradierAPIError as e:
        return {"error": f"Next chain fetch failed: {e}"}

    next_rows = [r for r in next_chain
                 if r["option_type"] == ot.lower()
                 and r["mid"] > 0
                 and abs(r["delta"] or 0) >= 0.15]

    if not next_rows:
        return {"error": f"No viable {ot} candidates in {next_exp}"}

    # Best same-side roll: closest strike to current, premium > close cost
    same_strike_rows = sorted(next_rows, key=lambda r: abs(r["strike"] - current_short_strike))
    best_roll = same_strike_rows[0]

    roll_credit = round(best_roll["mid"] - close_mid, 4)
    net_positive = roll_credit > 0.10  # require at least $0.10 net credit

    # ── Generation-2 continuity check ────────────────────────────────────────
    next_gen_avg = 0.0
    if gen2_exp:
        try:
            gen2_chain = get_option_chain(symbol, gen2_exp, session=session)
            gen2_rows  = [r for r in gen2_chain
                          if r["option_type"] == ot.lower() and r["mid"] > 0
                          and abs(r["strike"] - current_short_strike) < 10]
            if gen2_rows:
                next_gen_avg = round(sum(r["mid"] for r in gen2_rows[:3]) / min(3, len(gen2_rows)), 4)
        except TradierAPIError:
            pass

    continuity_score = min(100.0, next_gen_avg * 60)  # $1.67 avg → 100

    # ── Post-roll campaign state ──────────────────────────────────────────────
    new_credits = total_credits_so_far + best_roll["mid"]
    new_costs   = total_costs_so_far + close_mid
    basis_after = round(entry_debit - new_credits + new_costs, 4)
    rec_after   = round(max(0.0, (entry_debit - basis_after) / base_outlay * 100), 2)
    excess_after= round(max(0.0, -basis_after), 4)
    spread_unlocked = excess_after > 0.25

    # ── Recommendation ────────────────────────────────────────────────────────
    if not net_positive:
        action = "WAIT"
        rec = (f"Roll not yet profitable. Net credit would be ${roll_credit:.2f}. "
               f"Wait for {current_short_strike} {ot} to decay further. "
               f"Current close cost: ${close_mid:.2f}")
    elif basis_after < 0:
        action = "ROLL"
        rec = (f"🌟 GOLDEN HARVEST — Roll produces net credit AND fully recovers debit. "
               f"Roll credit: ${roll_credit:.2f}. Basis after: ${basis_after:.2f} "
               f"(${abs(basis_after):.2f} excess → available for spreads)")
    elif rec_after >= 80:
        action = "ROLL"
        rec = (f"Strong roll — {rec_after:.1f}% recovered after roll. "
               f"Net credit: ${roll_credit:.2f}. Keep rolling.")
    else:
        action = "ROLL"
        rec = (f"Net credit roll available: ${roll_credit:.2f}. "
               f"Basis improves from ${basis_before:.2f} → ${basis_after:.2f} "
               f"({rec_before:.1f}% → {rec_after:.1f}% recovered).")

    return RollAdvice(
        symbol=symbol,
        current_short_strike=current_short_strike,
        current_short_expiry=current_short_expiry,
        current_short_mid=round(close_mid, 4),
        option_type=ot,
        proposed_short_strike=best_roll["strike"],
        proposed_short_expiry=next_exp,
        proposed_short_mid=round(best_roll["mid"], 4),
        roll_credit_est=roll_credit,
        net_credit_positive=net_positive,
        next_gen_avg_premium=next_gen_avg,
        continuity_score=round(continuity_score, 2),
        campaign_basis_before=basis_before,
        campaign_basis_after=basis_after,
        basis_reduction=round(basis_before - basis_after, 4),
        recovery_pct_before=rec_before,
        recovery_pct_after=rec_after,
        excess_harvest_after=excess_after,
        spread_funding_unlocked=spread_unlocked,
        recommendation=rec,
        action=action,
    )


# ── Assignment guard integration ───────────────────────────────────────────────
def check_position_rescue(
    symbol: str,
    option_type: str,
    short_strike: float,
    short_expiry: str,
    short_dte: int,
    short_delta: float,
    short_mid: float,
    long_strike: float,
    spot_price: float,
    atr: float,
    move_today: float,
    opposite_strike: float,
    opposite_expiry: str,
    opposite_mid: float,
    roll_credit_est: float,
    contracts: int,
    entry_debit: float,
    total_credits: float,
    total_costs: float,
    account_cash: float,
) -> dict:
    """
    Wrapper that calls full_rescue_check and returns a dashboard-ready summary.
    Wire this into the roll advisor panel for live rescue alerts.
    """
    from engine.assignment_guard import full_rescue_check
    width = abs(short_strike - long_strike)
    result = full_rescue_check(
        symbol=symbol, option_type=option_type,
        short_strike=short_strike, short_expiry=short_expiry,
        short_dte=short_dte, short_delta=short_delta,
        short_mid=short_mid, spot_price=spot_price,
        atr=atr, move_today=move_today,
        opposite_strike=opposite_strike, opposite_expiry=opposite_expiry,
        opposite_mid=opposite_mid, roll_credit_per_contract=roll_credit_est,
        current_contracts=contracts, proposed_contracts=contracts + 2,
        spread_width=width, entry_debit=entry_debit,
        total_credits=total_credits, total_costs=total_costs,
        account_cash=account_cash,
    )
    return result
