"""
position_manager/position_tracker.py
Tracks open positions and surfaces roll/convert/exit signals.

PRIMARY SOURCE:  logs/trade_log.csv (rows where date_close is blank)
FALLBACK/OVERRIDE: data/positions/open_positions.csv (manual CSV)

Priority rule:
  1. Trade log is the default truth.
  2. Manual CSV rows supplement the trade log if they contain a trade_id
     not already in the log, OR override a log row if the CSV row has
     a matching trade_id with more recent data.
  3. If a manual CSV row has no trade_id, it is treated as supplemental.

Why this design:
  - Zero friction for existing workflow (trade log already exists)
  - Manual override available for broker-sourced position data
  - No data entry required unless you want to supplement
"""

from __future__ import annotations

import csv
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from position_manager.calendar_diagonal_engine import (
    CalDiagConfig, OpenCalDiagPosition, evaluate_position,
    decision_to_dict,
)


# ─────────────────────────────────────────────
# DEFAULTS
# ─────────────────────────────────────────────

DEFAULT_TRADE_LOG  = Path("logs/trade_log.csv")
DEFAULT_MANUAL_CSV = Path("data/positions/open_positions.csv")

_CALENDAR_DIAGONAL_TYPES = {"calendar", "diagonal"}
_CREDIT_TYPES            = {"bull_put", "bear_call"}
_DEBIT_TYPES             = {"bull_call_debit", "bear_put_debit"}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _sf(v: Any, default: float | None = None) -> float | None:
    try:
        return float(v) if v not in (None, "", "null", "—") else default
    except (TypeError, ValueError):
        return default


def _si(v: Any, default: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None, "", "null") else default
    except (TypeError, ValueError):
        return default


def _is_open(row: dict) -> bool:
    """A trade is open if date_close is blank, null, or missing."""
    dc = row.get("date_close", "")
    return not dc or str(dc).strip() in ("", "null", "None")


def _compute_dte(expiration: str) -> int:
    try:
        exp = datetime.strptime(expiration.strip(), "%Y-%m-%d").date()
        return max(0, (exp - date.today()).days)
    except (ValueError, AttributeError):
        return 0


def _credit_management_status(row: dict, spot: float | None) -> str:
    """
    Quick credit spread management signal without full scoring.
    Returns: HOLD / REVIEW_OR_ROLL / CLOSE_STOP / CLOSE_TIME
    """
    entry   = abs(_sf(row.get("entry_price", row.get("entry_debit_credit", 0))) or 0)
    target  = _sf(row.get("target_price",   row.get("target_exit_value")))
    stop    = _sf(row.get("stop_price",     row.get("stop_value")))
    short_dte = _si(row.get("short_dte"), _compute_dte(row.get("short_expiration", "")))

    from config.settings import TIME_EXIT_DTE
    if short_dte <= TIME_EXIT_DTE:
        return "CLOSE_TIME"
    if target is not None and entry <= target:
        return "CLOSE_TP"
    if stop is not None and entry >= stop:
        return "CLOSE_STOP"

    if spot and row.get("short_strike"):
        short_k = _sf(row["short_strike"])
        st_type = row.get("strategy_type", "")
        if st_type == "bull_put" and spot <= (short_k or 999):
            return "REVIEW_OR_ROLL"
        if st_type == "bear_call" and spot >= (short_k or 0):
            return "REVIEW_OR_ROLL"

    return "HOLD"


# ─────────────────────────────────────────────
# LOADERS
# ─────────────────────────────────────────────

def load_open_from_trade_log(path: Path | str | None = None) -> list[dict]:
    """
    Load all open trades from trade_log.csv.
    Returns list of row dicts where date_close is blank.
    """
    filepath = Path(path) if path else DEFAULT_TRADE_LOG
    if not filepath.exists():
        return []
    rows = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if _is_open(row):
                    rows.append(dict(row))
    except Exception:
        pass
    return rows


def load_manual_positions(path: Path | str | None = None) -> list[dict]:
    """
    Load manual override / supplement positions from CSV.
    Expected columns mirror trade_log.csv schema but only a subset is required.
    """
    filepath = Path(path) if path else DEFAULT_MANUAL_CSV
    if not filepath.exists():
        return []
    rows = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(dict(row))
    except Exception:
        pass
    return rows


def merge_positions(
    log_rows:    list[dict],
    manual_rows: list[dict],
) -> list[dict]:
    """
    Merge trade-log positions with manual CSV positions.

    Priority rules:
      - Manual row with matching trade_id OVERRIDES the log row.
      - Manual row with NO trade_id (or unknown id) is APPENDED as supplemental.
      - Trade log rows with no manual counterpart are kept as-is.
    """
    # Index log rows by trade_id
    merged: dict[str, dict] = {}
    supplemental: list[dict] = []

    for row in log_rows:
        tid = row.get("trade_id", "")
        if tid:
            merged[tid] = row

    for row in manual_rows:
        tid = row.get("trade_id", "")
        if tid and tid in merged:
            # Manual data overrides matching log row
            merged[tid] = {**merged[tid], **{k: v for k, v in row.items() if v not in ("", None)}}
        elif tid:
            merged[tid] = row
        else:
            supplemental.append(row)

    return list(merged.values()) + supplemental


# ─────────────────────────────────────────────
# POSITION TRACKER
# ─────────────────────────────────────────────

class PositionTracker:
    """
    Tracks open positions and surfaces actionable signals.

    Usage:
        tracker = PositionTracker()
        snapshot = tracker.snapshot(derived=derived_context, spot=669.03)
        for pos in snapshot["calendar_diagonal"]:
            print(pos["decision"]["action"])
        for pos in snapshot["credit_spreads"]:
            print(pos["management_status"])
    """

    def __init__(
        self,
        trade_log_path:  Path | str | None = None,
        manual_csv_path: Path | str | None = None,
        cfg:             CalDiagConfig     | None = None,
    ):
        self.trade_log_path  = Path(trade_log_path)  if trade_log_path  else DEFAULT_TRADE_LOG
        self.manual_csv_path = Path(manual_csv_path) if manual_csv_path else DEFAULT_MANUAL_CSV
        self.cfg             = cfg or CalDiagConfig()

    def load_all_open(self) -> list[dict]:
        """Load and merge all open positions from both sources."""
        log_rows    = load_open_from_trade_log(self.trade_log_path)
        manual_rows = load_manual_positions(self.manual_csv_path)
        return merge_positions(log_rows, manual_rows)

    def snapshot(
        self,
        derived: dict | None = None,
        spot:    float | None = None,
    ) -> dict[str, Any]:
        """
        Build a full position snapshot with management signals.

        Returns:
            {
                "total_open":        int,
                "calendar_diagonal": list[dict],   # with lifecycle decision
                "credit_spreads":    list[dict],   # with EGPE management status
                "debit_spreads":     list[dict],   # with simple hold/exit signal
                "other":             list[dict],   # unclassified
                "summary":           dict,         # counts + urgency rollup
            }
        """
        all_open = self.load_all_open()

        derived = derived or {}
        live_spot = spot or derived.get("spot_price") or 0.0
        vga       = derived.get("vga_environment", "mixed")
        gamma_r   = derived.get("gamma_regime", "unknown")
        iv_r      = derived.get("iv_regime", "unknown")
        em        = derived.get("expected_move", 0.0)

        cal_diag     : list[dict] = []
        credit_sp    : list[dict] = []
        debit_sp     : list[dict] = []
        other        : list[dict] = []

        for row in all_open:
            st = row.get("strategy_type", "").lower()

            if st in _CALENDAR_DIAGONAL_TYPES:
                enriched = self._eval_cal_diag(row, live_spot, vga, gamma_r, iv_r, em)
                cal_diag.append(enriched)

            elif st in _CREDIT_TYPES:
                row["management_status"] = _credit_management_status(row, live_spot)
                row["live_spot"]         = live_spot
                # Attach VH harvest fields to credit spreads too
                try:
                    from position_manager.harvest_engine import build_harvest_summary
                    from position_manager.vh_triggers import evaluate_vh_triggers
                    from engines.sentiment_pivot_engine import recommend_sentiment_pivot
                    mctx = {"spot_price": live_spot, "gamma_regime": gamma_r,
                            "iv_regime": iv_r, "vga_environment": vga,
                            "gamma_trap": None}
                    flip_dict = recommend_sentiment_pivot(row, mctx, sentiment_score=0.0)
                    flip_rec  = flip_dict.get("pivot_recommendation", "HOLD_STRUCTURE")
                    triggers  = evaluate_vh_triggers(row, mctx)
                    row["vh_triggers"] = triggers
                    harvest = build_harvest_summary(row, mctx, flip_rec)
                    row.update({
                        "net_liq":              harvest["net_liq"],
                        "harvestable_equity":   harvest["harvestable_equity"],
                        "proposed_roll_credit": harvest["proposed_roll_credit"],
                        "harvest_badge":        harvest["harvest_badge"],
                        "gamma_trap_distance":  harvest["gamma_trap_distance"],
                        "flip_recommendation":  flip_rec,
                        "sentiment_score":      0.0,
                    })
                except Exception:
                    pass
                credit_sp.append(row)

            elif st in _DEBIT_TYPES:
                # Simple time-based signal for debit spreads
                short_dte = _si(row.get("short_dte"), _compute_dte(row.get("short_expiration", "")))
                from config.settings import TIME_EXIT_DTE
                row["management_status"] = "CLOSE_TIME" if short_dte <= TIME_EXIT_DTE else "HOLD"
                row["live_spot"]         = live_spot
                debit_sp.append(row)

            else:
                other.append(row)

        # Urgency rollup
        high   = sum(1 for p in cal_diag if p.get("decision", {}).get("urgency") == "HIGH")
        medium = sum(1 for p in cal_diag if p.get("decision", {}).get("urgency") == "MEDIUM")
        close_signals = sum(1 for p in credit_sp + debit_sp
                            if "CLOSE" in p.get("management_status", ""))

        return {
            "total_open":        len(all_open),
            "calendar_diagonal": cal_diag,
            "credit_spreads":    credit_sp,
            "debit_spreads":     debit_sp,
            "other":             other,
            "summary": {
                "high_urgency":    high,
                "medium_urgency":  medium,
                "close_signals":   close_signals,
                "total_positions": len(all_open),
                "vga_environment": vga,
            },
        }

    def _eval_cal_diag(
        self,
        row:     dict,
        spot:    float,
        vga:     str,
        gamma_r: str,
        iv_r:    str,
        em:      float,
    ) -> dict:
        """Build an OpenCalDiagPosition from a trade row and evaluate it."""
        entry   = abs(_sf(row.get("entry_debit_credit", row.get("entry_price", 0))) or 0)
        current = abs(_sf(row.get("current_value",      row.get("exit_price",  entry))) or entry)
        long_k  = _sf(row.get("long_strike")) or spot
        short_k = _sf(row.get("short_strike")) or spot
        l_dte   = _si(row.get("long_dte"),  _compute_dte(row.get("long_expiration",  "")))
        s_dte   = _si(row.get("short_dte"), _compute_dte(row.get("short_expiration", "")))

        # Infer option side from direction or strategy_type
        direction = str(row.get("direction", row.get("strategy_type", ""))).lower()
        option_side = "put" if "put" in direction or "bear" in direction else "call"

        pos = OpenCalDiagPosition(
            symbol=row.get("symbol", ""),
            structure_type=row.get("strategy_type", "calendar"),
            option_side=option_side,
            long_strike=long_k,
            short_strike=short_k,
            long_dte=l_dte,
            short_dte=s_dte,
            entry_debit=entry,
            current_value=current,
            spot=spot if spot else _sf(row.get("spot_open")) or 0.0,
            expected_move=em if em else _sf(row.get("expected_move")) or 0.0,
            vga_environment=vga,
            gamma_regime=gamma_r,
            iv_regime=iv_r,
        )

        decision = evaluate_position(pos, self.cfg)
        enriched = dict(row)
        enriched["decision"]    = decision_to_dict(decision)
        enriched["live_spot"]   = spot
        enriched["live_vga"]    = vga

        # ── VH harvest layer (additive) ───────────────────────────────────────
        try:
            from position_manager.vh_triggers import evaluate_vh_triggers
            from position_manager.harvest_engine import build_harvest_summary
            from engines.sentiment_pivot_engine import recommend_sentiment_pivot

            mctx = {
                "spot_price":      spot or 0.0,
                "gamma_regime":    gamma_r,
                "iv_regime":       iv_r,
                "vga_environment": vga,
                "gamma_trap":      row.get("gamma_trap_strike"),
                "put_25d_iv":      row.get("put_25d_iv"),
                "call_25d_iv":     row.get("call_25d_iv"),
                "expected_move":   em,
            }
            sentiment = float(row.get("sentiment_score", 0.0))
            flip_dict = recommend_sentiment_pivot(enriched, mctx, sentiment_score=sentiment)
            flip_rec  = flip_dict.get("pivot_recommendation", "HOLD_STRUCTURE")

            triggers  = evaluate_vh_triggers(enriched, mctx)
            enriched["vh_triggers"] = triggers

            harvest = build_harvest_summary(enriched, mctx, flip_rec)
            enriched.update({
                "net_liq":              harvest["net_liq"],
                "harvestable_equity":   harvest["harvestable_equity"],
                "proposed_roll_credit": harvest["proposed_roll_credit"],
                "harvest_badge":        harvest["harvest_badge"],
                "gamma_trap_distance":  harvest["gamma_trap_distance"],
                "flip_recommendation":  flip_rec,
                "sentiment_score":      sentiment,
                "harvest_summary":      harvest,
            })
        except Exception:
            pass

        return enriched
