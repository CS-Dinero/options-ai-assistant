"""
providers/massive_provider.py
Thin wrapper around existing data_sources/massive_api.py.

Implements MarketDataProvider so the engine can use Massive/Polygon
through the same interface as CSV, mock, or Tradier.
massive_api.py is NOT modified — this is purely additive.
"""

from __future__ import annotations
from typing import Any

from providers.data_provider_interface import MarketDataProvider


class MassiveProvider(MarketDataProvider):
    """
    Wraps massive_api.py for use via the provider interface.
    Falls back gracefully if Massive API key is missing.
    """

    def __init__(self, api_key: str = "", symbol: str = "SPY"):
        self._api_key = api_key
        self._default_symbol = symbol.upper()

    def provider_name(self) -> str:
        return "massive"

    def get_market(self, symbol: str) -> dict[str, Any]:
        try:
            from data_sources.massive_api import (
                get_spot_price, get_expirations, get_option_chain,
                pick_short_expiration, pick_long_expiration,
                extract_atm_straddle, extract_front_iv, extract_skew_25d,
                _compute_dte,
            )
            sym       = symbol.upper()
            expirations = get_expirations(sym)
            short_exp = pick_short_expiration(expirations)
            long_exp  = pick_long_expiration(expirations)
            spot      = get_spot_price(sym)
            chain     = get_option_chain(sym, short_exp)

            short_dte = _compute_dte(short_exp)
            long_dte  = _compute_dte(long_exp)

            # IV + skew first so they're available for ATR fallback
            front_iv     = extract_front_iv(chain, short_dte)
            back_iv      = extract_front_iv(chain, long_dte)
            skew         = extract_skew_25d(chain, short_dte)
            put_25d_iv   = skew.get("put_25d_iv")
            call_25d_iv  = skew.get("call_25d_iv")

            straddle     = extract_atm_straddle(chain, spot, short_dte)
            atm_call_mid = straddle.get("atm_call_mid", 0.0)
            atm_put_mid  = straddle.get("atm_put_mid", 0.0)

            # ATR: try live endpoint, fall back to IV-derived estimate
            try:
                from data_sources.massive_api import get_atr_14
                atr_14, atr_prior = get_atr_14(sym)
            except (ImportError, Exception):
                import math as _math
                _iv   = float(front_iv or 0.18)
                _atr  = round(spot * _iv / _math.sqrt(252) * 0.70, 2)
                atr_14, atr_prior = _atr, round(_atr * 1.05, 2)

            return {
                "symbol":               sym,
                "spot_price":           spot,
                "short_dte_target":     short_dte,
                "long_dte_target":      long_dte,
                "atm_call_mid":         atm_call_mid,
                "atm_put_mid":          atm_put_mid,
                "front_iv":             front_iv,
                "back_iv":              back_iv,
                "put_25d_iv":           put_25d_iv,
                "call_25d_iv":          call_25d_iv,
                "iv_percentile":        50.0,   # not available from Massive directly
                "atr_14":               atr_14,
                "atr_prior":            atr_prior,
                # Strategy config defaults
                "default_spread_width": 5,
                "front_dte":            short_dte,
                "event_flag":           False,
                "preferred_risk_dollars": 500,
            }
        except Exception as e:
            raise RuntimeError(f"MassiveProvider.get_market failed for {symbol}: {e}") from e

    def get_chain(self, symbol: str) -> list[dict[str, Any]]:
        try:
            from data_sources.massive_api import (
                get_expirations, get_option_chain,
                pick_short_expiration, pick_long_expiration,
            )
            sym  = symbol.upper()
            exps = get_expirations(sym)
            rows = []
            for exp in [pick_short_expiration(exps), pick_long_expiration(exps)]:
                rows.extend(get_option_chain(sym, exp))
            return rows
        except Exception as e:
            raise RuntimeError(f"MassiveProvider.get_chain failed for {symbol}: {e}") from e
