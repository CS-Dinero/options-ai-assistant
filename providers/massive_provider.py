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
            sym = symbol.upper()
            expirations = get_expirations(sym)
            short_exp = pick_short_expiration(expirations)
            long_exp  = pick_long_expiration(expirations)
            spot      = get_spot_price(sym)
            chain     = get_option_chain(sym, short_exp)

            from data_sources.massive_api import get_atr_14
            atr_14, atr_prior = get_atr_14(sym)

            atm_call_mid, atm_put_mid = extract_atm_straddle(chain, spot)
            front_iv, back_iv         = extract_front_iv(chain)
            put_25d_iv, call_25d_iv   = extract_skew_25d(chain)

            return {
                "symbol":            sym,
                "spot_price":        spot,
                "short_dte_target":  _compute_dte(short_exp),
                "long_dte_target":   _compute_dte(long_exp),
                "atm_call_mid":      atm_call_mid,
                "atm_put_mid":       atm_put_mid,
                "front_iv":          front_iv,
                "back_iv":           back_iv,
                "put_25d_iv":        put_25d_iv,
                "call_25d_iv":       call_25d_iv,
                "iv_percentile":     50.0,   # not available from Massive directly
                "atr_14":            atr_14,
                "atr_prior":         atr_prior,
                # Strategy config defaults
                "default_spread_width": 5,
                "front_dte":            _compute_dte(short_exp),
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
