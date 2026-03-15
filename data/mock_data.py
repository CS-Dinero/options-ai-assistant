"""
data/mock_data.py
Static SPY market context and realistic mock option chain.
Replace load_mock_market() with a live API call when ready.
Replace build_mock_chain() with polygon_api or tradier_api.
"""

import math
from typing import Optional


# ─────────────────────────────────────────────
# MARKET CONTEXT
# ─────────────────────────────────────────────

_MARKET_STATIC = {
    "symbol":           "SPY",
    "spot_price":       520.15,

    # ATR
    "atr_14":           3.20,
    "atr_prior":        2.85,

    # IV
    "iv_percentile":    22.0,
    "front_iv":         16.2,
    "back_iv":          19.1,

    # ATM straddle (for expected move)
    "atm_call_mid":     4.85,
    "atm_put_mid":      4.25,
    "front_dte":        7,

    # Skew — 25-delta IVs
    "put_25d_iv":       18.4,
    "call_25d_iv":      12.6,

    # Gamma context (set any to None to test partial-input normalization)
    "gamma_flip":           530.0,
    "gamma_trap_strike":    520.0,
    "total_gex":            4.2e9,

    # Trade sizing
    "preferred_risk_dollars": 500,
    "default_spread_width":   5,
    "long_dte_target":        60,
    "short_dte_target":       7,

    # Event flag
    "event_flag": False,
}


def load_mock_market() -> dict:
    """Return a copy of the static market context dict."""
    return _MARKET_STATIC.copy()


# ─────────────────────────────────────────────
# MOCK OPTION CHAIN BUILDER
# ─────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _bs_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str):
    """
    Black-Scholes option pricing.
    Returns: (price, delta, gamma, theta, vega, d2)
    """
    if T <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return intrinsic, (1.0 if option_type == "call" else -1.0), 0.0, 0.0, 0.0, 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        delta = _norm_cdf(d1)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = -_norm_cdf(-d1)

    gamma = _norm_cdf(d1) / (S * sigma * math.sqrt(T))
    theta = (
        -(S * _norm_cdf(d1) * sigma) / (2 * math.sqrt(T))
        - r * K * math.exp(-r * T) * _norm_cdf(d2)
    ) / 365
    vega  = S * _norm_cdf(d1) * math.sqrt(T) / 100

    return price, delta, gamma, theta, vega, d2


def _skew_iv(spot: float, K: float, option_type: str, T: float, base_sigma: float) -> float:
    """
    Realistic skew: OTM puts carry higher IV than OTM calls.
    Back month carries higher IV (term premium).
    """
    moneyness = (K - spot) / spot
    if option_type == "put":
        skew_adj = 1 + 0.4 * max(-moneyness, 0)
    else:
        skew_adj = 1 + 0.1 * max(moneyness, 0)

    term_adj = 1 + 0.15 * (T * 365 / 60)
    return base_sigma * skew_adj * term_adj


def build_mock_chain() -> list[dict]:
    """
    Build a realistic 52-row SPY option chain.

    Two expirations:
      SHORT_EXP = 7 DTE  (weekly — credit spreads, debit spreads)
      LONG_EXP  = 60 DTE (LEAPS-lite — calendar/diagonal long legs)

    Strikes: $490 to $550 in $5 increments (13 strikes)
    Calls + puts at each strike × 2 expirations = 52 rows

    Pricing: Black-Scholes with realistic put skew baked in.
    """
    spot      = 520.15
    SHORT_EXP = "2026-03-21"
    LONG_EXP  = "2026-05-15"
    base_iv   = 0.162      # 16.2% front month IV
    r         = 0.053      # risk-free rate
    strikes   = list(range(490, 555, 5))

    chain: list[dict] = []

    for exp, dte in [(SHORT_EXP, 7), (LONG_EXP, 60)]:
        T              = dte / 365.0
        iv_multiplier  = 1.18 if dte == 60 else 1.0   # contango

        for strike in strikes:
            for opt_type in ["call", "put"]:
                sigma  = _skew_iv(spot, strike, opt_type, T, base_iv) * iv_multiplier
                price, delta, gamma, theta, vega, d2 = _bs_price(
                    spot, strike, T, r, sigma, opt_type
                )

                moneyness_dist = abs(strike - spot) / spot
                spread_half    = max(0.02, min(0.15, 0.03 + moneyness_dist * 0.5))
                bid = round(max(0.01, price - spread_half), 2)
                ask = round(price + spread_half, 2)
                mid = round((bid + ask) / 2, 2)

                oi_base = int(20000 * math.exp(-5 * moneyness_dist**2))
                oi      = max(100, oi_base + int(500 * (1 if dte == 7 else 0.7)))
                vol     = int(oi * 0.4)

                chain.append({
                    "symbol":       "SPY",
                    "expiration":   exp,
                    "dte":          dte,
                    "option_type":  opt_type,
                    "strike":       float(strike),
                    "bid":          bid,
                    "ask":          ask,
                    "mid":          mid,
                    "delta":        round(delta, 4),
                    "gamma":        round(gamma, 4),
                    "theta":        round(theta, 4),
                    "vega":         round(vega, 4),
                    "iv":           round(sigma * 100, 2),
                    "open_interest": oi,
                    "volume":       vol,
                    "d2":           round(d2, 4),
                })

    return chain
