"""history/trend_renderer.py — Renders trend blocks in the cockpit."""
from __future__ import annotations
import streamlit as st

DIR_ICONS={"UP":"↑","DOWN":"↓","FLAT":"→","INSUFFICIENT_HISTORY":"?"}

def render_trend_block(title: str, trend: dict) -> None:
    d=trend.get("direction","?"); icon=DIR_ICONS.get(d,"?")
    color={"UP":"#22c55e","DOWN":"#ef4444","FLAT":"#6b7280","INSUFFICIENT_HISTORY":"#6b7280"}.get(d,"#6b7280")
    st.markdown(f"**{title}** {icon}")
    c1,c2,c3=st.columns(3)
    c1.metric("Latest",   f"{trend.get('latest',0):.3g}")
    c2.metric("Previous", f"{trend.get('previous',0):.3g}" if trend.get("previous") is not None else "—")
    delta_val=trend.get("delta")
    c3.metric("Δ", f"{delta_val:+.4f}" if delta_val is not None else "—")

def render_policy_impact_block(title: str, impact: dict) -> None:
    st.markdown(f"**{title}**")
    c1,c2,c3=st.columns(3)
    c1.metric("Before Avg", f"{impact.get('before_avg',0):.3g}" if impact.get("before_avg") is not None else "—")
    c2.metric("After Avg",  f"{impact.get('after_avg',0):.3g}"  if impact.get("after_avg")  is not None else "—")
    d=impact.get("delta"); c3.metric("Δ", f"{d:+.4f}" if d is not None else "—")
    st.caption(f"Status: {impact.get('status','?')} | Direction: {impact.get('direction','?')}")
