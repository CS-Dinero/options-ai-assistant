"""
providers/data_provider_interface.py
Abstract interface for all market data providers.

Any real provider (Massive, Tradier, IBKR, CSV) implements this contract.
The engine never knows which provider is underneath — it only sees normalized
market dict + option chain rows that match the live engine schema.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class MarketDataProvider(ABC):
    """
    Abstract base for all data providers.

    Implementations must return data normalized to the Options AI Assistant
    schema — same field names used by context_builder.py and strategy modules.
    """

    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        raise NotImplementedError

    @abstractmethod
    def get_market(self, symbol: str) -> dict[str, Any]:
        """
        Return normalized market dict for a symbol.

        Required keys: symbol, spot_price, short_dte_target, long_dte_target
        Optional keys: front_iv, back_iv, iv_percentile, atr_14, atr_prior,
                       put_25d_iv, call_25d_iv, atm_call_mid, atm_put_mid,
                       total_gex, gamma_flip, gamma_trap_strike
        """
        raise NotImplementedError

    @abstractmethod
    def get_chain(self, symbol: str) -> list[dict[str, Any]]:
        """
        Return normalized option chain rows for a symbol.

        Each row must match the live engine option_row schema:
        symbol, expiration, dte, option_type, strike,
        bid, ask, mid, delta, gamma, theta, vega, iv,
        open_interest, volume
        """
        raise NotImplementedError

    def get_open_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """
        Return open position rows. Optional — defaults to empty list.
        Override in broker providers (Tradier, IBKR).
        """
        return []
