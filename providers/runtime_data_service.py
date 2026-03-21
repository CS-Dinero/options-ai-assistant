"""
providers/runtime_data_service.py
Bridge between MarketDataProvider implementations and run_portfolio_engine().

Calls provider.get_market(), provider.get_chain(), provider.get_open_positions()
and packages them into the symbol_payload format expected by portfolio_runner.

Usage:
    from providers.provider_factory import build_provider
    from providers.runtime_data_service import RuntimeDataService

    svc    = RuntimeDataService(build_provider("csv"))
    output = svc.run_portfolio(["SPY","QQQ"])

    # Or with all logging options:
    svc    = RuntimeDataService(build_provider("massive", api_key="..."))
    output = svc.run_portfolio(
        ["SPY"],
        log_backtest_events=True,
        persist_state=True,
        snapshot_history=True,
    )
"""
from __future__ import annotations

from typing import Any

from providers.data_provider_interface import MarketDataProvider


class RuntimeDataService:
    """
    Packages provider output into portfolio_runner's symbol_payload format.

    Payload format portfolio_runner.run_portfolio_engine() expects:
      {
        "symbol":         str,
        "market":         dict,          # provider.get_market() output
        "chain":          list[dict],    # provider.get_chain() output
        "open_positions": list[dict],    # provider.get_open_positions() output
      }
    """

    def __init__(self, provider: MarketDataProvider) -> None:
        self.provider = provider

    @property
    def provider_name(self) -> str:
        return self.provider.provider_name()

    def build_symbol_payload(self, symbol: str) -> dict[str, Any]:
        sym  = symbol.upper()
        return {
            "symbol":         sym,
            "market":         self.provider.get_market(sym),
            "chain":          self.provider.get_chain(sym),
            "open_positions": self.provider.get_open_positions(sym),
        }

    def build_payloads(self, symbols: list[str]) -> list[dict[str, Any]]:
        return [self.build_symbol_payload(sym) for sym in symbols]

    def run_portfolio(
        self,
        symbols: list[str],
        *,
        config_path:            str  = "config/config.yaml",
        log_backtest_events:    bool = False,
        backtest_events_path:   str  = "logs/backtest_events.csv",
        backtest_summary_path:  str  = "logs/backtest_runs.csv",
        log_execution_journal:  bool = False,
        execution_journal_path: str  = "logs/execution_journal.csv",
        log_alerts:             bool = False,
        alerts_path:            str  = "logs/alerts.csv",
        log_rolls:              bool = False,
        rolls_path:             str  = "logs/roll_suggestions.csv",
        persist_state:          bool = False,
        state_dir:              str  = "state",
        snapshot_history:       bool = False,
        snapshots_dir:          str  = "snapshots",
        run_id:                 str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch data for all symbols, then run the full portfolio engine.
        All logging/persistence flags pass through unchanged.
        """
        from engines.portfolio_runner import run_portfolio_engine

        payloads = self.build_payloads(symbols)

        return run_portfolio_engine(
            payloads,
            config_path=config_path,
            log_backtest_events=log_backtest_events,
            backtest_events_path=backtest_events_path,
            backtest_summary_path=backtest_summary_path,
            log_execution_journal=log_execution_journal,
            execution_journal_path=execution_journal_path,
            log_alerts=log_alerts,
            alerts_path=alerts_path,
            log_rolls=log_rolls,
            rolls_path=rolls_path,
            persist_state=persist_state,
            state_dir=state_dir,
            snapshot_history=snapshot_history,
            snapshots_dir=snapshots_dir,
            run_id=run_id,
        )
