"""
backtest/generate_mock_data.py
Generate synthetic historical data for backtesting.

Writes one file per trading day per symbol into:
  data/historical/prices/      — OHLCV + market context  (JSON)
  data/historical/chains/      — option chain rows        (JSON)
  data/historical/volatility/  — IV surface inputs        (JSON)
  data/historical/gamma/       — gamma context            (JSON)

Run:
    python backtest/generate_mock_data.py
"""

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
PRICES  = ROOT / "data" / "historical" / "prices"
CHAINS  = ROOT / "data" / "historical" / "chains"
VOL     = ROOT / "data" / "historical" / "volatility"
GAMMA   = ROOT / "data" / "historical" / "gamma"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _bs_price(S, K, T, r, sigma, option_type):
    if T <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return intrinsic, (1.0 if option_type == "call" else -1.0), 0.0, 0.0, 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        delta = _norm_cdf(d1)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = -_norm_cdf(-d1)
    gamma = _norm_cdf(d1) / (S * sigma * math.sqrt(T))
    theta = (-(S * _norm_cdf(d1) * sigma) / (2 * math.sqrt(T))
             - r * K * math.exp(-r * T) * _norm_cdf(d2)) / 365
    vega  = S * _norm_cdf(d1) * math.sqrt(T) / 100
    return price, delta, gamma, theta, vega


def _skew_iv(spot, K, option_type, T, base_sigma):
    moneyness = (K - spot) / spot
    if option_type == "put":
        skew_adj = 1 + 0.4 * max(-moneyness, 0)
    else:
        skew_adj = 1 + 0.1 * max(moneyness, 0)
    term_adj = 1 + 0.15 * (T * 365 / 60)
    return base_sigma * skew_adj * term_adj


def _trading_days(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # Mon–Fri
            days.append(d)
        d += timedelta(days=1)
    return days


def _next_friday(from_date: date, weeks_ahead: int = 0) -> date:
    days_to_friday = (4 - from_date.weekday()) % 7 or 7
    return from_date + timedelta(days=days_to_friday + weeks_ahead * 7)


# ── Price simulation (geometric brownian motion) ──────────────────────────────

def simulate_prices(symbol: str, start: date, end: date,
                    s0: float = 520.15, annual_vol: float = 0.16,
                    annual_drift: float = 0.08, seed: int = 42) -> dict[str, float]:
    """Return {date_str: close_price} for every trading day."""
    rng   = random.Random(seed)
    days  = _trading_days(start, end)
    dt    = 1 / 252
    price = s0
    prices = {}
    for d in days:
        z      = rng.gauss(0, 1)
        ret    = (annual_drift - 0.5 * annual_vol ** 2) * dt + annual_vol * math.sqrt(dt) * z
        price  = price * math.exp(ret)
        prices[d.isoformat()] = round(price, 2)
    return prices


# ── Chain builder ──────────────────────────────────────────────────────────────

def build_chain_for_day(symbol: str, as_of: date, spot: float,
                        front_iv: float, back_iv: float) -> list[dict]:
    short_exp = _next_friday(as_of, weeks_ahead=0)
    long_exp  = _next_friday(as_of, weeks_ahead=8)
    short_dte = max(1, (short_exp - as_of).days)
    long_dte  = (long_exp - as_of).days

    rows: list[dict] = []
    strikes = [round(spot * (1 + pct * 0.01), 0) for pct in range(-12, 13, 1)]

    for exp, dte, base_iv in [
        (short_exp, short_dte, front_iv),
        (long_exp,  long_dte,  back_iv),
    ]:
        T = dte / 365.0
        for strike in strikes:
            for opt_type in ("call", "put"):
                sigma = _skew_iv(spot, strike, opt_type, T, base_iv / 100)
                price, delta, gamma, theta, vega = _bs_price(
                    spot, strike, T, 0.053, sigma, opt_type
                )
                moneyness_dist = abs(strike - spot) / spot
                spread_half    = max(0.02, min(0.20, 0.03 + moneyness_dist * 0.5))
                bid = round(max(0.01, price - spread_half), 2)
                ask = round(price + spread_half, 2)
                oi  = max(100, int(15000 * math.exp(-4 * moneyness_dist ** 2)))
                rows.append({
                    "symbol":        symbol,
                    "expiration":    exp.isoformat(),
                    "dte":           dte,
                    "option_type":   opt_type,
                    "strike":        float(strike),
                    "bid":           bid,
                    "ask":           ask,
                    "mid":           round((bid + ask) / 2, 2),
                    "delta":         round(delta, 4),
                    "gamma":         round(gamma, 6),
                    "theta":         round(theta, 4),
                    "vega":          round(vega, 4),
                    "iv":            round(sigma * 100, 2),
                    "open_interest": oi,
                    "volume":        int(oi * 0.35),
                })
    return rows


# ── Volatility surface ─────────────────────────────────────────────────────────

def vol_surface_for_day(spot: float, front_iv: float, back_iv: float,
                        iv_pct: float) -> dict:
    slope = back_iv - front_iv
    return {
        "front_iv":       round(front_iv, 2),
        "back_iv":        round(back_iv, 2),
        "iv_percentile":  round(iv_pct, 1),
        "term_slope":     round(slope, 2),
        "put_25d_iv":     round(front_iv * 1.14, 2),
        "call_25d_iv":    round(front_iv * 0.78, 2),
        "atm_call_mid":   round(spot * front_iv / 100 * math.sqrt(7 / 365) * 0.4, 2),
        "atm_put_mid":    round(spot * front_iv / 100 * math.sqrt(7 / 365) * 0.38, 2),
    }


# ── Gamma context ──────────────────────────────────────────────────────────────

def gamma_context_for_day(spot: float, seed_offset: int = 0) -> dict:
    rng        = random.Random(42 + seed_offset)
    flip_dist  = rng.uniform(5, 20)
    trap_dist  = rng.uniform(-8, 8)
    total_gex  = rng.uniform(-2e9, 8e9)
    return {
        "gamma_flip":        round(spot + flip_dist, 1),
        "gamma_trap_strike": round(spot + trap_dist, 1),
        "total_gex":         round(total_gex, 0),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def generate(symbols: list[str], start: str, end: str):
    start_d = date.fromisoformat(start)
    end_d   = date.fromisoformat(end)
    days    = _trading_days(start_d, end_d)

    for symbol in symbols:
        print(f"Generating {symbol} ({start} → {end})  {len(days)} trading days...")

        price_path = simulate_prices(symbol, start_d, end_d)

        # IV regime: mean-reverting around 22%
        rng    = random.Random(99)
        iv_pct = 22.0
        iv_series: dict[str, float] = {}
        for d in days:
            iv_pct = max(5, min(80, iv_pct + rng.gauss(0, 2)))
            iv_series[d.isoformat()] = round(iv_pct, 1)

        for i, d in enumerate(days):
            ds      = d.isoformat()
            spot    = price_path[ds]
            iv_p    = iv_series[ds]
            front_iv = 12 + iv_p * 0.18
            back_iv  = front_iv + rng.uniform(1.5, 5.0)

            # Prices
            atr   = round(spot * 0.006 + rng.uniform(-0.3, 0.3), 2)
            market = {
                "symbol":               symbol,
                "spot_price":           spot,
                "atr_14":               max(1.0, atr),
                "atr_prior":            max(1.0, atr * rng.uniform(0.85, 1.15)),
                "iv_percentile":        iv_p,
                "front_iv":             round(front_iv, 2),
                "back_iv":              round(back_iv, 2),
                "front_dte":            7,
                "preferred_risk_dollars": 500,
                "default_spread_width":   5,
                "long_dte_target":        60,
                "short_dte_target":       7,
                "event_flag":           False,
            }
            vol_data  = vol_surface_for_day(spot, front_iv, back_iv, iv_p)
            market.update(vol_data)

            gamma_data = gamma_context_for_day(spot, seed_offset=i)
            market.update(gamma_data)

            chain = build_chain_for_day(symbol, d, spot, front_iv, back_iv)

            # Write files
            (PRICES  / f"{symbol}_{ds}.json").write_text(json.dumps(market))
            (CHAINS  / f"{symbol}_{ds}.json").write_text(json.dumps(chain))
            (VOL     / f"{symbol}_{ds}.json").write_text(json.dumps(vol_data))
            (GAMMA   / f"{symbol}_{ds}.json").write_text(json.dumps(gamma_data))

        print(f"  ✓ {len(days)} days written for {symbol}")

    print("\nDone. Run: python -c \"from backtest.run_backtest import run_backtest; "
          "r = run_backtest(['SPY'],'2025-03-10','2025-03-21'); print(r['performance'])\"")


if __name__ == "__main__":
    generate(["SPY"], "2025-03-10", "2025-03-21")
