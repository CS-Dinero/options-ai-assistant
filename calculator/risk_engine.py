"""
calculator/risk_engine.py
Trade economics, position sizing, and probability proxies.
All values are per-contract. Multiply by contracts for total risk.
"""

from config.settings import (
    CREDIT_TARGET_PERCENT,
    CREDIT_STOP_MULTIPLIER,
    DEBIT_TARGET_CAPTURE,
    DEBIT_STOP_PERCENT,
)


# ─────────────────────────────────────────────
# CREDIT SPREAD
# ─────────────────────────────────────────────

def price_credit_spread(short_mid: float, long_mid: float, width: float) -> dict:
    """
    Bear call or bull put credit spread economics.

    credit   = short_mid - long_mid
    max_loss = (width - credit) * 100
    target   = credit * 50%  → close when this much premium has decayed
    stop     = credit * 2x   → defensive exit if spread doubles against you
    """
    credit   = round(short_mid - long_mid, 2)
    max_loss = round(width - credit, 2)

    return {
        "entry_debit_credit": credit,
        "max_profit":         round(credit * 100, 2),
        "max_loss":           round(max_loss * 100, 2),
        "target_exit_value":  round(credit * CREDIT_TARGET_PERCENT, 2),
        "stop_value":         round(credit * CREDIT_STOP_MULTIPLIER, 2),
    }


# ─────────────────────────────────────────────
# DEBIT SPREAD
# ─────────────────────────────────────────────

def price_debit_spread(long_mid: float, short_mid: float, width: float) -> dict:
    """
    Bull call or bear put debit spread economics.

    debit      = long_mid - short_mid   (cost paid)
    max_profit = (width - debit) * 100
    target     = entry + 50% of remaining spread value
    stop       = lose 50% of debit
    """
    debit      = round(long_mid - short_mid, 2)
    max_profit = round(width - debit, 2)

    return {
        "entry_debit_credit": round(-debit, 2),          # negative = debit paid
        "max_profit":         round(max_profit * 100, 2),
        "max_loss":           round(debit * 100, 2),
        "target_exit_value":  round(long_mid + max_profit * DEBIT_TARGET_CAPTURE, 2),
        "stop_value":         round(debit * DEBIT_STOP_PERCENT, 2),
    }


# ─────────────────────────────────────────────
# POSITION SIZING
# ─────────────────────────────────────────────

def compute_contracts(max_risk_dollars: float, dollar_risk_per_contract: float) -> int:
    """
    Floor division: how many contracts fit within max_risk_dollars.
    Always returns at least 1.
    """
    if dollar_risk_per_contract <= 0:
        return 1
    return max(1, int(max_risk_dollars / dollar_risk_per_contract))


# ─────────────────────────────────────────────
# PROBABILITY PROXIES
# ─────────────────────────────────────────────

def prob_itm_proxy(delta: float) -> float:
    """
    P(ITM) ≈ |delta|
    Fast approximation. Use BS d2 for higher precision in Phase 2.
    """
    return round(abs(delta), 4)


def prob_touch_proxy(delta: float) -> float:
    """
    P(touch) ≈ 2 × |delta|
    A strike with 0.15 delta has roughly 30% chance of being touched.
    Useful for assessing management likelihood.
    """
    return round(min(1.0, 2 * abs(delta)), 4)
