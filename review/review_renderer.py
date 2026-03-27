"""review/review_renderer.py — Renders review queue and packet details."""
from __future__ import annotations
import streamlit as st

PRIORITY_COLORS={"P0":"#dc2626","P1":"#f59e0b","P2":"#2563eb","P3":"#6b7280"}

def render_review_queue(review_packets: list[dict]) -> None:
    st.markdown("### 🔎 Human Review Queue")
    if not review_packets: st.info("No open review tasks."); return
    open_p=[r for r in review_packets if r.get("state") in ("OPEN","IN_REVIEW")]
    c1,c2,c3=st.columns(3)
    c1.metric("Open Reviews",len(open_p))
    c2.metric("P0/P1 Reviews",sum(1 for r in open_p if r.get("priority") in ("P0","P1")))
    c3.metric("Approver Queue",sum(1 for r in open_p if r.get("assigned_role")=="APPROVER"))
    import pandas as pd
    rows=[{"Priority":r.get("priority","?"),"Type":r.get("review_type","?"),
           "Title":r.get("title","")[:50],"Role":r.get("assigned_role","?"),
           "State":r.get("state","?"),"Created":r.get("created_utc","")[:16]}
          for r in sorted(open_p,key=lambda x: {"P0":0,"P1":1,"P2":2,"P3":3}.get(x.get("priority","P3"),3))]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
