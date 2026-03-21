"""
engines/optimizer_report.py
Summarizes trading outcomes from logs and snapshots to guide:
  - which strategies outperform
  - which rejection reasons dominate
  - which roll actions recur
  - which symbols deserve more/less allocation
  - how recent snapshots are trending

build_optimizer_report() → {summary, strategy_outcomes, rejection_reasons,
                              roll_actions, symbol_allocation, snapshot_changes}
"""
from __future__ import annotations
from typing import Any
import os

import pandas as pd


def _cloud(p: str) -> str:
    from pathlib import Path
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p


def _load(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(_cloud(path))
    except FileNotFoundError:
        return pd.DataFrame()


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(dtype=float)


# ── Strategy outcomes ─────────────────────────────────────────────────────────

def strategy_outcome_report(path: str = "logs/execution_journal.csv") -> pd.DataFrame:
    df = _load(path)
    if df.empty:
        return pd.DataFrame()

    for col in ["realized_pnl","slippage","variance_vs_model"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    closed = df[df.get("event_stage","") == "exited"] if "event_stage" in df.columns else df
    if closed.empty or "strategy" not in closed.columns:
        return pd.DataFrame()

    g = (closed.groupby("strategy", dropna=False)
         .agg(closed_trades=("strategy","size"),
              total_pnl=("realized_pnl","sum"),
              avg_pnl=("realized_pnl","mean"),
              avg_slippage=("slippage","mean"),
              avg_variance=("variance_vs_model","mean"),
              wins=("realized_pnl", lambda s: int((s>0).sum())),
              losses=("realized_pnl", lambda s: int((s<0).sum())))
         .reset_index())
    g["win_rate"] = (g["wins"] / g["closed_trades"].replace(0, pd.NA)).fillna(0.0)
    g["expectancy"] = (g["total_pnl"] / g["closed_trades"].replace(0, pd.NA)).fillna(0.0)
    for c in ["total_pnl","avg_pnl","avg_slippage","avg_variance","win_rate","expectancy"]:
        g[c] = g[c].round(4)
    return g.sort_values(["expectancy","win_rate"], ascending=[False,False])


# ── Rejection reasons ─────────────────────────────────────────────────────────

def rejection_reason_report(path: str = "logs/backtest_events.csv") -> pd.DataFrame:
    df = _load(path)
    if df.empty or "event_type" not in df.columns:
        return pd.DataFrame()
    rej = df[df["event_type"] == "rejected_trade"].copy()
    if rej.empty:
        return pd.DataFrame()
    reason_col = "reject_reason" if "reject_reason" in rej.columns else "reason"
    if reason_col not in rej.columns:
        return pd.DataFrame()
    g = (rej.groupby(reason_col, dropna=False)
         .agg(count=(reason_col,"size"),
              avg_score=("score","mean"),
              avg_risk=("risk_dollars","mean"))
         .reset_index()
         .sort_values("count", ascending=False))
    for c in ["avg_score","avg_risk"]:
        if c in g.columns:
            g[c] = pd.to_numeric(g[c], errors="coerce").fillna(0.0).round(2)
    return g


# ── Roll actions ──────────────────────────────────────────────────────────────

def roll_action_report(path: str = "logs/roll_suggestions.csv") -> pd.DataFrame:
    df = _load(path)
    if df.empty or "action" not in df.columns:
        return pd.DataFrame()
    strat_col = "strategy" if "strategy" in df.columns else df.columns[0]
    g = (df.groupby([strat_col,"action"], dropna=False)
         .agg(count=("action","size"),
              high_urgency=("urgency", lambda s: int((s.astype(str).str.upper()=="HIGH").sum())))
         .reset_index()
         .sort_values(["count","high_urgency"], ascending=[False,False]))
    return g


# ── Symbol allocation recommendation ─────────────────────────────────────────

def symbol_allocation_recommendation(
    backtest_path: str = "logs/backtest_events.csv",
    journal_path:  str = "logs/execution_journal.csv",
) -> pd.DataFrame:
    bt_df  = _load(backtest_path)
    ex_df  = _load(journal_path)

    rows = {}

    # From backtest events
    if not bt_df.empty and "symbol" in bt_df.columns:
        bt_df["score"]        = pd.to_numeric(bt_df.get("score","0"), errors="coerce").fillna(0.0)
        bt_df["risk_dollars"] = pd.to_numeric(bt_df.get("risk_dollars","0"), errors="coerce").fillna(0.0)
        for sym, grp in bt_df.groupby("symbol"):
            sel = grp[grp.get("event_type","") == "selected_trade"]
            rows[sym] = {
                "symbol": sym,
                "ranked": int(len(grp[grp.get("event_type","") == "ranked_trade"])),
                "selected": int(len(sel)),
                "avg_score": round(float(grp["score"].mean()), 2),
                "total_risk": round(float(sel["risk_dollars"].sum()), 2),
                "realized_pnl": 0.0,
            }

    # From execution journal
    if not ex_df.empty and "symbol" in ex_df.columns:
        ex_df["realized_pnl"] = pd.to_numeric(ex_df.get("realized_pnl",0), errors="coerce").fillna(0.0)
        for sym, grp in ex_df.groupby("symbol"):
            r = rows.setdefault(sym, {"symbol": sym, "ranked":0, "selected":0,
                                       "avg_score":0.0, "total_risk":0.0, "realized_pnl":0.0})
            r["realized_pnl"] = round(float(grp["realized_pnl"].sum()), 2)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(list(rows.values()))
    df["allocation_score"] = (
        df["avg_score"] * 0.4 +
        df["realized_pnl"] * 0.3 +
        df["selected"] * 2.0
    ).round(2)
    df["allocation_action"] = df["allocation_score"].apply(
        lambda s: "Increase" if s >= 50 else ("Maintain" if s >= 10 else "Reduce")
    )
    return df.sort_values("allocation_score", ascending=False)


# ── Snapshot change summary ───────────────────────────────────────────────────

def snapshot_change_summary(snapshots_dir: str = "snapshots", limit: int = 5) -> pd.DataFrame:
    try:
        from engines.snapshot_manager import SnapshotManager
        mgr = SnapshotManager(base_dir=snapshots_dir)
        items = mgr.latest_snapshots(category="portfolio", n=limit)
    except Exception:
        return pd.DataFrame()

    rows = []
    for item in items:
        snap = mgr.load_snapshot(item["path"])
        p    = snap.get("payload", snap)
        meta = p.get("portfolio_meta", {})
        rows.append({
            "filename":            item["filename"],
            "saved_at":            snap.get("saved_at",""),
            "run_id":              meta.get("run_id",""),
            "selected_trades":     meta.get("selected_trades",0),
            "rejected_trades":     meta.get("rejected_trades",0),
            "portfolio_risk_used": meta.get("portfolio_risk_used",0.0),
        })
    return pd.DataFrame(rows)


# ── Master report ─────────────────────────────────────────────────────────────

def build_optimizer_report(
    *,
    backtest_events_path:   str = "logs/backtest_events.csv",
    execution_journal_path: str = "logs/execution_journal.csv",
    roll_log_path:          str = "logs/roll_suggestions.csv",
    snapshots_dir:          str = "snapshots",
) -> dict[str, Any]:
    strat_df   = strategy_outcome_report(execution_journal_path)
    reject_df  = rejection_reason_report(backtest_events_path)
    roll_df    = roll_action_report(roll_log_path)
    alloc_df   = symbol_allocation_recommendation(backtest_events_path, execution_journal_path)
    snap_df    = snapshot_change_summary(snapshots_dir)

    summary = {
        "best_strategy":             strat_df.iloc[0].to_dict() if not strat_df.empty else {},
        "dominant_rejection_reason": reject_df.iloc[0].to_dict() if not reject_df.empty else {},
        "best_symbol_candidate":     alloc_df.iloc[0].to_dict() if not alloc_df.empty else {},
        "recurring_roll_patterns":   roll_df.head(10).to_dict(orient="records") if not roll_df.empty else [],
    }

    return {
        "summary":           summary,
        "strategy_outcomes": strat_df,
        "rejection_reasons": reject_df,
        "roll_actions":      roll_df,
        "symbol_allocation": alloc_df,
        "snapshot_changes":  snap_df,
    }
