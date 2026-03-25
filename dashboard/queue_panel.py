"""dashboard/queue_panel.py — Transition queue ranked table."""
from __future__ import annotations
import streamlit as st

def render_queue_panel(queue: list[dict]) -> None:
    st.markdown("### 🎯 Transition Queue")
    if not queue: st.info("No approved transitions in queue."); return
    import pandas as pd
    rows=[{"Symbol":q.get("symbol"),"Action":q.get("transition_action","").replace("_"," ").title(),
           "Score":f'{float(q.get("queue_score",0)):.1f}',"Policy":q.get("execution_policy","—"),
           "Credit":f'${float(q.get("transition_credit",0)):.2f}',"Priority":q.get("priority","—"),
           "Summary":q.get("queue_one_liner","")} for q in queue[:10]]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    ready=[q for q in queue if q.get("execution_policy")=="FULL_NOW"]
    stag =[q for q in queue if q.get("execution_policy")=="STAGGER"]
    delay=[q for q in queue if q.get("execution_policy")=="DELAY"]
    c1,c2,c3=st.columns(3)
    c1.metric("Ready Now",len(ready)); c2.metric("Stagger",len(stag)); c3.metric("Delay",len(delay))
