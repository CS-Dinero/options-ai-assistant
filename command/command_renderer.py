"""command/command_renderer.py — The executive control surface."""
from __future__ import annotations
import streamlit as st

ENV_COLORS={"LIVE":"#22c55e","SIM":"#2563eb","DEV":"#6b7280"}
BAND_ICONS={"ACT_NOW":"🔴","DECIDE_NOW":"🟡","WATCH_CLOSELY":"🔵","IMPROVE_LATER":"⚪"}

def render_command_center(summary: dict, routed_attention: dict) -> None:
    env=summary.get("headline","").split("|")[0].strip() if summary.get("headline") else "?"
    color=ENV_COLORS.get(env,"#6b7280")
    st.markdown(f'<div style="padding:10px 16px;background:{color};color:#fff;border-radius:8px;'
                f'font-size:16px;font-weight:700;margin-bottom:12px">'
                f'⚑ {summary.get("headline","")}</div>', unsafe_allow_html=True)

    kpis=summary.get("kpis",{})
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Queue Depth",kpis.get("queue_depth",0))
    c2.metric("Ready Now",kpis.get("ready_now_count",0))
    c3.metric("🔴 Critical",kpis.get("critical_alert_count",0))
    c4.metric("Urgent Reviews",kpis.get("urgent_review_count",0))
    c5.metric("Active Releases",kpis.get("active_release_count",0))

    c6,c7,c8=st.columns(3)
    c6.metric("Deployable Capital",f'${kpis.get("deployable_capital",0):,.0f}')
    c7.metric("Avail. Incr. Risk",f'${kpis.get("available_incremental_risk",0):,.0f}')
    c8.metric("Weakest Capability",kpis.get("weakest_capability","—") or "—")

    col1,col2,col3=st.columns(3)
    with col1: st.info(f"**Top Issue**\n{summary.get('top_issue','None')}")
    with col2: st.success(f"**Top Opportunity**\n{summary.get('top_opportunity','None')}")
    with col3: st.info(f"**Key Learning**\n{summary.get('important_learning','None')}")

    st.divider()
    for section,items in routed_attention.items():
        if not items: continue
        st.markdown(f"**{section.replace('_',' ')}**")
        for item in items[:3]:
            icon=BAND_ICONS.get(item.get("priority_band",""),"•")
            st.caption(f"{icon} {item.get('title','?')}")
