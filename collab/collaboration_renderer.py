"""collab/collaboration_renderer.py — Renders handoffs and timelines."""
from __future__ import annotations
import streamlit as st

def render_handoff_queue(handoffs: list[dict]) -> None:
    st.markdown("### 🤝 Team Handoffs")
    if not handoffs: st.info("No active handoffs."); return
    import pandas as pd
    rows=[{"Type":h.get("handoff_type","?"),"From":h.get("source_role","?"),"To":h.get("target_role","?"),
           "State":h.get("state","?"),"Summary":h.get("summary","")[:60],
           "Required":h.get("required_next_action","")[:50],"Created":h.get("created_utc","")[:16]}
          for h in handoffs]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

def render_collaboration_timeline(timeline: list[dict]) -> None:
    st.markdown("### 📅 Collaboration Timeline")
    if not timeline: st.info("No collaboration history."); return
    for item in timeline:
        icon={"HANDOFF_CREATED":"🚀","HANDOFF_ACCEPTED":"✅","HANDOFF_NOTE":"📝","DECISION":"⚡"}.get(item.get("event",""),"•")
        st.caption(f"{icon} {item.get('timestamp_utc','')[:16]} | **{item.get('event')}** | {item.get('summary','')}")
