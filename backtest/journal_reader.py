"""
backtest/journal_reader.py
Analytics over the execution journal CSV.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import pandas as pd


def _path(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p


def load_journal(path: str = "logs/execution_journal.csv") -> pd.DataFrame:
    try:
        df = pd.read_csv(_path(path))
        for col in ["realized_pnl", "slippage", "variance_vs_model", "engine_score"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    except FileNotFoundError:
        return pd.DataFrame()


def summarize(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"selected":0,"entered":0,"closed":0,"skipped":0,
                "realized_pnl":0.0,"avg_slippage":0.0,"avg_variance":0.0}
    stages = df.get("event_stage", pd.Series(dtype=str)) if "event_stage" in df.columns else pd.Series(dtype=str)
    exited = df[df.get("event_stage","") == "exited"] if "event_stage" in df else pd.DataFrame()
    filled = df[df.get("event_stage","") == "entered"] if "event_stage" in df else pd.DataFrame()
    return {
        "selected": int((stages == "selected").sum()),
        "entered":  int((stages == "entered").sum()),
        "closed":   int((stages == "exited").sum()),
        "skipped":  int((df.get("status","") == "skipped").sum()) if "status" in df else 0,
        "realized_pnl":   round(float(exited["realized_pnl"].sum()), 2) if not exited.empty else 0.0,
        "avg_slippage":   round(float(filled["slippage"].mean()), 4) if not filled.empty else 0.0,
        "avg_variance":   round(float(exited["variance_vs_model"].mean()), 2) if not exited.empty else 0.0,
    }


def by_strategy(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "strategy" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("strategy", dropna=False)
        .agg(entered=("event_stage", lambda s: int((s=="entered").sum())),
             exited=("event_stage", lambda s: int((s=="exited").sum())),
             realized_pnl=("realized_pnl","sum"),
             avg_slippage=("slippage","mean"),
             avg_variance=("variance_vs_model","mean"))
        .round(3).reset_index()
        .sort_values("realized_pnl", ascending=False)
    )


def closed_trades(df: pd.DataFrame, max_rows: int = 100) -> pd.DataFrame:
    if df.empty or "event_stage" not in df.columns:
        return pd.DataFrame()
    closed = df[df["event_stage"] == "exited"].copy()
    keep = [c for c in ["timestamp","journal_id","symbol","strategy",
                         "actual_contracts","entry_fill","exit_fill",
                         "exit_reason","fees","realized_pnl","variance_vs_model","notes"]
            if c in closed.columns]
    return closed[keep].sort_values("timestamp", ascending=False).head(max_rows)
