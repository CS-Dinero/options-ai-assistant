"""
engines/ui_renderer.py
Streamlit renderer for engine_orchestrator output.

Renders the full engine output dict into dashboard panels.
All rendering goes through here — dashboard/app.py just calls
render_full_engine_output(result) and gets the full UI.

Design: renderer reads from the standardized orchestrator output dict.
No raw market or derived dicts needed — orchestrator pre-packages everything.
"""
from __future__ import annotations
from typing import Any

import streamlit as st


# ─────────────────────────────────────────────
# COLOR MAPS
# ─────────────────────────────────────────────

VGA_COLORS: dict[str, str] = {
    "premium_selling":      "#22c55e",
    "neutral_time_spreads": "#3b82f6",
    "cautious_directional": "#f59e0b",
    "trend_directional":    "#f97316",
    "mixed":                "#6b7280",
    "no_trade":             "#ef4444",
}

ACTION_COLORS: dict[str, str] = {
    "STRONG":              "#22c55e",
    "TRADABLE":            "#3b82f6",
    "WATCHLIST":           "#f59e0b",
    "SKIP":                "#ef4444",
    "HOLD":                "#22c55e",
    "REVIEW_OR_ROLL":      "#f97316",
    "CLOSE_TP":            "#22c55e",
    "CLOSE_STOP":          "#ef4444",
    "CLOSE_TIME":          "#7c3aed",
    "CLOSE":               "#ef4444",
    "CLOSE_OR_CONVERT":    "#f97316",
    "EXIT_OR_ROLL_LONG":   "#7c3aed",
    "CONVERT_TO_DIAGONAL": "#f97316",
    "ROLL_SHORT":          "#f59e0b",
    "ROLL_DIAGONAL_SHORT": "#f59e0b",
    "EXIT_LONG_WINDOW":    "#ef4444",
    "EXIT_STRUCTURE_BREAK":"#ef4444",
    "EXIT_ENVIRONMENT":    "#ef4444",
    "INVALID":             "#6b7280",
    "UNKNOWN":             "#6b7280",
}


# ─────────────────────────────────────────────
# FORMATTING
# ─────────────────────────────────────────────

def _money(v: Any) -> str:
    if v in (None, "", "Open", "—"):
        return str(v) if v in ("Open", "—") else "—"
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _pill(text: str, color: str) -> str:
    return (
        f'<span style="background:{color}22;color:{color};'
        f'padding:3px 12px;border-radius:10px;font-size:12px;'
        f'font-weight:700;border:1px solid {color}44">{text}</span>'
    )


def _action_pill(text: str) -> str:
    color = ACTION_COLORS.get(text, "#6b7280")
    return _pill(text.replace("_", " "), color)


def _card_open(border_color: str = "#374151") -> str:
    return (
        f'<div style="background:#0f1117;border:1px solid {border_color}33;'
        f'border-radius:12px;padding:16px;margin-bottom:12px">'
    )


def _card_close() -> str:
    return "</div>"


def _grid(items: list[tuple[str, Any]], cols: int = 4) -> str:
    cells = "".join(
        f'<div><div style="font-size:10px;color:#6b7280;text-transform:uppercase;'
        f'margin-bottom:2px">{label}</div>'
        f'<div style="font-size:14px;font-weight:600;color:#e5e7eb">{val}</div></div>'
        for label, val in items
    )
    return (
        f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);'
        f'gap:10px;margin-top:10px">{cells}</div>'
    )


# ─────────────────────────────────────────────
# SECTION RENDERERS
# ─────────────────────────────────────────────

def render_regime_card(result: dict[str, Any]) -> None:
    """Regime Router card — shows active regime, strategies, confidence."""
    regime = result.get("regime", {})
    if not regime:
        return

    name        = regime.get("regime", "mixed")
    ui_label    = regime.get("ui_label", "MIXED")
    ui_subtitle = regime.get("ui_subtitle", "")
    rationale   = regime.get("rationale", "")
    confidence  = regime.get("confidence", 0.0)
    primary     = ", ".join(regime.get("primary_strategies", [])) or "—"
    secondary   = ", ".join(regime.get("secondary_strategies", [])) or "—"
    bias        = regime.get("trade_bias", "—")
    notes       = regime.get("notes", [])
    size_mult   = regime.get("size_multiplier", 1.0)
    color       = VGA_COLORS.get(name, "#6b7280")

    st.markdown(
        _card_open(color) +
        f'<div style="font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:1px">Regime Router</div>'
        f'<div style="font-size:20px;font-weight:800;color:{color};margin:4px 0">{ui_label}</div>'
        f'<div style="font-size:12px;color:#9ca3af;margin-bottom:10px">{ui_subtitle}</div>'
        + _grid([
            ("Confidence",      f"{confidence:.0%}"),
            ("Size Multiplier", f"{size_mult:.0%}"),
            ("Bias",            bias),
            ("Primary",         primary),
        ]) +
        f'<div style="margin-top:10px;font-size:12px;color:#9ca3af">{rationale}</div>' +
        (f'<div style="margin-top:8px">' +
         "".join(f'<div style="font-size:11px;color:#6b7280">→ {n}</div>' for n in notes) +
         '</div>' if notes else "") +
        _card_close(),
        unsafe_allow_html=True,
    )


def render_summary_metrics(result: dict[str, Any]) -> None:
    """Top-line metrics bar."""
    s = result.get("summary", {})
    if not s:
        return

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Spot",           _money(s.get("spot_price")))
    m2.metric("Expected Move",  _money(s.get("expected_move")))
    m3.metric("VGA",            str(s.get("vga_environment", "—")).replace("_", " ").title())
    m4.metric("Candidates",     s.get("total_candidates", 0))
    m5.metric("Strong",         s.get("strong_count", 0))
    m6.metric("Open Positions", s.get("open_positions", 0))


def render_ranked_trades(result: dict[str, Any], max_cards: int = 5) -> None:
    """Ranked trade recommendation cards."""
    candidates = result.get("candidates", [])
    if not candidates:
        st.info("No qualified trades in the current regime.")
        return

    from config.settings import SCORE_STRONG, SCORE_TRADABLE

    for i, trade in enumerate(candidates[:max_cards], start=1):
        score    = trade.get("confidence_score", 0)
        st_type  = trade.get("strategy_type", "")
        label    = st_type.replace("_", " ").title()
        direction = trade.get("direction", "").replace("_", " ").title()

        if score >= SCORE_STRONG:
            tier, tier_color = "★ STRONG", "#22c55e"
        elif score >= SCORE_TRADABLE:
            tier, tier_color = "○ TRADABLE", "#3b82f6"
        else:
            tier, tier_color = "✗ SKIP", "#ef4444"

        is_credit  = st_type in ("bull_put", "bear_call")
        is_debit   = st_type in ("bull_call_debit", "bear_put_debit",
                                  "calendar", "diagonal", "double_diagonal")
        entry_val  = abs(trade.get("entry_debit_credit", 0) or 0)
        entry_label = "Credit" if is_credit else "Debit"
        entry_str   = f"${entry_val:.2f} (${entry_val*100:.0f}/contract)"

        with st.container():
            st.markdown(
                _card_open() +
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div>'
                f'<div style="font-size:11px;color:#6b7280">#{i}</div>'
                f'<div style="font-size:18px;font-weight:700;color:#f9fafb">{label}</div>'
                f'<div style="font-size:12px;color:#9ca3af">{direction}</div>'
                f'</div>'
                f'<div style="text-align:right">'
                f'<div style="font-size:20px;font-weight:800;color:{tier_color}">{score}/100</div>'
                f'<div style="margin-top:4px">{_pill(tier, tier_color)}</div>'
                f'</div>'
                f'</div>'
                + _grid([
                    ("Short Strike",  f"${trade.get('short_strike', '—')}"),
                    ("Long Strike",   f"${trade.get('long_strike', '—')}"),
                    (entry_label,     entry_str),
                    ("Expiration",    trade.get("short_expiration", "—")),
                    ("Max Profit",    _money(trade.get("max_profit"))),
                    ("Max Loss",      _money(trade.get("max_loss"))),
                    ("Target Exit",   _money(trade.get("target_exit_value"))),
                    ("Stop Level",    _money(trade.get("stop_value"))),
                    ("Contracts",     trade.get("contracts", 1)),
                    ("Short DTE",     trade.get("short_dte", "—")),
                    ("Long DTE",      trade.get("long_dte", "—")),
                    ("Prob ITM",      f"{trade.get('prob_itm_proxy', 0)*100:.0f}%"),
                ]) +
                f'<div style="margin-top:8px;font-size:11px;color:#6b7280">{trade.get("notes", "")}</div>' +
                _card_close(),
                unsafe_allow_html=True,
            )


def render_position_monitor(result: dict[str, Any]) -> None:
    """Position monitor — cal/diag lifecycle decisions + credit spread signals."""
    positions = result.get("positions", {})
    if not positions:
        return

    total = positions.get("total_open", 0)
    if total == 0:
        st.caption("No open positions tracked.")
        return

    s = positions.get("summary", {})
    p1, p2, p3 = st.columns(3)
    p1.metric("Open", total)
    p2.metric("🔴 High Urgency", s.get("high_urgency", 0))
    p3.metric("⚠️ Close Signals", s.get("close_signals", 0))

    # Calendar / diagonal
    for pos in positions.get("calendar_diagonal", []):
        decision = pos.get("decision", {})
        action   = decision.get("action", "HOLD")
        color    = ACTION_COLORS.get(action, "#6b7280")
        st.markdown(
            _card_open(color) +
            f'<div style="display:flex;justify-content:space-between">'
            f'<div style="font-size:14px;font-weight:700;color:#f9fafb">'
            f'{pos.get("strategy_type","").replace("_"," ").title()}'
            f'</div>{_action_pill(action)}</div>'
            + _grid([
                ("Symbol",      pos.get("symbol", "—")),
                ("Long Strike", f"${decision.get('long_strike', '—')}"),
                ("Short Strike",f"${decision.get('short_strike', '—')}"),
                ("Long DTE",    decision.get("long_dte", "—")),
            ]) +
            f'<div style="margin-top:8px;font-size:11px;color:#9ca3af">'
            f'{decision.get("rationale", "")}</div>' +
            _card_close(),
            unsafe_allow_html=True,
        )

    # Credit spreads
    for pos in positions.get("credit_spreads", []):
        status = pos.get("management_status", "HOLD")
        color  = ACTION_COLORS.get(status, "#6b7280")
        st.markdown(
            _card_open(color) +
            f'<div style="display:flex;justify-content:space-between">'
            f'<div style="font-size:14px;font-weight:700;color:#f9fafb">'
            f'{pos.get("strategy_type","").replace("_"," ").title()}'
            f'</div>{_action_pill(status)}</div>'
            + _grid([
                ("Symbol",     pos.get("symbol", "—")),
                ("Short",      f"${pos.get('short_strike','—')}"),
                ("Expiration", pos.get("short_expiration", "—")),
                ("DTE",        pos.get("short_dte", "—")),
            ]) +
            _card_close(),
            unsafe_allow_html=True,
        )


def render_diagnostics(result: dict[str, Any]) -> None:
    """Collapsible diagnostics panel."""
    with st.expander("🔧 Engine Diagnostics"):
        summary = result.get("summary", {})
        derived = result.get("derived", {})
        cols = st.columns(4)
        items = [
            ("IV Regime",      derived.get("iv_regime", "—")),
            ("Gamma Regime",   derived.get("gamma_regime", "—")),
            ("Term Structure", derived.get("term_structure", "—")),
            ("Skew State",     derived.get("skew_state", "—")),
            ("Gamma Flip",     _money(derived.get("gamma_flip"))),
            ("Gamma Trap",     _money(derived.get("gamma_trap"))),
            ("Total GEX",      f"{derived.get('total_gex', 0):.0f}"),
            ("ATR Trend",      derived.get("atr_trend", "—")),
        ]
        for i, (label, val) in enumerate(items):
            cols[i % 4].metric(label, val)


# ─────────────────────────────────────────────
# FULL OUTPUT RENDERER
# ─────────────────────────────────────────────

def render_full_engine_output(
    result:               dict[str, Any],
    *,
    show_summary:         bool = True,
    show_regime:          bool = True,
    show_ranked_trades:   bool = True,
    show_position_monitor:bool = True,
    show_diagnostics:     bool = True,
    max_trade_cards:      int  = 5,
) -> None:
    """
    Single call renders the complete engine output into Streamlit.
    Call this from dashboard/app.py after run_options_engine().
    """
    if show_summary:
        render_summary_metrics(result)
        st.divider()

    if show_regime:
        render_regime_card(result)
        st.divider()

    if show_ranked_trades:
        st.markdown("### 🎯 Trade Recommendations")
        render_ranked_trades(result, max_cards=max_trade_cards)
        st.divider()

    if show_position_monitor:
        st.markdown("### 📍 Position Monitor")
        render_position_monitor(result)
        st.divider()

    if show_diagnostics:
        render_diagnostics(result)
