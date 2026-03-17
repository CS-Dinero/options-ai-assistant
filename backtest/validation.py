"""
backtest/validation.py
Phase 4 validation checks — protects research pipeline integrity.

Four validators, each returns list[tuple[str, bool]]:
  validate_contexts()        — daily context reconstruction
  validate_simulated_trades() — simulator output completeness
  validate_equity_curve()    — portfolio engine coherence
  validate_reports()         — report structure completeness

Usage:
    from backtest.validation import combine_validation_results, all_checks_pass
    results = combine_validation_results(
        validate_contexts(contexts),
        validate_simulated_trades(simulated_trades),
        validate_equity_curve(equity_curve, equity_summary),
        validate_reports(reports),
    )
    passed = all_checks_pass(results)
"""

from __future__ import annotations
from backtest.schemas import (
    REQUIRED_CONTEXT_KEYS, REQUIRED_SIM_TRADE_KEYS,
    REQUIRED_EQUITY_KEYS, REQUIRED_REPORT_KEYS, REQUIRED_GROUP_METRICS,
    EXIT_REASONS, VGA_ENVIRONMENTS,
)


def has_required_keys(obj: dict, required_keys: list[str]) -> bool:
    """Return True if all required_keys exist in obj."""
    return all(k in obj for k in required_keys)


def validate_contexts(contexts: list[dict]) -> list[tuple[str, bool]]:
    """Validate historical daily contexts from signal_builder."""
    return [
        ("Contexts built",
            len(contexts) > 0),
        ("All contexts are dicts",
            all(isinstance(c, dict) for c in contexts)),
        ("All contexts have required keys",
            all(has_required_keys(c, REQUIRED_CONTEXT_KEYS) for c in contexts)),
        ("All contexts have positive expected_move",
            all(c.get("expected_move", 0) > 0 for c in contexts)),
        ("All contexts have upper > lower EM",
            all(c.get("upper_em", 0) > c.get("lower_em", 0) for c in contexts)),
        ("All contexts have valid iv_regime",
            all(c.get("iv_regime") in ("cheap", "moderate", "elevated", "rich", None)
                for c in contexts)),
        ("All contexts have valid term_structure",
            all(c.get("term_structure") in ("contango", "flat", "backwardation", "unknown")
                for c in contexts)),
        ("All contexts have valid gamma_regime",
            all(c.get("gamma_regime") in ("positive", "negative", "neutral", "unknown")
                for c in contexts)),
        ("All contexts have valid VGA environment",
            all(c.get("vga_environment") in VGA_ENVIRONMENTS for c in contexts)),
    ]


def validate_simulated_trades(simulated_trades: list[dict]) -> list[tuple[str, bool]]:
    """Validate output from trade_simulator.simulate_trade()."""
    return [
        ("Simulated trades built",
            len(simulated_trades) > 0),
        ("All simulated trades are dicts",
            all(isinstance(t, dict) for t in simulated_trades)),
        ("All simulated trades have required keys",
            all(has_required_keys(t, REQUIRED_SIM_TRADE_KEYS) for t in simulated_trades)),
        ("All simulated trades have numeric pnl",
            all(isinstance(t.get("pnl"), (int, float)) for t in simulated_trades)),
        ("All simulated trades have numeric return_pct",
            all(isinstance(t.get("return_pct"), (int, float)) for t in simulated_trades)),
        ("All simulated trades have positive max_loss",
            all(float(t.get("max_loss", 0)) > 0 for t in simulated_trades)),
        ("All simulated trades have contracts >= 1",
            all(int(t.get("contracts", 0)) >= 1 for t in simulated_trades)),
        ("All simulated trades have non-negative days_held",
            all(int(t.get("days_held", -1)) >= 0 for t in simulated_trades)),
        ("All simulated trades have valid exit_reason",
            all(t.get("exit_reason") in EXIT_REASONS for t in simulated_trades)),
        ("All simulated trades have valid VGA environment",
            all(t.get("vga_environment") in VGA_ENVIRONMENTS + (None,)
                for t in simulated_trades)),
    ]


def validate_equity_curve(
    equity_curve: list[dict],
    equity_summary: dict,
) -> list[tuple[str, bool]]:
    """Validate portfolio_engine outputs."""
    sorted_ok = (
        all(equity_curve[i]["date"] <= equity_curve[i+1]["date"]
            for i in range(len(equity_curve) - 1))
        if len(equity_curve) > 1 else True
    )
    cashflow_sum = round(sum(r["cashflow"] for r in equity_curve), 2)
    ending       = round(equity_summary.get("ending_capital", 0), 2)
    start        = round(equity_summary.get("starting_capital", 0), 2)

    return [
        ("Equity curve built",
            len(equity_curve) > 0),
        ("All equity rows have required keys",
            all(has_required_keys(r, REQUIRED_EQUITY_KEYS) for r in equity_curve)),
        ("All equity values numeric",
            all(isinstance(r.get("equity"), (int, float)) for r in equity_curve)),
        ("All cashflows numeric",
            all(isinstance(r.get("cashflow"), (int, float)) for r in equity_curve)),
        ("Equity curve sorted by date", sorted_ok),
        ("Equity summary is dict",
            isinstance(equity_summary, dict)),
        ("Equity summary has ending_capital",
            "ending_capital" in equity_summary),
        ("Equity summary has net_profit",
            "net_profit" in equity_summary),
        ("Ending capital equals start + cashflows",
            abs((start + cashflow_sum) - ending) < 0.01),
    ]


def validate_reports(reports: dict) -> list[tuple[str, bool]]:
    """Validate report structure from reports.py."""
    by_regime = reports.get("by_regime", {})

    strat_ok = all(has_required_keys(v, REQUIRED_GROUP_METRICS)
                   for v in reports.get("by_strategy", {}).values())
    env_ok   = all(has_required_keys(v, REQUIRED_GROUP_METRICS)
                   for v in reports.get("by_environment", {}).values())
    sym_ok   = all(has_required_keys(v, REQUIRED_GROUP_METRICS)
                   for v in reports.get("by_symbol", {}).values())
    wr_ok    = all(
        0.0 <= g["win_rate"] <= 1.0
        for report in [reports.get("by_strategy", {}), reports.get("by_environment", {})]
        for g in report.values()
    )

    return [
        ("Reports built",
            isinstance(reports, dict)),
        ("Reports have required top-level keys",
            has_required_keys(reports, REQUIRED_REPORT_KEYS)),
        ("by_strategy is dict",
            isinstance(reports.get("by_strategy"), dict)),
        ("by_environment is dict",
            isinstance(reports.get("by_environment"), dict)),
        ("by_symbol is dict",
            isinstance(reports.get("by_symbol"), dict)),
        ("by_regime is dict",
            isinstance(reports.get("by_regime"), dict)),
        ("Strategy group metrics complete",    strat_ok),
        ("Environment group metrics complete", env_ok),
        ("Symbol group metrics complete",      sym_ok),
        ("All win rates in valid range",        wr_ok),
        ("Regime report has iv_regime",        "iv_regime"     in by_regime),
        ("Regime report has gamma_regime",     "gamma_regime"  in by_regime),
        ("Regime report has term_structure",   "term_structure" in by_regime),
    ]


def combine_validation_results(*groups: list[tuple[str, bool]]) -> list[tuple[str, bool]]:
    """Merge multiple validation result lists into one."""
    combined: list[tuple[str, bool]] = []
    for group in groups:
        combined.extend(group)
    return combined


def all_checks_pass(results: list[tuple[str, bool]]) -> bool:
    """Return True only if every check passed."""
    return all(ok for _, ok in results)
