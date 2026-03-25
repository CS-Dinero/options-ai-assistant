"""dashboard/execution_readiness_panel.py — What can be done now vs blocked."""
from __future__ import annotations
import streamlit as st

def render_execution_readiness(rows: list[dict]) -> None:
    st.markdown("### ⚡ Execution Readiness")
    ready=[r for r in rows if r.get("transition_execution_policy")=="FULL_NOW"]
    stag =[r for r in rows if r.get("transition_execution_policy")=="STAGGER"]
    delay=[r for r in rows if r.get("transition_execution_policy")=="DELAY"]
    s_blk=[r for r in rows if r.get("transition_execution_surface_ok") is False]
    t_blk=[r for r in rows if r.get("transition_timing_ok") is False]
    p_blk=[r for r in rows if r.get("transition_portfolio_fit_ok") is False]
    c1,c2,c3=st.columns(3)
    c1.metric("✅ Full Now",len(ready)); c2.metric("⏳ Stagger",len(stag)); c3.metric("🕐 Delay",len(delay))
    c4,c5,c6=st.columns(3)
    c4.metric("🌊 Surface Blocked",len(s_blk)); c5.metric("🕰 Timing Blocked",len(t_blk)); c6.metric("📦 Portfolio Blocked",len(p_blk))
