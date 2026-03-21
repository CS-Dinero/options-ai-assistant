"""
engines/portfolio_allocator.py
Trade-level portfolio allocator — decides which trades to take across symbols.

Operates on enriched trade card dicts (output of engine_orchestrator +
allocation_ready_trades enrichment). Each trade carries symbol, strategy,
score, risk, environment, and regime context.

Features:
  - Calendar reserve: portion of budget held for time spreads
  - Side bucket tracking: prevents double-counting same side on one symbol
  - Per-symbol and per-trade budget caps
  - Reject reason tagging for analytics
  - Score quality ranking with regime confidence bonus
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Literal, Optional


StrategyType = Literal[
    "bull_put", "bear_call", "bull_call_debit", "bear_put_debit",
    "calendar", "diagonal", "double_diagonal",
    # Legacy EGPE names from spec adapters
    "bull_put_credit", "bear_call_credit", "atm_calendar",
]


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class AllocationConfig:
    account_size:                   float = 200_000
    max_total_portfolio_risk_pct:   float = 0.03    # 3% total = $6K on $200K
    max_symbol_risk_pct:            float = 0.02    # 2% per symbol = $4K
    max_trade_risk_pct:             float = 0.01    # 1% per trade  = $2K
    max_symbols:                    int   = 3
    max_trades_per_symbol:          int   = 2
    allow_both_sides_same_symbol:   bool  = True
    reserve_for_calendars_pct:      float = 0.25    # 25% of total budget held for time spreads
    calendar_min_score_gate:        float = 78.0
    min_trade_score:                float = 75.0


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@dataclass
class AllocationDecision:
    selected_trades:     list[dict[str, Any]]
    rejected_trades:     list[dict[str, Any]]
    total_risk_budget:   float
    used_risk_budget:    float
    remaining_risk_budget: float
    symbol_allocations:  dict[str, float]
    rationale:           list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _sf(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None, "", "—", "Open"):
            return default
        if isinstance(v, str):
            v = v.replace("$", "").replace(",", "").strip()
        return float(v)
    except (TypeError, ValueError):
        return default


def _trade_risk(trade: dict[str, Any]) -> float:
    """Risk dollars for one trade — uses max_loss, then debit fallback."""
    ml = _sf(trade.get("max_loss"))
    if ml > 0:
        return ml
    debit    = _sf(trade.get("entry_debit") or trade.get("entry_debit_credit"))
    contracts = max(int(_sf(trade.get("contracts"), 1)), 1)
    if debit > 0:
        return debit * 100 * contracts
    return 0.0


def _is_calendar_type(trade: dict[str, Any]) -> bool:
    st = str(trade.get("strategy_type", trade.get("strategy", ""))).lower()
    return st in ("calendar", "diagonal", "double_diagonal", "atm_calendar")


def _side_bucket(trade: dict[str, Any]) -> str:
    st = str(trade.get("strategy_type", trade.get("strategy", ""))).lower()
    if st in ("bull_put", "bull_put_credit"):
        return "put_credit"
    if st in ("bear_call", "bear_call_credit"):
        return "call_credit"
    if _is_calendar_type(trade):
        return "calendar"
    return "other"


def _rank_weight(trade: dict[str, Any]) -> float:
    score      = _sf(trade.get("confidence_score", trade.get("score")))
    reg_conf   = _sf(trade.get("regime_confidence"))
    env        = str(trade.get("vga_environment", trade.get("environment_label", "mixed"))).lower()
    decision   = str(trade.get("decision", "")).upper()

    env_bonus = {
        "premium_selling":      4.0,
        "neutral_time_spreads": 2.0,
        "mixed":               -2.0,
        "cautious_directional":-4.0,
        "trend_directional":   -6.0,
    }.get(env, 0.0)

    dec_bonus = {"STRONG": 5.0, "TRADABLE": 2.0, "WATCHLIST": -10.0, "SKIP": -25.0}.get(decision, 0.0)

    return score + (reg_conf * 10.0) + env_bonus + dec_bonus


# ─────────────────────────────────────────────
# ENRICHMENT HELPER
# ─────────────────────────────────────────────

def enrich_trade_for_allocation(
    trade:          dict[str, Any],
    symbol:         str,
    vga:            str,
    regime_name:    str,
    regime_confidence: float,
) -> dict[str, Any]:
    """
    Add allocation context fields to a raw candidate dict.
    Call this after run_options_engine() to prepare for allocate_portfolio().
    """
    enriched = dict(trade)
    enriched["symbol"]            = symbol
    enriched["vga_environment"]   = vga
    enriched["environment_label"] = vga
    enriched["regime_name"]       = regime_name
    enriched["regime_confidence"] = regime_confidence
    return enriched


# ─────────────────────────────────────────────
# ALLOCATOR
# ─────────────────────────────────────────────

def allocate_portfolio(
    trades: list[dict[str, Any]],
    cfg:    AllocationConfig | None = None,
) -> AllocationDecision:
    """
    Select trades from a ranked list subject to portfolio-level constraints.

    trades: enriched candidate dicts from enrich_trade_for_allocation()
    cfg:    AllocationConfig (uses defaults if None)

    Returns AllocationDecision with selected, rejected, budgets, rationale.
    """
    cfg = cfg or AllocationConfig()

    total_budget    = cfg.account_size * cfg.max_total_portfolio_risk_pct
    sym_cap         = cfg.account_size * cfg.max_symbol_risk_pct
    trade_cap       = cfg.account_size * cfg.max_trade_risk_pct
    cal_reserve     = total_budget * cfg.reserve_for_calendars_pct

    selected: list[dict[str, Any]] = []
    rejected:  list[dict[str, Any]] = []
    rationale: list[str]            = []

    sym_usage:  dict[str, float]     = {}
    sym_count:  dict[str, int]       = {}
    sym_sides:  dict[str, set[str]]  = {}

    used_credit  = 0.0
    used_calendar = 0.0

    # ── Pre-filter ────────────────────────────────────────────────────────────
    prefiltered: list[dict[str, Any]] = []
    for t in trades:
        score = _sf(t.get("confidence_score", t.get("score")))
        risk  = _trade_risk(t)
        if score < cfg.min_trade_score:
            rejected.append({**t, "_reject_reason": "below_min_score"})
            continue
        if risk <= 0:
            rejected.append({**t, "_reject_reason": "invalid_risk"})
            continue
        if risk > trade_cap:
            rejected.append({**t, "_reject_reason": "exceeds_trade_cap"})
            continue
        t2 = dict(t)
        t2["_risk"]        = risk
        t2["_rank_weight"] = _rank_weight(t)
        prefiltered.append(t2)

    # Sort by rank weight DESC (best first), then capital efficiency ASC
    prefiltered.sort(key=lambda x: (x["_rank_weight"], -x["_risk"]), reverse=True)

    # ── Selection loop ────────────────────────────────────────────────────────
    for trade in prefiltered:
        sym      = str(trade.get("symbol", ""))
        risk     = _sf(trade.get("_risk"))
        is_cal   = _is_calendar_type(trade)
        side     = _side_bucket(trade)

        # Symbol count cap
        active_syms = set(sym_usage.keys()) | {sym}
        if len(active_syms) > cfg.max_symbols:
            rejected.append({**trade, "_reject_reason": "max_symbols_reached"})
            continue

        # Trades per symbol cap
        if sym_count.get(sym, 0) >= cfg.max_trades_per_symbol:
            rejected.append({**trade, "_reject_reason": "max_trades_per_symbol"})
            continue

        # Per-symbol budget cap
        if sym_usage.get(sym, 0.0) + risk > sym_cap:
            rejected.append({**trade, "_reject_reason": "exceeds_symbol_cap"})
            continue

        # Both-sides restriction
        if not cfg.allow_both_sides_same_symbol:
            existing = sym_sides.get(sym, set())
            if existing and side not in existing:
                rejected.append({**trade, "_reject_reason": "both_sides_disabled"})
                continue

        # Calendar gate + reserve
        if is_cal:
            score = _sf(trade.get("confidence_score", trade.get("score")))
            if score < cfg.calendar_min_score_gate:
                rejected.append({**trade, "_reject_reason": "calendar_score_gate"})
                continue
            if used_calendar + risk > cal_reserve:
                rejected.append({**trade, "_reject_reason": "calendar_reserve_exceeded"})
                continue
        else:
            non_cal_cap = total_budget - cal_reserve
            if used_credit + risk > non_cal_cap:
                # Allow overflow into unused calendar reserve
                if used_calendar == 0.0 and (used_credit + risk) <= total_budget:
                    rationale.append(f"{sym}/{side}: credit overflow into unused calendar reserve.")
                else:
                    rejected.append({**trade, "_reject_reason": "credit_budget_exceeded"})
                    continue

        # Total budget cap
        if (used_credit + used_calendar + risk) > total_budget:
            rejected.append({**trade, "_reject_reason": "exceeds_total_budget"})
            continue

        # ── SELECT ────────────────────────────────────────────────────────────
        selected.append(trade)
        sym_usage[sym]  = sym_usage.get(sym, 0.0) + risk
        sym_count[sym]  = sym_count.get(sym, 0) + 1
        sym_sides.setdefault(sym, set()).add(side)
        if is_cal:
            used_calendar += risk
        else:
            used_credit += risk

    used    = used_credit + used_calendar
    remaining = max(total_budget - used, 0.0)

    rationale.extend([
        f"Total budget: ${total_budget:,.0f} | Used: ${used:,.0f} | Remaining: ${remaining:,.0f}",
        f"Calendar reserve: ${cal_reserve:,.0f} | Used: ${used_calendar:,.0f}",
        f"Selected {len(selected)} trade(s) across {len(sym_usage)} symbol(s).",
        *(f"  {k}: ${v:,.0f}" for k, v in sym_usage.items()),
    ])

    return AllocationDecision(
        selected_trades=selected,
        rejected_trades=rejected,
        total_risk_budget=round(total_budget, 2),
        used_risk_budget=round(used, 2),
        remaining_risk_budget=round(remaining, 2),
        symbol_allocations={k: round(v, 2) for k, v in sym_usage.items()},
        rationale=rationale,
    )
