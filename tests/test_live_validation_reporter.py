"""tests/test_live_validation_reporter.py — Reporter and regression tool."""
from validation.live_validation_reporter import build_live_validation_report, render_live_validation_report_text
from validation.live_validation_regression import compare_reports, render_regression_report
import json, tempfile, pathlib

SAMPLE_RESULTS=[
    {"symbol":"TSLA","regime_environment":"NEUTRAL_TIME_SPREADS","candidate_found":True,
     "campaign_family":"DEEP_ITM_CAMPAIGN","entry_family":"DEEP_ITM_CALENDAR_ENTRY",
     "campaign_state":"ROLL_READY","campaign_action":"ROLL","best_path_code":"ROLL_SAME_SIDE",
     "best_path_score":84.0,"queue_priority_band":"DECIDE_NOW","queue_priority_score":82.4,
     "ticket_ready":True,"warnings":[],"notes":["TSLA note"]},
    {"symbol":"SPY","regime_environment":"PREMIUM_SELLING","candidate_found":False,
     "campaign_state":None,"best_path_code":None,"queue_priority_band":None,
     "queue_priority_score":None,"ticket_ready":False,"warnings":[],"notes":[]},
    {"symbol":"QQQ","regime_environment":"NEUTRAL_TIME_SPREADS","candidate_found":False,
     "campaign_state":None,"best_path_code":None,"queue_priority_band":None,
     "queue_priority_score":None,"ticket_ready":False,"warnings":["No tracked campaign."],"notes":[]},
]

def test_live_validation_reporter_builds():
    report=build_live_validation_report(SAMPLE_RESULTS)
    assert report["summary"]["total_symbols"]==3
    assert report["summary"]["candidate_found_count"]==1
    assert report["summary"]["ticket_ready_count"]==1
    assert report["summary"]["warning_count"]==1
    assert report["summary"]["roll_ready_count"]==1
    assert report["summary"]["best_path_roll_count"]==1
    assert report["summary"]["decide_now_count"]==1

def test_render_text_report():
    text=render_live_validation_report_text(SAMPLE_RESULTS)
    assert "LIVE VALIDATION SUMMARY" in text
    assert "symbols=3" in text
    assert "TSLA:" in text
    assert "QQQ:" in text
    assert "WARNING:" in text

def test_regression_clean():
    with tempfile.TemporaryDirectory() as td:
        report={"summary":{"candidate_found_count":1,"ticket_ready_count":1,"warning_count":0,
                            "roll_ready_count":1,"best_path_roll_count":1},
                "rows":[{"symbol":"TSLA","candidate_found":True,"campaign_state":"ROLL_READY",
                          "campaign_action":"ROLL","selected_transition_type":"ROLL_SAME_SIDE",
                          "best_path_code":"ROLL_SAME_SIDE","best_path_score":84.0,"alt_path_code":"FLIP_SELECTIVELY",
                          "queue_priority_band":"DECIDE_NOW","queue_priority_score":82.4,
                          "ticket_ready":True,"warning_count":0}]}
        p1=pathlib.Path(td)/"old.json"; p2=pathlib.Path(td)/"new.json"
        p1.write_text(json.dumps(report)); p2.write_text(json.dumps(report))
        result=compare_reports(str(p1),str(p2))
        assert result["clean"]
        assert "No drift" in render_regression_report(result)

def test_regression_detects_path_drift():
    with tempfile.TemporaryDirectory() as td:
        old_row={"symbol":"TSLA","candidate_found":True,"campaign_state":"ROLL_READY",
                  "campaign_action":"ROLL","selected_transition_type":"ROLL_SAME_SIDE",
                  "best_path_code":"ROLL_SAME_SIDE","best_path_score":84.0,"alt_path_code":"FLIP_SELECTIVELY",
                  "queue_priority_band":"DECIDE_NOW","queue_priority_score":82.4,"ticket_ready":True,"warning_count":0}
        new_row={**old_row,"best_path_code":"FLIP_SELECTIVELY","queue_priority_band":"WATCH_CLOSELY"}
        base_summary={"candidate_found_count":1,"ticket_ready_count":1,"warning_count":0,"roll_ready_count":1,"best_path_roll_count":1}
        old={"summary":base_summary,"rows":[old_row]}
        new={"summary":{**base_summary,"best_path_roll_count":0},"rows":[new_row]}
        p1=pathlib.Path(td)/"old.json"; p2=pathlib.Path(td)/"new.json"
        p1.write_text(json.dumps(old)); p2.write_text(json.dumps(new))
        result=compare_reports(str(p1),str(p2))
        assert not result["clean"]
        assert result["total_changes"]>0
        report_text=render_regression_report(result)
        assert "FLIP_SELECTIVELY" in report_text or "changes" in report_text
