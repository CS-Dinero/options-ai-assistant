"""
engines/portfolio_ui_renderer.py
Streamlit renderer for portfolio_runner output.

Single entry point: render_portfolio_output(portfolio_output)
Renders: portfolio summary, symbol allocations, selected trades, per-symbol tabs.
"""
from __future__ import annotations
from typing import Any

import streamlit as st

from engines.ui_renderer import (
    render_regime_card, render_summary_metrics,
    render_ranked_trades, render_position_monitor,
    render_diagnostics, VGA_COLORS, ACTION_COLORS, _money, _pill, _action_pill,
)


def _fmt(v: Any) -> str:
    return _money(v)


def render_portfolio_summary(output: dict[str, Any]) -> None:
    meta  = output.get("portfolio_meta", {})
    alloc = output.get("allocation", {})

    m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
    m1.metric("Symbols",          meta.get("symbols_processed", 0))
    m2.metric("Ranked Trades",    meta.get("total_ranked_trades", 0))
    m3.metric("Selected",         meta.get("selected_trades", 0))
    m4.metric("Rejected",         meta.get("rejected_trades", 0))
    m5.metric("Open Positions",   meta.get("total_open_positions", 0))
    m6.metric("Budget",           _fmt(alloc.get("total_risk_budget")))
    m7.metric("Used",             _fmt(alloc.get("used_risk_budget")))
    m8.metric("Remaining",        _fmt(alloc.get("remaining_risk_budget")))


def render_symbol_allocations(output: dict[str, Any]) -> None:
    alloc     = output.get("allocation", {})
    sym_alloc = alloc.get("symbol_allocations", {})
    if not sym_alloc:
        return
    st.markdown("**Symbol Allocations**")
    cols = st.columns(min(len(sym_alloc), 4))
    for i, (sym, amt) in enumerate(sym_alloc.items()):
        cols[i % 4].metric(sym, _fmt(amt))


def render_selected_trades(output: dict[str, Any]) -> None:
    alloc    = output.get("allocation", {})
    selected = alloc.get("selected_trades", [])
    if not selected:
        st.info("No trades selected by portfolio allocator.")
        return
    for t in selected:
        st_type  = str(t.get("strategy_type", t.get("strategy", ""))).replace("_", " ").title()
        decision = str(t.get("decision", ""))
        score    = t.get("confidence_score", t.get("score", 0))
        vga      = str(t.get("vga_environment", t.get("environment_label", "mixed"))).lower()
        color    = VGA_COLORS.get(vga, "#6b7280")
        with st.container():
            st.markdown(
                f'<div style="background:#0f1117;border:1px solid {color}33;'
                f'border-radius:10px;padding:12px;margin-bottom:8px">'
                f'<div style="display:flex;justify-content:space-between">'
                f'<div><span style="font-size:13px;font-weight:700;color:#f9fafb">'
                f'{t.get("symbol","")} · {st_type}</span>'
                f'<br><span style="font-size:11px;color:#9ca3af">Score {score} | {vga}</span></div>'
                f'{_action_pill(decision)}'
                f'</div>'
                f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:8px">'
                f'<div><div style="font-size:10px;color:#6b7280">Risk</div>'
                f'<div style="font-size:13px;color:#e5e7eb">{_fmt(t.get("_risk"))}</div></div>'
                f'<div><div style="font-size:10px;color:#6b7280">Contracts</div>'
                f'<div style="font-size:13px;color:#e5e7eb">{t.get("contracts","—")}</div></div>'
                f'<div><div style="font-size:10px;color:#6b7280">Short Strike</div>'
                f'<div style="font-size:13px;color:#e5e7eb">${t.get("short_strike","—")}</div></div>'
                f'<div><div style="font-size:10px;color:#6b7280">Expiry</div>'
                f'<div style="font-size:13px;color:#e5e7eb">{t.get("short_expiration","—")}</div></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


def render_symbol_tabs(output: dict[str, Any]) -> None:
    symbols = output.get("symbols", [])
    if not symbols:
        return
    tabs = st.tabs([s["symbol"] for s in symbols])
    for tab, sym_block in zip(tabs, symbols):
        with tab:
            engine = sym_block.get("engine_output", {})
            render_summary_metrics(engine)
            st.divider()
            render_regime_card(engine)
            st.divider()
            render_ranked_trades(engine, max_cards=5)
            st.divider()
            render_position_monitor(engine)
            render_diagnostics(engine)


def render_allocation_rationale(output: dict[str, Any]) -> None:
    rationale = output.get("allocation", {}).get("rationale", [])
    if not rationale:
        return
    with st.expander("📊 Portfolio Allocation Rationale"):
        for line in rationale:
            st.caption(line)


def render_portfolio_output(output: dict[str, Any]) -> None:
    """Single call renders the full portfolio engine output."""
    render_portfolio_summary(output)
    st.divider()
    render_symbol_allocations(output)
    render_selected_trades(output)
    st.divider()
    render_symbol_tabs(output)
    render_allocation_rationale(output)
