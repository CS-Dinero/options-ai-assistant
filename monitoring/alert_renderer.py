"""monitoring/alert_renderer.py — Renders live alert stack in the cockpit."""
from __future__ import annotations
import streamlit as st

def render_alerts(alerts: list[dict]) -> None:
    st.markdown("### 🚨 Alerts")
    if not alerts: st.success("No active alerts."); return
    crit=[a for a in alerts if a.get("severity")=="CRITICAL"]
    warn=[a for a in alerts if a.get("severity")=="WARNING"]
    info=[a for a in alerts if a.get("severity")=="INFO"]
    c1,c2,c3=st.columns(3)
    c1.metric("🔴 Critical",len(crit)); c2.metric("🟡 Warning",len(warn)); c3.metric("🔵 Info",len(info))
    SEV_COLORS={"CRITICAL":"#dc2626","WARNING":"#f59e0b","INFO":"#3b82f6"}
    for a in sorted(alerts, key=lambda x: {"CRITICAL":0,"WARNING":1,"INFO":2}.get(x.get("severity","INFO"),3)):
        color=SEV_COLORS.get(a.get("severity","INFO"),"#6b7280")
        st.markdown(f'<div style="padding:6px 12px;border-left:4px solid {color};'
                    f'background:#0f1117;border-radius:6px;margin:3px 0">'
                    f'<strong style="color:{color}">[{a.get("severity")}]</strong> '
                    f'{a.get("summary","")} '
                    f'<span style="color:#6b7280;font-size:10px">{a.get("timestamp_utc","")[:16]}</span>'
                    f'</div>', unsafe_allow_html=True)
