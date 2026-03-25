"""dashboard/campaign_monitor.py — Per-position campaign recovery monitor."""
from __future__ import annotations
import streamlit as st

def render_campaign_monitor(rows: list[dict]) -> None:
    st.markdown("### 🗂 Campaign Monitor")
    if not rows:
        st.info("No open positions."); return
    import pandas as pd
    data=[{"Symbol":r.get("symbol"),"Basis":f'${float(r.get("campaign_net_basis",0)):.2f}',
           "Recovered%":f'{float(r.get("campaign_recovered_pct",0)):.1f}%',
           "Harvests":int(r.get("campaign_harvest_cycles",0)),
           "Flips":int(r.get("campaign_flip_count",0)),
           "Rebuilds":int(r.get("campaign_rebuild_count",0)),
           "Bot":r.get("bot_priority","—")} for r in rows]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    near_zero=[r for r in rows if float(r.get("campaign_net_basis",9999))<=0.5]
    trapped=[r for r in rows if float(r.get("campaign_recovered_pct",0))<25 and int(r.get("campaign_harvest_cycles",0))>=2]
    c1,c2=st.columns(2)
    c1.metric("Near-Zero Basis",len(near_zero)); c2.metric("Trapped Basis",len(trapped))
