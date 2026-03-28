"""
providers/tradier_provider.py
Tradier API provider scaffold.

Implements MarketDataProvider using Tradier's documented endpoints:
  GET /v1/markets/options/chains    (chain with greeks)
  GET /v1/markets/options/expirations
  GET /v1/markets/quotes            (spot price)
  GET /v1/accounts/{id}/positions   (open positions)

Status: scaffold — authentication and parsing complete,
        report context uses heuristic gamma/IV regime.
        Next upgrade: add /v1/markets/history for ATR + real IV percentile.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any

import requests

from providers.data_provider_interface import MarketDataProvider


@dataclass
class TradierConfig:
    access_token:  str
    account_id:    str
    use_sandbox:   bool = False
    timeout_sec:   int  = 15

    @property
    def base_url(self) -> str:
        return ("https://sandbox.tradier.com/v1"
                if self.use_sandbox
                else "https://api.tradier.com/v1")


class TradierProvider(MarketDataProvider):
    """
    Live Tradier adapter.
    Set use_sandbox=False and provide production credentials to go live.
    """

    def __init__(self, config: TradierConfig):
        self.config  = config
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {config.access_token}",
            "Accept":        "application/json",
        })

    def provider_name(self) -> str:
        return "tradier"

    # ── Public interface ──────────────────────────────────────────────────────

    def get_market(self, symbol: str) -> dict[str, Any]:
        sym  = symbol.upper()
        spot = self._fetch_spot(sym)
        exps = self._fetch_expirations(sym)
        if not exps:
            return self._empty_market(sym, spot)

        chain_rows = self._fetch_chain_rows(sym, exps[0])
        return self._build_market_context(sym, spot, chain_rows, exps)

    def get_chain(self, symbol: str) -> list[dict[str, Any]]:
        sym  = symbol.upper()
        exps = self._fetch_expirations(sym)
        rows = []
        for exp in exps[:2]:   # front + back for term structure
            rows.extend(self._fetch_chain_rows(sym, exp))
        return rows

    def get_open_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        data = self._get(f"/accounts/{self.config.account_id}/positions")
        raw  = data.get("positions", {}).get("position")
        items = raw if isinstance(raw, list) else ([raw] if raw else [])
        rows = []
        for item in items:
            row = self._normalize_position(item)
            if row and (not symbol or row.get("symbol", "").upper() == symbol.upper()):
                rows.append(row)
        return rows

    # ── Tradier HTTP ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = self.config.base_url + path
        r   = self._session.get(url, params=params or {}, timeout=self.config.timeout_sec)
        r.raise_for_status()
        return r.json()

    def _fetch_spot(self, symbol: str) -> float:
        data  = self._get("/markets/quotes", {"symbols": symbol, "greeks": "false"})
        quote = data.get("quotes", {}).get("quote") or {}
        if isinstance(quote, list):
            quote = quote[0] if quote else {}
        last = self._sf(quote.get("last"))
        bid  = self._sf(quote.get("bid"))
        ask  = self._sf(quote.get("ask"))
        return last or ((bid + ask) / 2 if bid and ask else 0.0)

    def _fetch_expirations(self, symbol: str) -> list[str]:
        data = self._get("/markets/options/expirations", {"symbol": symbol})
        exps = data.get("expirations", {}).get("date") or []
        return exps if isinstance(exps, list) else [exps]

    def _fetch_chain_rows(self, symbol: str, expiration: str) -> list[dict[str, Any]]:
        data    = self._get("/markets/options/chains",
                            {"symbol": symbol, "expiration": expiration, "greeks": "true"})
        options = data.get("options", {}).get("option") or []
        if not isinstance(options, list):
            options = [options]
        rows = []
        for opt in options:
            row = self._normalize_chain_row(opt, symbol)
            if row:
                rows.append(row)
        return rows

    # ── Normalizers ───────────────────────────────────────────────────────────

    def _normalize_chain_row(self, opt: dict, symbol: str) -> dict | None:
        if not isinstance(opt, dict):
            return None
        expiration = opt.get("expiration_date", "")
        strike     = self._sf(opt.get("strike"))
        bid        = self._sf(opt.get("bid"))
        ask        = self._sf(opt.get("ask"))
        mid        = (bid + ask) / 2 if bid and ask else self._sf(opt.get("last")) or 0.0
        otype      = str(opt.get("option_type", "")).lower()
        if otype not in ("call", "put"):
            return None
        greeks = opt.get("greeks") or {}
        import pandas as _pd
        exp_dt = _pd.to_datetime(expiration, errors="coerce")
        today  = _pd.Timestamp.utcnow().normalize()
        dte    = int((exp_dt.normalize() - today).days) if _pd.notna(exp_dt) else 0
        return {
            "symbol":        symbol,
            "expiration":    expiration,
            "dte":           dte,
            "option_type":   otype,
            "strike":        strike,
            "bid":           bid or 0.0,
            "ask":           ask or 0.0,
            "mid":           mid,
            "delta":         self._sf(greeks.get("delta")),
            "gamma":         self._sf(greeks.get("gamma")),
            "theta":         self._sf(greeks.get("theta")),
            "vega":          self._sf(greeks.get("vega")),
            "iv":            self._sf(greeks.get("mid_iv")),
            "open_interest": int(opt.get("open_interest") or 0),
            "volume":        int(opt.get("volume") or 0),
        }

    def _normalize_position(self, item: dict) -> dict | None:
        if not isinstance(item, dict):
            return None
        sym = str(item.get("symbol", ""))
        qty = int(item.get("quantity") or 0)
        if not sym or qty == 0:
            return None
        parsed = self._parse_occ(sym)
        if not parsed:
            return None
        cost   = float(item.get("cost_basis") or 0)
        mark   = float(item.get("last") or 0)
        avg_px = abs(cost / qty) if qty else 0.0
        return {**parsed, "quantity": qty, "avg_price": round(avg_px, 4),
                "mark": mark, "side": "long" if qty > 0 else "short"}

    def _build_market_context(self, symbol: str, spot: float,
                               chain_rows: list, exps: list) -> dict[str, Any]:
        if not chain_rows or spot <= 0:
            return self._empty_market(symbol, spot)
        front_exp = exps[0]
        back_exp  = exps[1] if len(exps) > 1 else front_exp
        import pandas as _pd
        today    = _pd.Timestamp.utcnow().normalize()
        short_dte = max(int((_pd.to_datetime(front_exp) - today).days), 1)
        long_dte  = max(int((_pd.to_datetime(back_exp)  - today).days), 1)
        # ATM IV as expected move proxy
        front_rows = [r for r in chain_rows if r.get("expiration") == front_exp]
        atm = min(front_rows, key=lambda r: abs((r.get("strike") or 0) - spot), default={})
        atm_iv = atm.get("iv") or 0.16
        calls  = [r for r in front_rows if r["option_type"] == "call"]
        puts   = [r for r in front_rows if r["option_type"] == "put"]
        atm_c  = min(calls, key=lambda r: abs((r.get("strike") or 0) - spot), default={})
        atm_p  = min(puts,  key=lambda r: abs((r.get("strike") or 0) - spot), default={})
        # Simple skew
        put_ivs  = [r.get("iv") or 0 for r in puts  if r.get("iv")]
        call_ivs = [r.get("iv") or 0 for r in calls if r.get("iv")]
        put_25d  = sum(put_ivs)  / len(put_ivs)  * 100 if put_ivs  else None
        call_25d = sum(call_ivs) / len(call_ivs) * 100 if call_ivs else None
        return {
            "symbol":             symbol,
            "spot_price":         spot,
            "short_dte_target":   short_dte,
            "long_dte_target":    long_dte,
            "atm_call_mid":       atm_c.get("mid"),
            "atm_put_mid":        atm_p.get("mid"),
            "front_iv":           atm_iv * 100,
            "back_iv":            atm_iv * 100 * 1.02,  # rough back-month proxy
            "iv_percentile":      50.0,   # placeholder — needs historical series
            "atr_14":             3.0,    # placeholder — needs /v1/markets/history
            "atr_prior":          3.0,
            "put_25d_iv":         put_25d,
            "call_25d_iv":        call_25d,
            "preferred_risk_dollars": 500,
            # Strategy config defaults
            "default_spread_width": 5,
            "front_dte":            short_dte,
            "event_flag":           False,
        }

    def _empty_market(self, symbol: str, spot: float) -> dict:
        return {"symbol": symbol, "spot_price": spot,
                "short_dte_target": 7, "long_dte_target": 60,
                "preferred_risk_dollars": 500}

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _sf(v: Any) -> float | None:
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_occ(symbol: str) -> dict | None:
        """Parse OCC option symbol: SPY260327P00640000"""
        s = symbol.strip().upper()
        if len(s) < 15:
            return None
        suffix     = s[-15:]
        underlying = s[:-15].strip()
        if not underlying:
            return None
        try:
            exp = f"20{suffix[0:2]}-{suffix[2:4]}-{suffix[4:6]}"
            cp  = suffix[6]
            opt_type = "call" if cp == "C" else ("put" if cp == "P" else "")
            if not opt_type:
                return None
            strike = int(suffix[7:]) / 1000.0
            import pandas as _pd
            exp_dt = _pd.to_datetime(exp, errors="coerce")
            today  = _pd.Timestamp.utcnow().normalize()
            dte    = int((exp_dt.normalize() - today).days) if _pd.notna(exp_dt) else 0
            return {"symbol": underlying, "expiration": exp,
                    "option_type": opt_type, "strike": strike, "dte": dte}
        except Exception:
            return None
