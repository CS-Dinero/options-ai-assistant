"""
providers/csv_provider.py
File-based provider for offline backtesting and exported broker data.
Reads from data/reports/, data/chains/, data/positions/.
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

from providers.data_provider_interface import MarketDataProvider


class CSVProvider(MarketDataProvider):
    """
    Loads market context and option chain from exported CSV files.
    Expected file layout:
      data/reports/{SYMBOL}_report.csv   — one-row market context
      data/chains/{SYMBOL}_chain.csv     — option chain rows
      data/positions/open_positions.csv  — open positions (optional)
    """

    def __init__(
        self,
        reports_dir:    str = "data/reports",
        chains_dir:     str = "data/chains",
        positions_path: str = "data/positions/open_positions.csv",
    ):
        self.reports_dir    = Path(reports_dir)
        self.chains_dir     = Path(chains_dir)
        self.positions_path = Path(positions_path)

    def provider_name(self) -> str:
        return "csv"

    def _safe_float(self, v: Any, default: float | None = None) -> float | None:
        try:
            return float(v) if v not in (None, "", "null") else default
        except (TypeError, ValueError):
            return default

    def get_market(self, symbol: str) -> dict[str, Any]:
        path = self.reports_dir / f"{symbol.upper()}_report.csv"
        with open(path, newline="", encoding="utf-8") as f:
            row = next(csv.DictReader(f), {})
        sf = self._safe_float
        return {
            "symbol":              symbol.upper(),
            "spot_price":          sf(row.get("spot")) or 0.0,
            "short_dte_target":    int(float(row.get("short_dte_target", 7))),
            "long_dte_target":     int(float(row.get("long_dte_target", 60))),
            "front_iv":            sf(row.get("front_iv")),
            "back_iv":             sf(row.get("back_iv")),
            "iv_percentile":       sf(row.get("iv_percentile")),
            "atr_14":              sf(row.get("atr_14")),
            "atr_prior":           sf(row.get("atr_prior")),
            "put_25d_iv":          sf(row.get("put_25d_iv")),
            "call_25d_iv":         sf(row.get("call_25d_iv")),
            # GEX / gamma fields
            "total_gex":           sf(row.get("total_gex")),
            "gamma_flip":          sf(row.get("gamma_flip")),
            "gamma_trap_strike":   sf(row.get("gamma_trap_strike")),
            # ATM straddle for expected move
            "atm_call_mid":        sf(row.get("atm_call_mid")),
            "atm_put_mid":         sf(row.get("atm_put_mid")),
            "preferred_risk_dollars": 500,
            # Strategy config defaults (can be overridden in report CSV if needed)
            "default_spread_width": int(float(row.get("default_spread_width", 5))),
            "front_dte":            int(float(row.get("front_dte", row.get("short_dte_target", 7)))),
            "event_flag":           row.get("event_flag", "false").lower() == "true"
                                    if isinstance(row.get("event_flag"), str)
                                    else bool(row.get("event_flag", False)),
        }

    def get_chain(self, symbol: str) -> list[dict[str, Any]]:
        path = self.chains_dir / f"{symbol.upper()}_chain.csv"
        rows = []
        sf = self._safe_float
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "symbol":        symbol.upper(),
                    "expiration":    r.get("expiration", ""),
                    "dte":           int(float(r.get("dte", 0))),
                    "option_type":   r.get("option_type", "").lower(),
                    "strike":        sf(r.get("strike")) or 0.0,
                    "bid":           sf(r.get("bid")) or 0.0,
                    "ask":           sf(r.get("ask")) or 0.0,
                    "mid":           sf(r.get("mid")) or sf(r.get("mark")) or 0.0,
                    "delta":         sf(r.get("delta")),
                    "gamma":         sf(r.get("gamma")),
                    "theta":         sf(r.get("theta")),
                    "vega":          sf(r.get("vega")),
                    "iv":            sf(r.get("iv")),
                    "open_interest": int(float(r.get("oi", r.get("open_interest", 0)) or 0)),
                    "volume":        int(float(r.get("volume", 0) or 0)),
                })
        return rows

    def get_open_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        if not self.positions_path.exists():
            return []
        rows = []
        with open(self.positions_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if symbol and r.get("symbol", "").upper() != symbol.upper():
                    continue
                rows.append(dict(r))
        return rows
