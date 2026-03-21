"""
backtest/trade_logger.py
Professional-grade trade logging system.

Three CSV files:
  trade_log.csv        — one row per trade (open + close)
  position_monitor.csv — one row per trade per day (Greeks tracking)
  scan_log.csv         — every AI suggestion, taken or not

Design principles:
  - Pure stdlib — no pandas required
  - Append-only writes — never overwrites existing data
  - None-safe — missing fields write as empty string
  - Idempotent headers — writes header only if file is new
  - UUID trade IDs — collision-proof across sessions

Usage:
    from backtest.trade_logger import TradeLogger
    logger = TradeLogger()

    # Log a trade suggestion from the AI
    scan_id = logger.log_scan(candidate, market, derived, taken=False)

    # When you decide to take the trade
    trade_id = logger.open_trade(candidate, market, derived)

    # End of day — update open positions
    logger.update_position(trade_id, spot=530.0, position_value=1.45)

    # When closing
    logger.close_trade(trade_id, exit_price=0.34, pnl=98.0, reason="target_hit")
"""

import csv
import uuid
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────
# DEFAULT LOG DIRECTORY
# ─────────────────────────────────────────────

DEFAULT_LOG_DIR = Path(__file__).parent.parent / "logs"


# ─────────────────────────────────────────────
# CSV SCHEMAS
# ─────────────────────────────────────────────

TRADE_LOG_FIELDS = [
    "trade_id", "date_open", "symbol", "strategy_type", "direction",
    "short_strike", "long_strike", "short_expiration", "long_expiration",
    "short_dte", "long_dte", "contracts",
    "entry_price", "max_loss", "target_price", "stop_price",
    "spot_open", "iv_regime", "term_structure", "gamma_regime",
    "gamma_flip", "gamma_trap", "expected_move",
    "short_delta", "long_delta", "short_theta", "long_theta",
    "short_vega", "long_vega", "score", "notes",
    # Extrinsic tracking (for diagonals/calendars)
    "short_entry_price", "short_intrinsic_entry", "short_extrinsic_entry",
    # Close fields (blank at open)
    "date_close", "exit_price", "pnl", "exit_reason",
    "short_exit_price", "short_intrinsic_exit", "short_extrinsic_exit",
    "extrinsic_captured", "extrinsic_capture_pct", "theta_efficiency",
]

POSITION_MONITOR_FIELDS = [
    "date", "trade_id", "symbol",
    "spot_price", "position_value", "unrealized_pnl",
    "short_delta", "long_delta", "short_theta", "long_theta",
    "short_vega", "long_vega",
    "iv_regime", "gamma_regime", "gamma_flip", "gamma_trap",
    "days_in_trade", "dte_remaining", "notes",
]

SCAN_LOG_FIELDS = [
    "scan_id", "scan_date", "scan_time", "symbol",
    "strategy_type", "direction",
    "short_strike", "long_strike",
    "short_expiration", "long_expiration", "short_dte", "long_dte",
    "entry_price", "max_loss", "target_price", "stop_price",
    "score", "spot", "expected_move",
    "iv_regime", "term_structure", "gamma_regime", "gamma_flip", "gamma_trap",
    "short_delta", "long_delta", "short_theta", "long_theta",
    "taken_trade", "trade_id",
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _safe(value, precision: int = 4):
    """Convert any value to a CSV-safe string. None → empty string."""
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, precision)
    return value


def _compute_intrinsic(spot: float, strike: float, option_type: str) -> float:
    """Compute intrinsic value for a single option leg."""
    if "call" in option_type.lower():
        return max(0.0, spot - strike)
    else:
        return max(0.0, strike - spot)


def _generate_id(prefix: str = "T") -> str:
    """Generate a short unique ID: T-YYYYMMDD-XXXX"""
    today = date.today().strftime("%Y%m%d")
    short = str(uuid.uuid4())[:6].upper()
    return f"{prefix}-{today}-{short}"


def _write_row(filepath: Path, fields: list, row: dict) -> None:
    """Append a row to a CSV file, writing header if file is new."""
    is_new = not filepath.exists() or filepath.stat().st_size == 0
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if is_new:
            writer.writeheader()
        writer.writerow({k: _safe(row.get(k)) for k in fields})


def _update_row(filepath: Path, fields: list, id_field: str, id_value: str, updates: dict) -> bool:
    """
    Update specific columns in an existing row identified by id_field=id_value.
    Rewrites the entire file. Returns True if row was found and updated.
    """
    if not filepath.exists():
        return False

    rows = []
    found = False
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get(id_field) == id_value:
                row.update({k: _safe(v) for k, v in updates.items()})
                found = True
            rows.append(row)

    if not found:
        return False

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return True


# ─────────────────────────────────────────────
# TRADE LOGGER
# ─────────────────────────────────────────────

class TradeLogger:
    """
    Manages the three-CSV trade logging system.

    Args:
        log_dir — directory where CSV files are stored.
                  Defaults to options_assistant/logs/
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.trade_log_path    = self.log_dir / "trade_log.csv"
        self.position_mon_path = self.log_dir / "position_monitor.csv"
        self.scan_log_path     = self.log_dir / "scan_log.csv"

    # ── SCAN LOG ──────────────────────────────────────────────────────────────

    def log_scan(
        self,
        candidate: dict,
        market: dict,
        derived: dict,
        taken: bool = False,
        trade_id: Optional[str] = None,
    ) -> str:
        """
        Record an AI assistant trade suggestion to scan_log.csv.

        Call this for EVERY suggestion, whether taken or not.
        This builds the dataset needed to evaluate AI accuracy over time.

        Returns: scan_id
        """
        scan_id  = _generate_id("S")
        now      = datetime.now()

        row = {
            "scan_id":        scan_id,
            "scan_date":      now.strftime("%Y-%m-%d"),
            "scan_time":      now.strftime("%H:%M:%S"),
            "symbol":         candidate.get("symbol", market.get("symbol", "")),
            "strategy_type":  candidate.get("strategy_type", ""),
            "direction":      candidate.get("direction", ""),
            "short_strike":   candidate.get("short_strike"),
            "long_strike":    candidate.get("long_strike"),
            "short_expiration": candidate.get("short_expiration", ""),
            "long_expiration":  candidate.get("long_expiration", ""),
            "short_dte":      candidate.get("short_dte"),
            "long_dte":       candidate.get("long_dte"),
            "entry_price":    abs(candidate.get("entry_debit_credit", 0)),
            "max_loss":       candidate.get("max_loss"),
            "target_price":   candidate.get("target_exit_value"),
            "stop_price":     candidate.get("stop_value"),
            "score":          candidate.get("confidence_score"),
            "spot":           market.get("spot_price"),
            "expected_move":  derived.get("expected_move"),
            "iv_regime":      derived.get("iv_regime", ""),
            "term_structure": derived.get("term_structure", ""),
            "gamma_regime":   derived.get("gamma_regime", ""),
            "gamma_flip":     derived.get("gamma_flip"),
            "gamma_trap":     derived.get("gamma_trap"),
            "short_delta":    candidate.get("short_delta"),
            "long_delta":     candidate.get("long_delta"),
            "short_theta":    candidate.get("short_theta"),
            "long_theta":     candidate.get("long_theta"),
            "taken_trade":    "yes" if taken else "no",
            "trade_id":       trade_id or "",
        }

        _write_row(self.scan_log_path, SCAN_LOG_FIELDS, row)
        return scan_id

    # ── TRADE LOG — OPEN ──────────────────────────────────────────────────────

    def open_trade(
        self,
        candidate: dict,
        market: dict,
        derived: dict,
        notes: str = "",
    ) -> str:
        """
        Record an opened trade to trade_log.csv.

        Computes intrinsic/extrinsic for the short leg at entry.
        Returns: trade_id
        """
        trade_id = _generate_id("T")
        spot     = market.get("spot_price", 0)

        # Extrinsic tracking at entry
        short_strike     = candidate.get("short_strike") or candidate.get("hedge_strike", 0)
        short_direction  = candidate.get("strategy_type", "")
        short_entry_mid  = candidate.get("entry_debit_credit", 0)

        short_intrinsic_entry = 0.0
        short_extrinsic_entry = 0.0
        if short_strike and spot:
            opt_type = "call" if "call" in short_direction else "put"
            short_intrinsic_entry = _compute_intrinsic(spot, short_strike, opt_type)
            short_extrinsic_entry = max(0.0, abs(short_entry_mid) - short_intrinsic_entry)

        row = {
            "trade_id":        trade_id,
            "date_open":       date.today().isoformat(),
            "symbol":          candidate.get("symbol", market.get("symbol", "")),
            "strategy_type":   candidate.get("strategy_type", ""),
            "direction":       candidate.get("direction", ""),
            "short_strike":    candidate.get("short_strike") or candidate.get("hedge_strike"),
            "long_strike":     candidate.get("long_strike"),
            "short_expiration": candidate.get("short_expiration", ""),
            "long_expiration":  candidate.get("long_expiration", ""),
            "short_dte":       candidate.get("short_dte"),
            "long_dte":        candidate.get("long_dte"),
            "contracts":       candidate.get("contracts", 1),
            "entry_price":     abs(candidate.get("entry_debit_credit", 0)),
            "max_loss":        candidate.get("max_loss"),
            "target_price":    candidate.get("target_exit_value"),
            "stop_price":      candidate.get("stop_value"),
            "spot_open":       spot,
            "iv_regime":       derived.get("iv_regime", ""),
            "term_structure":  derived.get("term_structure", ""),
            "gamma_regime":    derived.get("gamma_regime", ""),
            "gamma_flip":      derived.get("gamma_flip"),
            "gamma_trap":      derived.get("gamma_trap"),
            "expected_move":   derived.get("expected_move"),
            "short_delta":     candidate.get("short_delta"),
            "long_delta":      candidate.get("long_delta"),
            "short_theta":     candidate.get("short_theta"),
            "long_theta":      candidate.get("long_theta"),
            "short_vega":      candidate.get("short_vega"),
            "long_vega":       candidate.get("long_vega"),
            "score":           candidate.get("confidence_score"),
            "notes":           notes or candidate.get("notes", ""),
            "short_entry_price":     abs(short_entry_mid),
            "short_intrinsic_entry": short_intrinsic_entry,
            "short_extrinsic_entry": short_extrinsic_entry,
        }

        _write_row(self.trade_log_path, TRADE_LOG_FIELDS, row)
        return trade_id

    # ── TRADE LOG — CLOSE ─────────────────────────────────────────────────────

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        pnl: float,
        reason: str,
        spot_at_close: float = 0.0,
        short_exit_price: float = 0.0,
    ) -> bool:
        """
        Mark a trade as closed in trade_log.csv.

        Computes extrinsic captured and theta efficiency.
        Returns True if trade_id was found.
        """
        # Read entry extrinsic from existing row
        short_intrinsic_exit = 0.0
        short_extrinsic_exit = 0.0
        extrinsic_captured   = None
        extrinsic_capture_pct = None
        theta_efficiency     = None

        if not self.trade_log_path.exists():
            return False

        entry_row = None
        with open(self.trade_log_path, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("trade_id") == trade_id:
                    entry_row = row
                    break

        if entry_row and short_exit_price > 0 and spot_at_close > 0:
            short_strike = float(entry_row.get("short_strike") or 0)
            strategy     = entry_row.get("strategy_type", "")
            opt_type     = "call" if "call" in strategy else "put"
            short_intrinsic_exit = _compute_intrinsic(spot_at_close, short_strike, opt_type)
            short_extrinsic_exit = max(0.0, short_exit_price - short_intrinsic_exit)

            entry_ext = float(entry_row.get("short_extrinsic_entry") or 0)
            if entry_ext > 0:
                extrinsic_captured    = round(entry_ext - short_extrinsic_exit, 4)
                extrinsic_capture_pct = round(extrinsic_captured / entry_ext, 4)

            # Theta efficiency: actual capture vs theoretical theta decay
            short_theta = float(entry_row.get("short_theta") or 0)
            short_dte   = float(entry_row.get("short_dte") or 0)
            if short_theta and short_dte and extrinsic_captured is not None:
                expected_theta_decay = abs(short_theta) * short_dte
                if expected_theta_decay > 0:
                    theta_efficiency = round(extrinsic_captured / expected_theta_decay, 4)

        updates = {
            "date_close":            date.today().isoformat(),
            "exit_price":            exit_price,
            "pnl":                   pnl,
            "exit_reason":           reason,
            "short_exit_price":      short_exit_price if short_exit_price else "",
            "short_intrinsic_exit":  short_intrinsic_exit if short_exit_price else "",
            "short_extrinsic_exit":  short_extrinsic_exit if short_exit_price else "",
            "extrinsic_captured":    extrinsic_captured,
            "extrinsic_capture_pct": extrinsic_capture_pct,
            "theta_efficiency":      theta_efficiency,
        }

        return _update_row(
            self.trade_log_path, TRADE_LOG_FIELDS, "trade_id", trade_id, updates
        )

    # ── POSITION MONITOR ──────────────────────────────────────────────────────

    def update_position(
        self,
        trade_id: str,
        spot: float,
        position_value: float,
        unrealized_pnl: float = 0.0,
        short_delta: float = None,
        long_delta: float = None,
        short_theta: float = None,
        long_theta: float = None,
        short_vega: float = None,
        long_vega: float = None,
        iv_regime: str = "",
        gamma_regime: str = "",
        gamma_flip: float = None,
        gamma_trap: float = None,
        dte_remaining: int = None,
        notes: str = "",
    ) -> None:
        """
        Append a daily position snapshot to position_monitor.csv.

        Call this once per trading day for each open position.
        """
        # Calculate days in trade from trade_log
        days_in_trade = None
        if self.trade_log_path.exists():
            with open(self.trade_log_path, "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("trade_id") == trade_id:
                        try:
                            open_date   = datetime.strptime(row["date_open"], "%Y-%m-%d").date()
                            days_in_trade = (date.today() - open_date).days
                        except (ValueError, KeyError):
                            pass
                        break

        row = {
            "date":           date.today().isoformat(),
            "trade_id":       trade_id,
            "symbol":         "",  # can be filled from trade_log
            "spot_price":     spot,
            "position_value": position_value,
            "unrealized_pnl": unrealized_pnl,
            "short_delta":    short_delta,
            "long_delta":     long_delta,
            "short_theta":    short_theta,
            "long_theta":     long_theta,
            "short_vega":     short_vega,
            "long_vega":      long_vega,
            "iv_regime":      iv_regime,
            "gamma_regime":   gamma_regime,
            "gamma_flip":     gamma_flip,
            "gamma_trap":     gamma_trap,
            "days_in_trade":  days_in_trade,
            "dte_remaining":  dte_remaining,
            "notes":          notes,
        }

        _write_row(self.position_mon_path, POSITION_MONITOR_FIELDS, row)

    # ── READ HELPERS ──────────────────────────────────────────────────────────

    def get_open_trades(self) -> list[dict]:
        """Return all trades without a date_close (still open)."""
        if not self.trade_log_path.exists():
            return []
        with open(self.trade_log_path, "r", newline="", encoding="utf-8") as f:
            return [r for r in csv.DictReader(f) if not r.get("date_close")]

    def get_all_trades(self) -> list[dict]:
        """Return all trades (open and closed)."""
        if not self.trade_log_path.exists():
            return []
        with open(self.trade_log_path, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def get_scan_history(self, symbol: str = None, last_n: int = 50) -> list[dict]:
        """Return recent scan suggestions, optionally filtered by symbol."""
        if not self.scan_log_path.exists():
            return []
        with open(self.scan_log_path, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if symbol:
            rows = [r for r in rows if r.get("symbol", "").upper() == symbol.upper()]
        return rows[-last_n:]

    def summary_stats(self) -> dict:
        """
        Compute basic performance stats from closed trades.
        Returns dict with win_rate, avg_pnl, total_trades, by_strategy.
        """
        trades = [t for t in self.get_all_trades() if t.get("date_close")]
        if not trades:
            return {"total_trades": 0, "win_rate": None, "avg_pnl": None, "by_strategy": {}}

        wins = [t for t in trades if float(t.get("pnl") or 0) > 0]
        pnls = [float(t.get("pnl") or 0) for t in trades]

        by_strategy: dict[str, dict] = {}
        for t in trades:
            st  = t.get("strategy_type", "unknown")
            pnl = float(t.get("pnl") or 0)
            if st not in by_strategy:
                by_strategy[st] = {"trades": 0, "wins": 0, "total_pnl": 0.0}
            by_strategy[st]["trades"]    += 1
            by_strategy[st]["total_pnl"] += pnl
            if pnl > 0:
                by_strategy[st]["wins"] += 1

        for st, d in by_strategy.items():
            d["win_rate"] = round(d["wins"] / d["trades"], 4) if d["trades"] else None
            d["avg_pnl"]  = round(d["total_pnl"] / d["trades"], 2) if d["trades"] else None

        return {
            "total_trades": len(trades),
            "win_rate":     round(len(wins) / len(trades), 4),
            "avg_pnl":      round(sum(pnls) / len(pnls), 2),
            "by_strategy":  by_strategy,
        }

    # ── CSV EXPORT ────────────────────────────────────────────────────────────

    def export_candidate_as_scan_row(self, candidate: dict, market: dict, derived: dict) -> dict:
        """
        Return a dict representing one scan row — for dashboard export buttons.
        Does NOT write to disk. Caller decides whether to log_scan().
        """
        return {
            "scan_date":     date.today().isoformat(),
            "symbol":        candidate.get("symbol", ""),
            "strategy_type": candidate.get("strategy_type", ""),
            "direction":     candidate.get("direction", ""),
            "short_strike":  candidate.get("short_strike") or candidate.get("hedge_strike", ""),
            "long_strike":   candidate.get("long_strike", ""),
            "short_exp":     candidate.get("short_expiration", ""),
            "long_exp":      candidate.get("long_expiration", ""),
            "entry_price":   abs(candidate.get("entry_debit_credit", 0)),
            "max_loss":      candidate.get("max_loss", ""),
            "target":        candidate.get("target_exit_value", ""),
            "stop":          candidate.get("stop_value", ""),
            "score":         candidate.get("confidence_score", ""),
            "spot":          market.get("spot_price", ""),
            "iv_regime":     derived.get("iv_regime", ""),
            "gamma_regime":  derived.get("gamma_regime", ""),
            "expected_move": derived.get("expected_move", ""),
        }
