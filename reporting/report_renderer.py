"""reporting/report_renderer.py — Renders reports in the cockpit."""
from __future__ import annotations
import streamlit as st

def render_report(report: dict) -> None:
    st.markdown(f"### 📄 {report.get('title','Report')}")
    st.caption(f"Environment: {report.get('environment')} | "
               f"Policy: {report.get('live_policy_version_id','—')[:8] if report.get('live_policy_version_id') else '—'} | "
               f"{report.get('timestamp_utc','')[:16]}")
    st.markdown("**Summary**")
    for b in report.get("summary_bullets",[]): st.caption(f"• {b}")
    for sec in report.get("sections",[]):
        with st.expander(sec.get("title","Section")):
            content=sec.get("content")
            if isinstance(content,list) and content:
                import pandas as pd
                try: st.dataframe(pd.DataFrame(content),use_container_width=True,hide_index=True)
                except: st.write(content)
            elif isinstance(content,dict): st.json(content)
            else: st.write(str(content) if content else "No data.")
