"""knowledge/knowledge_renderer.py — Shows relevant memory in the cockpit."""
from __future__ import annotations
import streamlit as st

TYPE_ICONS={"SYMBOL_BEHAVIOR_NOTE":"📌","PLAYBOOK_CAVEAT":"⚠️","EXECUTION_TRAP":"🚫",
             "APPROVED_HEURISTIC":"✅","POLICY_RATIONALE":"📋","OVERRIDE_PATTERN":"🔄",
             "QUEUE_PATTERN":"📊","CAPITAL_PATTERN":"💰","ROLLBACK_LESSON":"🔙"}

def render_knowledge_context(entries: list[dict]) -> None:
    st.markdown("### 🧠 Knowledge Context")
    if not entries: st.info("No relevant knowledge context for current selection."); return
    for e in entries:
        icon=TYPE_ICONS.get(e.get("knowledge_type",""),"•")
        conf=e.get("confidence","?")
        color={"HIGH":"#22c55e","MEDIUM":"#f59e0b","LOW":"#ef4444"}.get(conf,"#6b7280")
        st.markdown(f'<div style="padding:6px 12px;border-left:3px solid {color};'
                    f'background:#0f1117;border-radius:4px;margin:3px 0">'
                    f'{icon} <strong>[{e.get("knowledge_type")}]</strong> '
                    f'{e.get("summary","")} '
                    f'<span style="color:#6b7280;font-size:10px">{e.get("subject_type")}:{e.get("subject_id")}</span>'
                    f'</div>', unsafe_allow_html=True)

def render_knowledge_library(entries: list[dict], environment: str="LIVE") -> None:
    st.markdown("### 🏛 Knowledge Library")
    env_entries=[e for e in entries if e.get("environment")==environment and e.get("status")=="ACTIVE"]
    if not env_entries: st.info("No knowledge entries yet."); return
    import pandas as pd
    rows=[{"Type":e.get("knowledge_type","?"),"Subject":f'{e.get("subject_type","?")}:{e.get("subject_id","?")}',
           "Summary":e.get("summary","")[:80],"Confidence":e.get("confidence","?"),
           "Created":e.get("created_utc","")[:10]} for e in env_entries]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
