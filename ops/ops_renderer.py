"""ops/ops_renderer.py — Renders scheduled job health in the cockpit."""
from __future__ import annotations
import streamlit as st

def render_ops_status(job_runs: list[dict]) -> None:
    st.markdown("### ⚙️ Scheduled Operations")
    if not job_runs: st.info("No job history yet."); return
    latest=job_runs[-10:]
    succ=sum(1 for j in latest if j.get("status")=="SUCCESS")
    fail=sum(1 for j in latest if j.get("status")=="FAILED")
    skip=sum(1 for j in latest if j.get("status")=="SKIPPED")
    c1,c2,c3=st.columns(3)
    c1.metric("✅ Success",succ); c2.metric("❌ Failed",fail); c3.metric("⏭ Skipped",skip)
    import pandas as pd
    rows=[{"Job":r.get("job_name","?"),"Status":r.get("status","?"),
           "Env":r.get("environment","?"),"Time":r.get("timestamp_utc","")[:16],
           "Error":r.get("error","")[:50] if r.get("error") else ""} for r in latest]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
