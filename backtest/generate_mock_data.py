"""
backtest/generate_mock_data.py
Generates mock historical CSV data for Phase 4 backtest testing.

Key design: each trading day's chain includes ALL active Friday expirations
(next 4 Fridays + 1 far-dated Friday ~60 DTE). This ensures a trade entered
on day N with exp=Friday_X can find marks on days N+1, N+2, ... up to Friday_X.
"""

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

BASE   = Path(__file__).parent.parent / "data" / "historical"
SYMBOL = "SPY"
FIXED_STRIKES = list(range(490, 560, 5))


def next_friday(d: date) -> date:
    """Return the next Friday strictly after d."""
    days = 4 - d.weekday()
    if days <= 0:
        days += 7
    return d + timedelta(days=days)


def fridays_from(d: date, count: int) -> list[date]:
    """Return the next `count` Fridays on or after d+1."""
    result, f = [], next_friday(d)
    while len(result) < count:
        result.append(f)
        f += timedelta(days=7)
    return result


def bs_call(S: float, K: float, t: float, sig: float) -> float:
    from math import log, sqrt, erf
    if t <= 0:
        return max(0.0, S - K)
    d1 = (log(S / K) + 0.5 * sig**2 * t) / (sig * sqrt(t))
    N  = lambda x: 0.5 * (1 + erf(x / sqrt(2)))
    return max(0.0, S * N(d1) - K * N(d1 - sig * sqrt(t)))


def delta_call(S: float, K: float, t: float, sig: float) -> float:
    from math import log, sqrt, erf
    if t <= 0:
        return 1.0 if S > K else 0.0
    d1 = (log(S / K) + 0.5 * sig**2 * t) / (sig * sqrt(t))
    return 0.5 * (1 + erf(d1 / sqrt(2)))


def gamma_f(S: float, K: float, t: float, sig: float) -> float:
    from math import log, sqrt, exp, pi
    if t <= 0:
        return 0.0
    d1  = (log(S / K) + 0.5 * sig**2 * t) / (sig * sqrt(t))
    phi = exp(-0.5 * d1**2) / sqrt(2 * pi)
    return phi / (S * sig * sqrt(t))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def generate(num_days: int = 30) -> None:
    trading_days: list[date] = []
    d = date(2025, 3, 10)
    while len(trading_days) < num_days:
        if d.weekday() < 5:
            trading_days.append(d)
        d += timedelta(days=1)

    # ── Prices ───────────────────────────────────────────────────────────────
    spot = 520.0
    price_map: dict[str, float] = {}
    price_rows: list[dict] = []
    for day in trading_days:
        spot = max(490.0, min(555.0, spot + random.uniform(-2.5, 2.5)))
        spot = round(spot, 2)
        price_map[day.strftime("%Y-%m-%d")] = spot
        price_rows.append({"date": day.strftime("%Y-%m-%d"), "symbol": SYMBOL,
            "open": round(spot-1,2), "high": round(spot+2,2),
            "low": round(spot-2,2), "close": spot, "volume": 80_000_000})
    _write_csv(BASE / "prices" / f"{SYMBOL}_prices.csv", price_rows)

    # ── Volatility ────────────────────────────────────────────────────────────
    vol_rows: list[dict] = []
    for day in trading_days:
        fi = round(random.uniform(14, 26), 1)
        bi = round(fi + random.uniform(0.5, 3.0), 1)
        vol_rows.append({"date": day.strftime("%Y-%m-%d"), "symbol": SYMBOL,
            "atr_14": 3.8, "atr_prior": 3.5, "front_iv": fi, "back_iv": bi,
            "iv_percentile": round(random.uniform(20, 65), 1),
            "iv_min": 11.0, "iv_max": 32.0,
            "put_25d_iv": round(fi+5, 1), "call_25d_iv": round(fi-1, 1)})
    _write_csv(BASE / "volatility" / f"{SYMBOL}_volatility.csv", vol_rows)

    # ── Chains — each day includes all active expirations ─────────────────────
    chain_rows: list[dict] = []
    sig = 0.16

    for day in trading_days:
        S       = price_map[day.strftime("%Y-%m-%d")]
        day_str = day.strftime("%Y-%m-%d")

        # All active expirations for this day:
        # next 4 weekly Fridays + 1 far-dated Friday (~60 DTE)
        near_fridays = fridays_from(day, 4)
        far_friday   = next(f for f in fridays_from(day, 12) if (f - day).days >= 55)
        active_exps  = sorted(set(near_fridays + [far_friday]))

        for exp_date in active_exps:
            dte = (exp_date - day).days
            t   = dte / 365.0
            exp_str = exp_date.strftime("%Y-%m-%d")

            for K in FIXED_STRIKES:
                K_f = float(K)
                for ot in ["call", "put"]:
                    cp    = bs_call(S, K_f, t, sig)
                    dc    = delta_call(S, K_f, t, sig)
                    price = cp                       if ot == "call" else max(0.0, cp - S + K_f)
                    delta = dc                       if ot == "call" else -(1 - dc)
                    gm    = gamma_f(S, K_f, t, sig)
                    th    = -gm * S**2 * sig**2 / 2 / 365 if t > 0 else 0.0
                    ve    = S * math.sqrt(t) * gm * S * sig if t > 0 else 0.0
                    # Asymmetric OI: calls have more OI above spot, puts below
                    # This creates realistic positive GEX near ATM
                    if ot == "call":
                        oi = max(100, int(25_000 * math.exp(-0.5 * ((K_f - S) / 6)**2)))
                    else:
                        oi = max(100, int(15_000 * math.exp(-0.5 * ((K_f - S) / 6)**2)))
                    bid = max(0.01, round(price * 0.98, 2))
                    ask = max(0.02, round(price * 1.02, 2))
                    chain_rows.append({
                        "date": day_str, "symbol": SYMBOL,
                        "expiration": exp_str, "dte": dte, "option_type": ot,
                        "strike": K_f, "bid": bid, "ask": ask,
                        "mid": round((bid + ask) / 2, 2),
                        "delta": round(delta, 4), "gamma": round(gm, 5),
                        "theta": round(th, 4), "vega": round(ve, 4),
                        "iv": sig * 100, "open_interest": oi, "volume": max(10, oi // 4),
                    })

    _write_csv(BASE / "chains" / f"{SYMBOL}_chains.csv", chain_rows)

    day_strs = [d.strftime("%Y-%m-%d") for d in trading_days]
    print(f"Generated {num_days} trading days: {day_strs[0]} → {day_strs[-1]}")
    print(f"Rows: {len(price_rows)} prices | {len(vol_rows)} vol | {len(chain_rows)} chain")
    # Show expirations on first day
    first = trading_days[0]
    exps  = sorted(set(fridays_from(first, 4) + [next(f for f in fridays_from(first,12) if (f-first).days>=55)]))
    print(f"Expirations on {first}: {[e.strftime('%Y-%m-%d') for e in exps]}")


if __name__ == "__main__":
    generate(num_days=30)
