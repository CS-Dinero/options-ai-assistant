"""
engines/parameter_tuner.py
Analyzes log behavior and suggests config parameter adjustments.

Reads:
  - logs/backtest_events.csv  (selection/rejection patterns)
  - logs/execution_journal.csv (closed-trade outcomes)
  - logs/roll_suggestions.csv  (roll pressure patterns)
  - config/config.yaml         (current thresholds)

Produces TuningReport with TuningSuggestion list — each with
parameter path, current/suggested value, direction, confidence, and evidence.

None of these suggestions are applied automatically.
They feed config_patcher.py for operator-reviewed application.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def _cloud(p: str) -> str:
    return f"/tmp/options_ai_logs/{Path(p).name}" if os.path.exists("/mount/src") else p


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(str(v).replace("$","").replace(",","").strip()) if v not in (None,"","—") else d
    except Exception:
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None,"") else d
    except Exception:
        return d


def _load_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(_cloud(path))
    except FileNotFoundError:
        return pd.DataFrame()


def _load_config(config_path: str) -> dict[str, Any]:
    for p in [config_path, str(Path(__file__).parent.parent / "config" / "config.yaml")]:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            continue
    return {}


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class TuningSuggestion:
    parameter:       str
    current_value:   Any
    suggested_value: Any
    direction:       str
    confidence:      float
    rationale:       str
    evidence:        dict[str, Any] = field(default_factory=dict)


@dataclass
class TuningReport:
    summary:     dict[str, Any]
    suggestions: list[TuningSuggestion]

    def to_dict(self) -> dict[str, Any]:
        return {"summary": self.summary,
                "suggestions": [asdict(s) for s in self.suggestions]}


# ─────────────────────────────────────────────
# SIGNAL EXTRACTORS
# ─────────────────────────────────────────────

def _sel_rej_ratio(df: pd.DataFrame) -> float:
    if df.empty or "event_type" not in df.columns:
        return 0.0
    sel = int((df["event_type"] == "selected_trade").sum())
    rej = int((df["event_type"] == "rejected_trade").sum())
    return sel / rej if rej else float(sel)


def _rejection_counts(df: pd.DataFrame) -> dict[str, int]:
    if df.empty or "event_type" not in df.columns:
        return {}
    rej = df[df["event_type"] == "rejected_trade"]
    col = "reject_reason" if "reject_reason" in rej.columns else "reason"
    if col not in rej.columns:
        return {}
    return {str(k): int(v) for k, v in rej[col].fillna("UNKNOWN").value_counts().items()}


def _roll_counts(path: str) -> dict[str, int]:
    df = _load_csv(path)
    if df.empty or "action" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df["action"].fillna("UNKNOWN").value_counts().items()}


def _strategy_stats(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    for col in ["realized_pnl","slippage","variance_vs_model"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "event_stage" in df.columns:
        df = df[df["event_stage"] == "exited"]
    if df.empty or "strategy" not in df.columns:
        return pd.DataFrame()
    g = (df.groupby("strategy", dropna=False)
         .agg(n=("strategy","size"),
              total_pnl=("realized_pnl","sum"),
              avg_pnl=("realized_pnl","mean"),
              wins=("realized_pnl", lambda s: int((s>0).sum())))
         .reset_index())
    g["win_rate"] = (g["wins"] / g["n"].replace(0, pd.NA)).fillna(0.0)
    return g


def _symbol_concentration(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "symbol" not in df.columns or "event_type" not in df.columns:
        return pd.DataFrame()
    sel = df[df["event_type"] == "selected_trade"]
    if sel.empty:
        return pd.DataFrame()
    g = sel.groupby("symbol").size().reset_index(name="count")
    total = g["count"].sum()
    g["share"] = g["count"] / total if total else 0.0
    return g.sort_values("count", ascending=False)


# ─────────────────────────────────────────────
# TUNER
# ─────────────────────────────────────────────

def tune_parameters(
    *,
    config_path:            str = "config/config.yaml",
    backtest_events_path:   str = "logs/backtest_events.csv",
    execution_journal_path: str = "logs/execution_journal.csv",
    roll_log_path:          str = "logs/roll_suggestions.csv",
) -> TuningReport:
    cfg      = _load_config(config_path)
    bt_df    = _load_csv(backtest_events_path)
    ex_df    = _load_csv(execution_journal_path)

    filters    = cfg.get("filters", {})
    risk       = cfg.get("risk", {})
    credit_cfg = cfg.get("credit_spreads", {})

    credit_thresh    = _sf(filters.get("credit_score_threshold", 75))
    calendar_thresh  = _sf(filters.get("calendar_score_threshold", 72))
    cal_reserve      = _sf(risk.get("reserve_for_calendars_pct", 0.25))
    max_per_sym      = _si(risk.get("max_trades_per_symbol", 2))
    delta_min        = _sf(credit_cfg.get("short_delta_min", 0.15))
    delta_max        = _sf(credit_cfg.get("short_delta_max", 0.20))

    ratio    = _sel_rej_ratio(bt_df)
    rej      = _rejection_counts(bt_df)
    rolls    = _roll_counts(roll_log_path)
    strats   = _strategy_stats(ex_df)
    sym_conc = _symbol_concentration(bt_df)

    suggestions: list[TuningSuggestion] = []

    # 1 — Credit threshold
    if ratio < 0.15:
        suggestions.append(TuningSuggestion(
            parameter="filters.credit_score_threshold",
            current_value=credit_thresh,
            suggested_value=min(credit_thresh + 3, 90),
            direction="raise", confidence=0.72,
            rationale="Low selection ratio — too many candidates rejected downstream. Tighten threshold.",
            evidence={"selected_rejected_ratio": round(ratio, 2)},
        ))
    elif ratio > 0.65:
        suggestions.append(TuningSuggestion(
            parameter="filters.credit_score_threshold",
            current_value=credit_thresh,
            suggested_value=max(credit_thresh - 2, 65),
            direction="lower", confidence=0.62,
            rationale="High selection ratio — modestly lower threshold for more diversity.",
            evidence={"selected_rejected_ratio": round(ratio, 2)},
        ))

    # 2 — Calendar reserve
    if not strats.empty:
        cal_row    = strats[strats["strategy"].isin(["calendar","atm_calendar"])]
        credit_row = strats[strats["strategy"].isin(["bull_put","bear_call","bull_put_credit","bear_call_credit"])]
        cal_pnl    = float(cal_row["total_pnl"].sum()) if not cal_row.empty else 0.0
        cred_pnl   = float(credit_row["total_pnl"].sum()) if not credit_row.empty else 0.0
        cal_n      = int(cal_row["n"].sum()) if not cal_row.empty else 0

        if cal_n >= 3 and cal_pnl < 0 and cal_reserve > 0.10:
            suggestions.append(TuningSuggestion(
                parameter="risk.reserve_for_calendars_pct",
                current_value=cal_reserve,
                suggested_value=round(max(cal_reserve - 0.05, 0.10), 2),
                direction="lower", confidence=0.78,
                rationale="Calendars underperforming — reduce reserve.",
                evidence={"calendar_pnl": round(cal_pnl,2), "credit_pnl": round(cred_pnl,2), "n": cal_n},
            ))
        elif cal_n >= 3 and cal_pnl > cred_pnl * 0.35 and cal_reserve < 0.35:
            suggestions.append(TuningSuggestion(
                parameter="risk.reserve_for_calendars_pct",
                current_value=cal_reserve,
                suggested_value=round(min(cal_reserve + 0.05, 0.35), 2),
                direction="raise", confidence=0.63,
                rationale="Calendars contributing well — increase reserve slightly.",
                evidence={"calendar_pnl": round(cal_pnl,2), "credit_pnl": round(cred_pnl,2), "n": cal_n},
            ))

    # 3 — Delta band (roll pressure signal)
    roll_pressure = rolls.get("ROLL_OUT_AND_AWAY",0) + rolls.get("ROLL_UP",0) + rolls.get("ROLL_DOWN",0)
    if roll_pressure >= 10 and delta_max > 0.18:
        suggestions.append(TuningSuggestion(
            parameter="credit_spreads.short_delta_max",
            current_value=delta_max,
            suggested_value=round(max(delta_max - 0.02, delta_min + 0.01), 2),
            direction="tighten", confidence=0.74,
            rationale="Frequent roll pressure — short strikes may be too aggressive.",
            evidence={"roll_pressure_count": roll_pressure},
        ))

    budget_rej = rej.get("exceeds_per_trade_budget", 0)
    if budget_rej >= 8 and delta_min < 0.18:
        suggestions.append(TuningSuggestion(
            parameter="credit_spreads.short_delta_min",
            current_value=delta_min,
            suggested_value=round(min(delta_min + 0.01, delta_max - 0.01), 2),
            direction="raise", confidence=0.58,
            rationale="Repeated budget rejects — higher delta floor improves credit efficiency.",
            evidence={"budget_rejects": budget_rej},
        ))

    # 4 — Max trades per symbol
    if not sym_conc.empty:
        top_share = float(sym_conc.iloc[0]["share"])
        top_sym   = str(sym_conc.iloc[0]["symbol"])
        if top_share > 0.65 and max_per_sym > 1:
            suggestions.append(TuningSuggestion(
                parameter="risk.max_trades_per_symbol",
                current_value=max_per_sym,
                suggested_value=max(max_per_sym - 1, 1),
                direction="lower", confidence=0.67,
                rationale="Concentration too high in one symbol — reduce per-symbol cap.",
                evidence={"top_symbol": top_sym, "share": round(top_share,2)},
            ))
        elif top_share < 0.30 and max_per_sym < 3:
            suggestions.append(TuningSuggestion(
                parameter="risk.max_trades_per_symbol",
                current_value=max_per_sym,
                suggested_value=min(max_per_sym + 1, 3),
                direction="raise", confidence=0.51,
                rationale="Good diversification — allow slightly more per-symbol trades.",
                evidence={"top_symbol": top_sym, "share": round(top_share,2)},
            ))

    # 5 — Calendar threshold
    if not strats.empty:
        cal_row = strats[strats["strategy"].isin(["calendar","atm_calendar"])]
        if not cal_row.empty:
            cal_wr  = float(cal_row["win_rate"].iloc[0])
            cal_avg = float(cal_row["avg_pnl"].iloc[0])
            if cal_wr < 0.45 and calendar_thresh < 82:
                suggestions.append(TuningSuggestion(
                    parameter="filters.calendar_score_threshold",
                    current_value=calendar_thresh,
                    suggested_value=min(calendar_thresh + 3, 85),
                    direction="raise", confidence=0.76,
                    rationale="Calendar win rate weak — require higher score before allocation.",
                    evidence={"win_rate": round(cal_wr,2), "avg_pnl": round(cal_avg,2)},
                ))
            elif cal_wr > 0.60 and cal_avg > 0 and calendar_thresh > 68:
                suggestions.append(TuningSuggestion(
                    parameter="filters.calendar_score_threshold",
                    current_value=calendar_thresh,
                    suggested_value=max(calendar_thresh - 2, 68),
                    direction="lower", confidence=0.56,
                    rationale="Calendar performance stable — slightly widen intake.",
                    evidence={"win_rate": round(cal_wr,2), "avg_pnl": round(cal_avg,2)},
                ))

    top_rej = max(rej, key=rej.get) if rej else None
    top_roll = max(rolls, key=rolls.get) if rolls else None

    return TuningReport(
        summary={
            "selected_rejected_ratio": round(ratio, 2),
            "top_rejection_reason":    top_rej,
            "top_roll_action":         top_roll,
            "strategies_with_data":    len(strats),
            "symbols_active":          len(sym_conc),
        },
        suggestions=suggestions,
    )
