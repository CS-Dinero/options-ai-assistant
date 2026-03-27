"""attribution/attribution_renderer.py — Renders attribution summaries in the cockpit."""
from __future__ import annotations
import streamlit as st
from typing import Any

def _top_pos(d):
    if not d: return "N/A",0.0
    k=max(d,key=lambda x: d[x].get("avg_roi_score",-9999)); return k,d[k].get("avg_roi_score",0)
def _top_neg(d):
    if not d: return "N/A",0.0
    k=min(d,key=lambda x: d[x].get("avg_roi_score",9999)); return k,d[k].get("avg_roi_score",0)

def render_attribution_summary(playbook_attr: dict[str,Any], mandate_attr: dict[str,Any],
                                handoff_attr: dict[str,Any]) -> None:
    st.markdown("### 📈 Performance Attribution")
    pp,ppv=_top_pos(playbook_attr); pn,pnv=_top_neg(playbook_attr)
    mp,mpv=_top_pos(mandate_attr); hn,hnv=_top_neg(handoff_attr)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Best Playbook ROI",f"{pp}",f"{ppv:+.1f}")
    c2.metric("Worst Playbook ROI",f"{pn}",f"{pnv:+.1f}")
    c3.metric("Best Mandate ROI",f"{mp}",f"{mpv:+.1f}")
    c4.metric("Most Friction Handoff",f"{hn}",f"{hnv:+.1f}")
