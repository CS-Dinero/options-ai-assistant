"""
providers/broker_template_provider.py
Stub template for wiring a real broker or market-data API.

Copy this file, rename it (e.g. ibkr_provider.py), and fill in
the three _fetch_* methods. Everything else stays unchanged.

The rule: return raw data here, let existing adapters normalize downstream.

Already exists for your current setup:
  providers/massive_provider.py  — Polygon.io (live options data)
  providers/tradier_provider.py  — Tradier (live chain + positions, awaiting approval)
  providers/csv_provider.py      — exported CSV files (works today)
  providers/mock_provider.py     — deterministic test data (always works)
"""
from __future__ import annotations

from typing import Any

from providers.data_provider_interface import MarketDataProvider


class BrokerTemplateProvider(MarketDataProvider):
    """
    Template — replace the three _fetch_* methods with real API calls.

    Implementation order:
      1. _fetch_spot(symbol)           — broker quote endpoint
      2. _fetch_chain_rows(symbol)     — options chain endpoint
      3. _fetch_position_rows()        — account positions endpoint
      4. get_market(symbol)            — build market dict from the above
    """

    def __init__(
        self, *,
        api_key:    str = "",
        api_secret: str = "",
        base_url:   str = "",
        account_id: str = "",
        timeout:    int = 15,
    ) -> None:
        self.api_key    = api_key
        self.api_secret = api_secret
        self.base_url   = base_url.rstrip("/")
        self.account_id = account_id
        self.timeout    = timeout

    def provider_name(self) -> str:
        return "broker_template"

    def get_market(self, symbol: str) -> dict[str, Any]:
        """
        Build the market context dict.

        Required keys the engine reads (context_builder.py):
          spot_price, short_dte_target, long_dte_target,
          front_iv, back_iv, atm_call_mid, atm_put_mid,
          put_25d_iv, call_25d_iv, iv_percentile,
          atr_14, atr_prior,
          total_gex, gamma_flip, gamma_trap_strike,
          default_spread_width, front_dte, event_flag,
          preferred_risk_dollars

        If your broker doesn't supply some of these directly,
        compute them from the chain (GEX from OI, skew from 25D quotes)
        or use None — the engine handles missing values gracefully.
        """
        spot  = self._fetch_spot(symbol)
        chain = self._fetch_chain_rows(symbol)

        # Derive ATM straddle from chain if not available from API directly
        atm_options = [r for r in chain if abs(r.get("strike", 0) - spot) < 2.0]
        atm_call    = next((r["mid"] for r in atm_options if r.get("option_type") == "call"), None)
        atm_put     = next((r["mid"] for r in atm_options if r.get("option_type") == "put"), None)

        return {
            "symbol":               symbol.upper(),
            "spot_price":           spot,
            "short_dte_target":     7,      # replace with your DTE selection logic
            "long_dte_target":      55,
            "front_iv":             None,   # replace with chain front-month IV
            "back_iv":              None,
            "atm_call_mid":         atm_call,
            "atm_put_mid":          atm_put,
            "put_25d_iv":           None,
            "call_25d_iv":          None,
            "iv_percentile":        None,   # needs historical IV series
            "atr_14":               None,   # replace with candles → ATR calc
            "atr_prior":            None,
            "total_gex":            None,   # engine computes from chain OI if None
            "gamma_flip":           None,
            "gamma_trap_strike":    None,
            "default_spread_width": 5,
            "front_dte":            7,
            "event_flag":           False,
            "preferred_risk_dollars": 500,
        }

    def get_chain(self, symbol: str) -> list[dict[str, Any]]:
        """
        Return normalized option chain rows.
        Each row must match the engine option_row schema.
        """
        return self._fetch_chain_rows(symbol)

    def get_open_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        rows = self._fetch_position_rows()
        if symbol:
            rows = [r for r in rows if str(r.get("symbol","")).upper() == symbol.upper()]
        return rows

    # ── Replace these three methods ───────────────────────────────────────────

    def _fetch_spot(self, symbol: str) -> float:
        """Return current spot price. Replace with broker quote call."""
        raise NotImplementedError("Implement _fetch_spot()")

    def _fetch_chain_rows(self, symbol: str) -> list[dict[str, Any]]:
        """
        Return chain rows. Replace with broker chain endpoint.

        Each row should have:
          symbol, expiration, dte, option_type, strike,
          bid, ask, mid, delta, gamma, theta, vega, iv,
          open_interest (or oi), volume
        """
        raise NotImplementedError("Implement _fetch_chain_rows()")

    def _fetch_position_rows(self) -> list[dict[str, Any]]:
        """
        Return open positions. Replace with broker positions endpoint.

        Each row should have:
          symbol, expiration, option_type, strike,
          quantity, dte, avg_price, mark, side
        """
        return []   # default: no positions — safe for data-only providers
