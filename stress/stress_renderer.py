"""stress/stress_renderer.py — Renders stress test results in the cockpit."""
from __future__ import annotations
import streamlit as st
from reporting.report_renderer import render_report

def render_stress_result(report: dict) -> None:
    st.markdown("### ⚡ Stress Test Result")
    resilience={}
    for sec in report.get("sections",[]):
        if sec.get("title")=="Resilience Score": resilience=sec.get("content",{})
    score=resilience.get("resilience_score",0); status=resilience.get("status","?")
    color={"ROBUST":"#22c55e","STABLE":"#f59e0b","FRAGILE":"#dc2626"}.get(status,"#6b7280")
    st.markdown(f'<div style="padding:8px 14px;border-left:4px solid {color};background:#0f1117;border-radius:8px">'
                f'<strong style="color:{color}">Resilience: {score:.1f} — {status}</strong></div>',
                unsafe_allow_html=True)
    render_report(report)

def render_stress_lab(enriched_rows, transition_queue, exposure_metrics, active_mandate, environment="DEV"):
    """Interactive stress lab in Streamlit."""
    import streamlit as st
    from stress.stress_scenario_builder import build_stress_scenario
    from stress.stress_simulator import simulate_stress_scenario
    from stress.stress_diff_engine import build_stress_diff
    from stress.stress_scoring_engine import score_stress_resilience
    from stress.stress_report_builder import build_stress_report
    from monitoring.metric_engine import compute_operational_metrics

    PRESETS={
        "Fill Quality Shock (-15pt)": {"shocks":[{"type":"ROWS","fn":__import__("stress.stress_variable_engine",fromlist=["apply_fill_quality_shock"]).apply_fill_quality_shock,"kwargs":{"points":15.0}}]},
        "Surface Compression (-8pt)": {"shocks":[{"type":"ROWS","fn":__import__("stress.stress_variable_engine",fromlist=["apply_surface_compression_shock"]).apply_surface_compression_shock,"kwargs":{"points":8.0}}]},
        "Timing Friction (-10pt)":    {"shocks":[{"type":"ROWS","fn":__import__("stress.stress_variable_engine",fromlist=["apply_timing_friction_shock"]).apply_timing_friction_shock,"kwargs":{"points":10.0}}]},
        "Capital Choke":              {"shocks":[{"type":"ROWS","fn":__import__("stress.stress_variable_engine",fromlist=["apply_capital_choke_shock"]).apply_capital_choke_shock,"kwargs":{}}]},
        "Combined Risk":              {"shocks":[
            {"type":"ROWS","fn":__import__("stress.stress_variable_engine",fromlist=["apply_fill_quality_shock"]).apply_fill_quality_shock,"kwargs":{"points":10.0}},
            {"type":"ROWS","fn":__import__("stress.stress_variable_engine",fromlist=["apply_surface_compression_shock"]).apply_surface_compression_shock,"kwargs":{"points":6.0}},
        ]},
    }

    from mandate.mandate_registry import MANDATE_REGISTRY
    preset_name=st.selectbox("Stress Preset",list(PRESETS.keys()),key="stress_preset")
    mandate_override=st.selectbox("Mandate Override (optional)",["-"]+list(MANDATE_REGISTRY.keys()),key="stress_mandate")
    mo=None if mandate_override=="-" else mandate_override

    if st.button("▶ Run Stress Test",key="run_stress"):
        with st.spinner("Running stress simulation..."):
            preset=PRESETS[preset_name]
            scenario=build_stress_scenario(preset_name,active_mandate,preset["shocks"],mo)
            result=simulate_stress_scenario(enriched_rows,transition_queue,exposure_metrics,active_mandate,scenario,environment)
            baseline_metrics=compute_operational_metrics(enriched_rows,transition_queue,{},{},exposure_metrics)
            baseline_alerts=[]
            diff=build_stress_diff(baseline_metrics,result["stressed_metrics"],
                                   transition_queue,result["stressed_queue"],
                                   baseline_alerts,result["stressed_alerts"],
                                   [],result["stressed_refinements"])
            resilience=score_stress_resilience(diff)
            report=build_stress_report(environment,None,preset_name,
                                       result["stressed_mandate"],diff,resilience,
                                       result["stressed_alerts"],result["stressed_refinements"])
            render_stress_result(report)
