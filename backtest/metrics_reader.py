"""
backtest/metrics_reader.py
Analytics layer over backtest_events.csv and backtest_runs.csv.

Provides summary stats, per-symbol breakdowns, regime analysis,
and rejection diagnostics — all as plain dicts/DataFrames that
the analytics dashboard tab can consume directly.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import os
import pandas as pd


def _safe_path(path: str) -> str:
    if os.path.exists("/mount/src"):
        return f"/tmp/options_ai_logs/{Path(path).name}"
    return path


def load_events(path: str = "logs/backtest_events.csv") -> pd.DataFrame:
    try:
        df = pd.read_csv(_safe_path(path))
        for col in ["score", "risk_dollars", "pnl_estimate", "regime_confidence"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    except FileNotFoundError:
        return pd.DataFrame()


def load_runs(path: str = "logs/backtest_runs.csv") -> pd.DataFrame:
    try:
        return pd.read_csv(_safe_path(path))
    except FileNotFoundError:
        return pd.DataFrame()


def summary_stats(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "total_events": 0, "ranked_trades": 0,
            "selected_trades": 0, "rejected_trades": 0,
            "position_actions": 0, "avg_ranked_score": 0.0,
            "avg_selected_score": 0.0, "estimated_position_pnl": 0.0,
        }
    ranked   = df[df["event_type"] == "ranked_trade"]
    selected = df[df["event_type"] == "selected_trade"]
    rejected = df[df["event_type"] == "rejected_trade"]
    actions  = df[df["event_type"] == "position_action"]
    return {
        "total_events":          len(df),
        "ranked_trades":         len(ranked),
        "selected_trades":       len(selected),
        "rejected_trades":       len(rejected),
        "position_actions":      len(actions),
        "avg_ranked_score":      round(float(ranked["score"].mean()), 2) if len(ranked) else 0.0,
        "avg_selected_score":    round(float(selected["score"].mean()), 2) if len(selected) else 0.0,
        "estimated_position_pnl": round(float(actions["pnl_estimate"].sum()), 2) if len(actions) else 0.0,
    }


def by_symbol(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby("symbol", dropna=False)
        .agg(
            total=("symbol", "size"),
            ranked=("event_type", lambda s: int((s == "ranked_trade").sum())),
            selected=("event_type", lambda s: int((s == "selected_trade").sum())),
            rejected=("event_type", lambda s: int((s == "rejected_trade").sum())),
            avg_score=("score", "mean"),
            total_risk=("risk_dollars", "sum"),
            est_pnl=("pnl_estimate", "sum"),
        )
        .round(2)
        .reset_index()
    )


def by_regime(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "vga_environment" not in df.columns:
        return pd.DataFrame()
    return (
        df[df["event_type"].isin(["ranked_trade", "selected_trade"])]
        .groupby("vga_environment", dropna=False)
        .agg(
            ranked=("event_type", lambda s: int((s == "ranked_trade").sum())),
            selected=("event_type", lambda s: int((s == "selected_trade").sum())),
            avg_score=("score", "mean"),
        )
        .round(2)
        .reset_index()
    )


def rejection_reasons(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "reject_reason" not in df.columns:
        return pd.DataFrame()
    rej = df[df["event_type"] == "rejected_trade"]
    if rej.empty:
        return pd.DataFrame()
    return (
        rej.groupby("reject_reason", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def by_strategy(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return (
        df[df["event_type"].isin(["ranked_trade", "selected_trade"])]
        .groupby("strategy", dropna=False)
        .agg(
            ranked=("event_type", lambda s: int((s == "ranked_trade").sum())),
            selected=("event_type", lambda s: int((s == "selected_trade").sum())),
            avg_score=("score", "mean"),
            total_risk=("risk_dollars", "sum"),
        )
        .round(2)
        .reset_index()
    )


def selection_rate_by_regime(df: pd.DataFrame) -> pd.DataFrame:
    """What % of ranked trades in each VGA environment got selected."""
    if df.empty or "vga_environment" not in df.columns:
        return pd.DataFrame()
    ranked   = df[df["event_type"] == "ranked_trade"].groupby("vga_environment").size()
    selected = df[df["event_type"] == "selected_trade"].groupby("vga_environment").size()
    combined = pd.DataFrame({"ranked": ranked, "selected": selected}).fillna(0)
    combined["selection_rate"] = (combined["selected"] / combined["ranked"]).round(3)
    return combined.reset_index()
