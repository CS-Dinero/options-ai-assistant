"""
backtest/trade_simulator.py
Simulates one trade's lifecycle from entry to exit.

MVP scope: vertical spreads (bull_put, bear_call, bull_call_debit, bear_put_debit)
Later: calendar, diagonal

Exit rules (in priority order):
  1. Expiration reached — always exit at expiry
  2. Target hit         — credit: value <= target  |  debit: value >= target
  3. Stop hit           — credit: value >= stop     |  debit: value <= stop
  4. Max hold period    — configurable safety valve
  5. Missing data       — graceful fallback

P/L formulas:
  Credit spread: pnl = (entry_credit - exit_value) * 100 * contracts
  Debit spread:  pnl = (exit_value - entry_debit)  * 100 * contracts
  return_pct = pnl / max_loss  (normalizes across different risk sizes)
"""

from __future__ import annotations

from datetime import datetime
from backtest.utils import compute_days_held, trading_dates_between
from backtest.schemas import EXIT_REASONS


# Strategies that collect credit at entry (value should decrease to profit)
CREDIT_STRATEGIES = ("bull_put", "bear_call")

# Strategies that pay debit at entry (value should increase to profit)
DEBIT_STRATEGIES  = ("bull_call_debit", "bear_put_debit")

# Maximum days to hold before force-closing (safety valve)
DEFAULT_MAX_HOLD_DAYS = 10


# ─────────────────────────────────────────────
# OPTION MARK LOOKUP
# ─────────────────────────────────────────────

def find_option_mark(
    chain_snapshot: list[dict],
    expiration:    str,
    option_type:   str,
    strike:        float,
) -> float | None:
    """
    Find the mid price of a specific option in a chain snapshot.
    Returns None if the contract is not found.
    """
    for row in chain_snapshot:
        if (row.get("expiration") == expiration
                and row.get("option_type") == option_type
                and abs(float(row.get("strike", 0)) - strike) < 0.01):
            mid = row.get("mid")
            return float(mid) if mid is not None else None
    return None


# ─────────────────────────────────────────────
# SPREAD PRICING
# ─────────────────────────────────────────────

def price_vertical_from_snapshot(
    trade: dict,
    chain_snapshot: list[dict],
) -> float | None:
    """
    Price a vertical spread from a daily chain snapshot.

    Credit spreads: returns net credit (positive = have sold premium)
    Debit spreads:  returns net debit  (positive = spread has value)

    Returns None if any leg can't be priced.
    """
    strategy_type = trade.get("strategy_type", "")
    short_exp     = trade.get("short_expiration", "")
    long_exp      = trade.get("long_expiration", "")

    if strategy_type == "bull_put":
        short_mid = find_option_mark(chain_snapshot, short_exp, "put",
                                     trade.get("short_strike") or 0)
        hedge_mid = find_option_mark(chain_snapshot, long_exp,  "put",
                                     trade.get("hedge_strike") or trade.get("long_strike") or 0)
        if short_mid is None or hedge_mid is None:
            return None
        return round(short_mid - hedge_mid, 4)

    elif strategy_type == "bear_call":
        short_mid = find_option_mark(chain_snapshot, short_exp, "call", trade.get("short_strike") or 0)
        hedge_mid = find_option_mark(chain_snapshot, long_exp,  "call", trade.get("hedge_strike") or trade.get("long_strike") or 0)
        if short_mid is None or hedge_mid is None:
            return None
        return round(short_mid - hedge_mid, 4)

    elif strategy_type == "bull_call_debit":
        long_mid  = find_option_mark(chain_snapshot, long_exp,  "call", trade.get("long_strike")  or 0)
        short_mid = find_option_mark(chain_snapshot, short_exp, "call", trade.get("short_strike") or 0)
        if long_mid is None or short_mid is None:
            return None
        return round(long_mid - short_mid, 4)

    elif strategy_type == "bear_put_debit":
        long_mid  = find_option_mark(chain_snapshot, long_exp,  "put", trade.get("long_strike")  or 0)
        short_mid = find_option_mark(chain_snapshot, short_exp, "put", trade.get("short_strike") or 0)
        if long_mid is None or short_mid is None:
            return None
        return round(long_mid - short_mid, 4)

    return None


def mark_trade_to_market(
    trade: dict,
    chain_snapshot: list[dict],
) -> float | None:
    """
    Return the current market value of a trade from a chain snapshot.
    Dispatches to the correct pricer by strategy_type.
    """
    strategy = trade.get("strategy_type", "")
    if strategy in ("bull_put", "bear_call", "bull_call_debit", "bear_put_debit"):
        return price_vertical_from_snapshot(trade, chain_snapshot)
    elif strategy in ("calendar", "diagonal"):
        return price_time_spread_from_snapshot(trade, chain_snapshot)
    return None


def price_time_spread_from_snapshot(
    trade: dict,
    chain_snapshot: list[dict],
) -> float | None:
    """
    Price a calendar or diagonal spread from a daily chain snapshot.

    Both are long back-month / short front-month structures:
        value = long_leg_mid - short_leg_mid
    Higher is better (debit spread logic).
    Returns None if either leg can't be priced.
    """
    direction = trade.get("direction", "")

    # Determine option type from direction
    if "call" in direction or trade.get("strategy_type") == "calendar":
        opt_type = "call"
    else:
        opt_type = "put"

    long_mid  = find_option_mark(
        chain_snapshot,
        trade.get("long_expiration", ""),
        opt_type,
        trade.get("long_strike") or 0,
    )
    short_mid = find_option_mark(
        chain_snapshot,
        trade.get("short_expiration", ""),
        opt_type,
        trade.get("short_strike") or 0,
    )

    if long_mid is None or short_mid is None:
        return None
    return round(long_mid - short_mid, 4)


# ─────────────────────────────────────────────
# EXIT LOGIC
# ─────────────────────────────────────────────

def check_exit_conditions(
    trade:         dict,
    current_value: float,
    current_date:  str,
) -> str | None:
    """
    Check all exit conditions and return the exit reason, or None to continue.

    Priority order:
      1. Expiration
      2. Target / stop
      3. Max hold
    """
    strategy_type = trade.get("strategy_type", "")
    short_exp     = trade.get("short_expiration")
    entry_date    = trade.get("entry_date", "")
    target        = trade.get("target_exit_value")
    stop          = trade.get("stop_value")

    # 1. Expiration always wins
    if short_exp and current_date >= short_exp:
        return "expiration"

    # 2. Max hold safety valve
    if entry_date:
        days = compute_days_held(entry_date, current_date)
        if days >= DEFAULT_MAX_HOLD_DAYS:
            return "max_hold"

    # 3. Target / stop
    if strategy_type in CREDIT_STRATEGIES:
        if target is not None and current_value <= target:
            return "target_hit"
        if stop is not None and current_value >= stop:
            return "stop_hit"

    elif strategy_type in DEBIT_STRATEGIES or strategy_type in ("calendar", "diagonal"):
        if target is not None and current_value >= target:
            return "target_hit"
        if stop is not None and current_value <= stop:
            return "stop_hit"

    return None


# ─────────────────────────────────────────────
# SINGLE TRADE SIMULATION
# ─────────────────────────────────────────────

def simulate_trade(
    trade:         dict,
    chain_history: dict[str, list[dict]],
    price_history: dict[str, dict],
) -> dict:
    """
    Simulate one trade from entry to exit.

    Walks forward through daily chain snapshots from entry_date,
    marks the trade each day, and exits on first condition met.

    Returns a normalized SimulatedTradeResult dict.
    """
    entry_date  = trade.get("entry_date", "")
    entry_price = trade.get("entry_debit_credit", trade.get("entry_price", 0))
    contracts   = trade.get("contracts", 1)
    max_loss    = trade.get("max_loss", 0)
    strategy    = trade.get("strategy_type", "")

    # Convert entry_price to absolute value (credit stored as positive in schema)
    entry_price = abs(entry_price)

    # Trading dates available after entry
    all_dates = sorted(d for d in chain_history.keys() if d >= entry_date)

    last_value  = entry_price
    exit_date   = None
    exit_value  = None
    exit_reason = "missing_data"

    for current_date in all_dates:
        snapshot = chain_history.get(current_date, [])
        if not snapshot:
            continue

        current_value = mark_trade_to_market(trade, snapshot)
        if current_value is None:
            continue

        last_value = current_value

        reason = check_exit_conditions(trade, current_value, current_date)
        if reason is not None:
            exit_date   = current_date
            exit_value  = current_value
            exit_reason = reason
            break

    # If never exited, use last known value
    if exit_date is None:
        if all_dates:
            exit_date   = all_dates[-1]
            exit_value  = last_value
            exit_reason = "max_hold"
        else:
            exit_date   = entry_date
            exit_value  = entry_price
            exit_reason = "missing_data"

    # P&L calculation
    if strategy in CREDIT_STRATEGIES:
        pnl = (entry_price - exit_value) * 100 * contracts
    else:
        # Debit spreads, calendars, diagonals — all pay debit to enter
        pnl = (exit_value - entry_price) * 100 * contracts

    return_pct   = round(pnl / max_loss, 4) if max_loss and max_loss > 0 else 0.0
    days_held    = compute_days_held(entry_date, exit_date)

    return {
        "trade_id":        trade.get("trade_id", ""),
        "symbol":          trade.get("symbol", ""),
        "strategy_type":   strategy,
        "direction":       trade.get("direction", ""),
        "entry_date":      entry_date,
        "exit_date":       exit_date,
        "entry_price":     round(entry_price, 4),
        "exit_price":      round(exit_value, 4) if exit_value is not None else 0.0,
        "contracts":       contracts,
        "pnl":             round(pnl, 2),
        "return_pct":      return_pct,
        "max_loss":        max_loss,
        "exit_reason":     exit_reason,
        "days_held":       days_held,
        "vga_environment": trade.get("vga_environment"),
        "iv_regime":       trade.get("iv_regime"),
        "gamma_regime":    trade.get("gamma_regime"),
        "term_structure":  trade.get("term_structure"),
        "score":           trade.get("score"),
    }
