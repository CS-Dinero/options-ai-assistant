"""
backtest/run_backtest.py
Walk-forward backtest engine.

For each trading day in [start, end]:
  1. Load historical market + chain from data/historical/
  2. Run the strategy engine to generate candidates
  3. Simulate entries on the top-ranked TRADABLE trade
  4. Advance open positions by one day — check target/stop/expiry
  5. Record PnL to trade_log.csv via TradeLogger

Returns a performance dict with win rate, avg PnL, Sharpe, etc.

Usage:
    from backtest.run_backtest import run_backtest
    result = run_backtest(['SPY'], '2025-03-10', '2025-03-21')
    print(result['performance'])
"""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from engines.context_builder import build_derived
from strategies.bear_call       import generate_bear_call_spreads
from strategies.bull_put        import generate_bull_put_spreads
from strategies.bull_call_debit import generate_bull_call_debit_spreads
from strategies.bear_put_debit  import generate_bear_put_debit_spreads
from strategies.calendar        import generate_calendar_candidates
from strategies.diagonal        import generate_diagonal_candidates
from calculator.trade_scoring   import rank_candidates
from config.settings            import SCORE_TRADABLE

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).parent.parent
PRICES = ROOT / "data" / "historical" / "prices"
CHAINS = ROOT / "data" / "historical" / "chains"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trading_days(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _load_day(symbol: str, d: date) -> tuple[Optional[dict], Optional[list]]:
    ds = d.isoformat()
    p  = PRICES / f"{symbol}_{ds}.json"
    c  = CHAINS / f"{symbol}_{ds}.json"
    if not p.exists() or not c.exists():
        return None, None
    return json.loads(p.read_text()), json.loads(c.read_text())


def _generate_candidates(market: dict, chain: list, derived: dict) -> list[dict]:
    candidates: list[dict] = []
    for fn in (
        generate_bear_call_spreads,
        generate_bull_put_spreads,
        generate_bull_call_debit_spreads,
        generate_bear_put_debit_spreads,
        generate_calendar_candidates,
        generate_diagonal_candidates,
    ):
        try:
            candidates.extend(fn(market, chain, derived))
        except Exception:
            pass
    return rank_candidates(candidates)


def _exit_pnl(trade: dict, current_spot: float, current_chain: list,
              current_date: date) -> tuple[Optional[float], str]:
    """
    Check if trade should be closed. Returns (pnl_dollars, reason) or (None, '').

    Priority: expiry → target → stop → still open
    """
    exp_str = trade["short_expiration"]
    exp_d   = date.fromisoformat(exp_str)

    # Expiry
    if current_date >= exp_d:
        # Estimate intrinsic value at expiry
        short_s   = trade["short_strike"]
        long_s    = trade["hedge_strike"] if "hedge_strike" in trade else trade.get("long_strike", short_s)
        stype     = trade["strategy_type"]
        spot      = current_spot
        if stype == "bear_call":
            intrinsic = max(0, min(spot - short_s, long_s - short_s))
        elif stype == "bull_put":
            intrinsic = max(0, min(short_s - spot, short_s - long_s))
        elif stype == "bull_call_debit":
            intrinsic = max(0, min(spot - long_s, short_s - long_s))
        elif stype == "bear_put_debit":
            intrinsic = max(0, min(long_s - spot, long_s - short_s))
        else:
            intrinsic = 0.0
        exit_val = intrinsic
        entry    = trade["entry_credit"] if trade.get("entry_credit") else -(trade.get("entry_debit") or 0)
        pnl      = round((entry - exit_val) * 100 * trade["contracts"], 2)
        return pnl, "expiry"

    # Look up current mid from chain
    short_mid = _find_mid(current_chain, trade["short_strike"],
                          "call" if trade["strategy_type"] in ("bear_call", "bull_call_debit") else "put",
                          exp_str)
    if short_mid is None:
        return None, ""

    entry = trade["entry_credit"] if trade.get("entry_credit") else -(trade.get("entry_debit") or 0)

    if trade.get("entry_credit"):           # credit spread
        current_val = short_mid
        target      = trade["target_exit_value"]
        stop        = trade["stop_value"]
        if current_val <= target:
            return round((entry - current_val) * 100 * trade["contracts"], 2), "target_hit"
        if current_val >= stop:
            return round((entry - current_val) * 100 * trade["contracts"], 2), "stop_hit"
    else:                                   # debit spread
        current_val = short_mid
        target      = trade.get("target_exit_value", entry * 2)
        stop        = trade.get("stop_value", entry * 0.5)
        if current_val >= target:
            return round((current_val - abs(entry)) * 100 * trade["contracts"], 2), "target_hit"
        if current_val <= stop:
            return round((current_val - abs(entry)) * 100 * trade["contracts"], 2), "stop_hit"

    return None, ""


def _find_mid(chain: list, strike: float, opt_type: str, exp: str) -> Optional[float]:
    for row in chain:
        if (abs(row["strike"] - strike) < 0.5
                and row["option_type"] == opt_type
                and row["expiration"] == exp):
            return row["mid"]
    return None


# ── Main backtest loop ─────────────────────────────────────────────────────────

def run_backtest(symbols: list[str], start: str, end: str,
                 max_open_trades: int = 3) -> dict:
    """
    Run walk-forward backtest.

    Args:
        symbols         — list of ticker symbols e.g. ['SPY']
        start / end     — ISO date strings  '2025-03-10' / '2025-03-21'
        max_open_trades — max concurrent positions per symbol

    Returns dict with:
        performance     — summary metrics
        daily_pnl       — {date: pnl} cumulative
        trades          — list of all closed trade records
        skipped_days    — dates with no historical data
    """
    start_d = date.fromisoformat(start)
    end_d   = date.fromisoformat(end)
    days    = _trading_days(start_d, end_d)

    closed_trades: list[dict] = []
    daily_pnl:     dict[str, float] = {}
    skipped_days:  list[str] = []
    open_positions: list[dict] = []   # active trades being tracked

    for d in days:
        ds        = d.isoformat()
        day_pnl   = 0.0
        to_close  = []

        for symbol in symbols:
            market, chain = _load_day(symbol, d)
            if market is None:
                skipped_days.append(ds)
                continue

            derived = build_derived(market, chain)

            # ── 1. Check exits on open positions ─────────────────────────────
            for pos in open_positions:
                if pos["symbol"] != symbol:
                    continue
                pnl, reason = _exit_pnl(pos, market["spot_price"], chain, d)
                if pnl is not None:
                    pos["exit_date"]  = ds
                    pos["pnl"]        = pnl
                    pos["exit_reason"]= reason
                    closed_trades.append(pos)
                    to_close.append(pos)
                    day_pnl += pnl

            # ── 2. Enter new trade if room ────────────────────────────────────
            sym_open = sum(1 for p in open_positions
                           if p["symbol"] == symbol and p not in to_close)
            if sym_open < max_open_trades:
                ranked = _generate_candidates(market, chain, derived)
                for t in ranked:
                    if t["confidence_score"] >= SCORE_TRADABLE:
                        entry = t.get("credit", 0) or -t.get("debit", 0)
                        pos = dict(t)
                        pos.update({
                            "symbol":          symbol,
                            "entry_date":      ds,
                            "entry_credit":    t.get("credit"),
                            "entry_debit":     t.get("debit"),
                            "hedge_strike":    t.get("hedge_strike") or t.get("long_strike"),
                        })
                        open_positions.append(pos)
                        break   # one trade per symbol per day

        for pos in to_close:
            open_positions.remove(pos)

        daily_pnl[ds] = round(day_pnl, 2)

    # ── Force-close any positions still open at end_d ─────────────────────────
    for pos in list(open_positions):
        market, chain = _load_day(pos["symbol"], end_d)
        if market:
            pnl, _ = _exit_pnl(pos, market["spot_price"], chain, end_d + timedelta(days=1))
            if pnl is None:
                pnl = 0.0
        else:
            pnl = 0.0
        pos["exit_date"]   = end_d.isoformat()
        pos["pnl"]         = pnl
        pos["exit_reason"] = "end_of_backtest"
        closed_trades.append(pos)
        daily_pnl[end_d.isoformat()] = daily_pnl.get(end_d.isoformat(), 0) + pnl

    # ── Performance metrics ────────────────────────────────────────────────────
    pnls        = [t["pnl"] for t in closed_trades]
    total       = len(pnls)
    winners     = [p for p in pnls if p > 0]
    losers      = [p for p in pnls if p <= 0]
    win_rate    = len(winners) / total if total else 0.0
    avg_pnl     = sum(pnls) / total if total else 0.0
    avg_win     = sum(winners) / len(winners) if winners else 0.0
    avg_loss    = sum(losers)  / len(losers)  if losers  else 0.0
    total_pnl   = sum(pnls)
    max_dd      = _max_drawdown(list(daily_pnl.values()))

    by_strategy: dict[str, dict] = {}
    for t in closed_trades:
        s = t.get("strategy_type", "unknown")
        by_strategy.setdefault(s, {"trades": 0, "pnl": 0.0, "wins": 0})
        by_strategy[s]["trades"] += 1
        by_strategy[s]["pnl"]    += t["pnl"]
        if t["pnl"] > 0:
            by_strategy[s]["wins"] += 1

    performance = {
        "total_trades": total,
        "win_rate":     round(win_rate, 3),
        "avg_pnl":      round(avg_pnl, 2),
        "avg_win":      round(avg_win, 2),
        "avg_loss":     round(avg_loss, 2),
        "total_pnl":    round(total_pnl, 2),
        "max_drawdown": round(max_dd, 2),
        "profit_factor": round(-avg_win / avg_loss, 2) if avg_loss else None,
        "by_strategy":  {
            s: {
                "trades":   v["trades"],
                "win_rate": round(v["wins"] / v["trades"], 3) if v["trades"] else 0,
                "total_pnl": round(v["pnl"], 2),
            }
            for s, v in by_strategy.items()
        },
        "skipped_days": len(skipped_days),
        "date_range":   f"{start} → {end}",
    }

    return {
        "performance": performance,
        "daily_pnl":   daily_pnl,
        "trades":      closed_trades,
        "skipped_days": skipped_days,
    }


def _max_drawdown(daily_pnls: list[float]) -> float:
    peak = cum = dd = 0.0
    for p in daily_pnls:
        cum  += p
        peak  = max(peak, cum)
        dd    = min(dd, cum - peak)
    return dd
