"""
providers/provider_factory.py
Builds the correct provider from a string key.
"""
from __future__ import annotations
from providers.data_provider_interface import MarketDataProvider


def build_provider(provider_type: str, **kwargs) -> MarketDataProvider:
    ptype = provider_type.strip().lower()
    if ptype == "mock":
        from providers.mock_provider import MockProvider
        return MockProvider()
    if ptype == "massive":
        from providers.massive_provider import MassiveProvider
        return MassiveProvider(api_key=kwargs.get("api_key", ""),
                               symbol=kwargs.get("symbol", "SPY"))
    if ptype == "csv":
        from providers.csv_provider import CSVProvider
        return CSVProvider(
            reports_dir=kwargs.get("reports_dir", "data/reports"),
            chains_dir=kwargs.get("chains_dir", "data/chains"),
            positions_path=kwargs.get("positions_path", "data/positions/open_positions.csv"))
    if ptype == "tradier":
        from providers.tradier_provider import TradierProvider, TradierConfig
        cfg = TradierConfig(
            access_token=kwargs.get("access_token", ""),
            account_id=kwargs.get("account_id", ""),
            use_sandbox=kwargs.get("use_sandbox", True))
        return TradierProvider(cfg)
    raise ValueError(f"Unknown provider: '{provider_type}'. Valid: mock, massive, csv, tradier")
