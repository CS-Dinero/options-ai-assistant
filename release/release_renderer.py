"""release/release_renderer.py — Renders release bundles in the cockpit."""
from __future__ import annotations
import streamlit as st

STATE_COLORS={"DRAFT":"#6b7280","APPROVED":"#2563eb","LIVE":"#22c55e","ROLLED_BACK":"#ef4444"}

def render_release_packets(releases: list[dict]) -> None:
    st.markdown("### 📦 Release Management")
    if not releases: st.info("No active release bundles."); return
    import pandas as pd
    rows=[{"ID":r.get("release_id","")[:8],"Type":r.get("bundle_type","?"),
           "Title":r.get("title","")[:50],"State":r.get("state","?"),
           "Env":r.get("environment","?"),"Impacted":len(r.get("scope",{}).get("impacted_components",[])),
           "Created":r.get("created_utc","")[:10]} for r in releases]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
