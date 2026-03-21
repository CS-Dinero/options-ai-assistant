"""
providers/mock_provider.py
Mock provider for testing — returns deterministic data without any API calls.
Useful for CI, demos, and offline development.
"""

from __future__ import annotations
from typing import Any

from providers.data_provider_interface import MarketDataProvider
from data.mock_data import load_mock_market, build_mock_chain


class MockProvider(MarketDataProvider):
    """Returns the same mock SPY data used by the test suite."""

    def provider_name(self) -> str:
        return "mock"

    def get_market(self, symbol: str) -> dict[str, Any]:
        return load_mock_market()

    def get_chain(self, symbol: str) -> list[dict[str, Any]]:
        return build_mock_chain()
