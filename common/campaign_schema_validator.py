"""common/campaign_schema_validator.py — Lightweight field validators for campaign pipeline objects.

Each validator returns (passed: bool, errors: list[str]).
Call these at stage boundaries to catch schema drift early.
"""
from __future__ import annotations
from typing import Any

# ─── Required fields per stage ────────────────────────────────────────────────
SCANNER_CANDIDATE_REQUIRED = [
    "campaign_family","entry_family","structure","entry_net_debit",
    "entry_cheapness_score","future_roll_score","candidate_score",
    "expected_move_clearance","liquidity_score",
]
ENRICHED_ROW_REQUIRED = [
    "symbol","campaign_id","campaign_family","entry_family",
    "current_structure","current_side","opening_debit","opening_credit",
    "realized_credit_collected","realized_close_cost","repair_debit_paid",
    "net_campaign_basis","campaign_recovered_pct","campaign_cycle_count","campaign_realized_pnl",
]
LEDGER_SNAPSHOT_REQUIRED = [
    "campaign_id","campaign_family","entry_family","opening_debit","opening_credit",
    "realized_credit_collected","realized_close_cost","repair_debit_paid",
    "net_campaign_basis","campaign_recovered_pct","campaign_cycle_count","campaign_realized_pnl",
]
LIFECYCLE_DECISION_REQUIRED = [
    "campaign_id","campaign_family","entry_family","campaign_state","campaign_action",
    "campaign_urgency","campaign_reason","selected_transition_type",
]
RANKED_PATH_REQUIRED = [
    "path_code","path_total_score","campaign_recovery_score","future_roll_score",
    "projected_credit","projected_debit","projected_basis_after_action","approved","reason",
]
QUEUE_ROW_REQUIRED = [
    "symbol","campaign_id","campaign_family","entry_family","campaign_state","campaign_action",
    "campaign_urgency","net_campaign_basis","campaign_recovered_pct",
    "best_path_code","queue_priority_score","queue_priority_band",
]
WORKSPACE_REQUIRED_KEYS = [
    "workspace_type","campaign_economics","selected_path","roll_panel",
    "transition_panel","execution_panel",
]
WORKSPACE_ECONOMICS_REQUIRED = [
    "opening_debit","net_campaign_basis","campaign_recovered_pct","campaign_cycle_count",
]
WORKSPACE_ROLL_PANEL_REQUIRED = ["roll_credit_est","future_roll_score"]
TICKET_REQUIRED = [
    "ticket_type","authority","campaign_id","selected_path","projected_credit",
    "projected_debit","projected_basis_after_action","future_roll_score",
    "campaign_snapshot","execution_plan","warnings","notes",
]
TRADE_SUMMARY_REQUIRED = [
    "campaign_id","symbol","campaign_family","entry_family","status",
    "opening_debit","realized_credit_collected","realized_close_cost",
    "net_campaign_basis","campaign_recovered_pct","campaign_cycle_count","event_count",
]
RESEARCH_ROW_REQUIRED = [
    "campaign_id","campaign_family","entry_family","row_source",
    "net_campaign_basis","campaign_recovered_pct",
]
JOURNAL_ROW_REQUIRED = [
    "journal_id","campaign_id","campaign_family","entry_family",
    "path_recommended","journal_status","net_campaign_basis","campaign_recovered_pct",
]

# ─── Value constraints ─────────────────────────────────────────────────────────
VALID_CAMPAIGN_FAMILIES = {"DEEP_ITM_CAMPAIGN"}
VALID_ENTRY_FAMILIES = {"DEEP_ITM_CALENDAR_ENTRY","DEEP_ITM_DIAGONAL_ENTRY"}
VALID_SIDES = {"PUT","CALL"}
VALID_CAMPAIGN_STATES = {"HARVEST_READY","ROLL_READY","DEFENSIVE_ROLL","FLIP_REVIEW",
                          "COLLAPSE_CANDIDATE","BANK_REDUCE","DEFER","BROKEN"}
VALID_CAMPAIGN_ACTIONS = {"HARVEST","ROLL","DEFEND","FLIP","COLLAPSE","BANK_REDUCE","HOLD","CLOSE"}
VALID_PATH_CODES = {"ROLL_SAME_SIDE","DEFENSIVE_ROLL","FLIP_SELECTIVELY",
                     "COLLAPSE_TO_SPREAD","BANK_AND_REDUCE","DEFER_AND_WAIT"}
VALID_PRIORITY_BANDS = {"ACT_NOW","DECIDE_NOW","WATCH_CLOSELY","IMPROVE_LATER"}
VALID_JOURNAL_STATUSES = {"OPEN","APPROVED","EXECUTED","DEFERRED","CANCELLED","CLOSED"}
VALID_ROW_SOURCES = {"QUEUE_ROW","TRADE_RECORD","TRADE_EVENT","LIFECYCLE_DECISION"}
VALID_TICKET_AUTHORITIES = {"AUTO_DRAFT","HUMAN_APPROVAL","HUMAN_EXECUTION"}

# ─── Core helper ──────────────────────────────────────────────────────────────
def _check_fields(obj: dict|Any, required: list[str], label: str) -> list[str]:
    errors=[]
    for f in required:
        v=obj.get(f) if isinstance(obj,dict) else getattr(obj,f,None)
        if v is None:
            errors.append(f"{label}: required field '{f}' is None or missing")
    return errors

def _check_value(val: Any, valid_set: set, field: str, label: str) -> list[str]:
    if val is not None and val not in valid_set:
        return [f"{label}: '{field}' value '{val}' not in allowed set {sorted(valid_set)}"]
    return []

def _get(obj: Any, field: str) -> Any:
    if isinstance(obj,dict): return obj.get(field)
    return getattr(obj,field,None)

# ─── Stage validators ─────────────────────────────────────────────────────────
def validate_scanner_candidate(candidate: dict) -> tuple[bool,list[str]]:
    errors=_check_fields(candidate,SCANNER_CANDIDATE_REQUIRED,"scanner_candidate")
    errors+=_check_value(candidate.get("campaign_family"),VALID_CAMPAIGN_FAMILIES,"campaign_family","scanner_candidate")
    errors+=_check_value(candidate.get("entry_family"),VALID_ENTRY_FAMILIES,"entry_family","scanner_candidate")
    if (candidate.get("entry_cheapness_score") or 0) <= 0:
        errors.append("scanner_candidate: entry_cheapness_score should be positive")
    return len(errors)==0, errors

def validate_enriched_row(row: dict) -> tuple[bool,list[str]]:
    errors=_check_fields(row,ENRICHED_ROW_REQUIRED,"enriched_row")
    errors+=_check_value(row.get("campaign_family"),VALID_CAMPAIGN_FAMILIES,"campaign_family","enriched_row")
    errors+=_check_value(row.get("current_side"),VALID_SIDES,"current_side","enriched_row")
    if (row.get("opening_debit") or 0) < 0:
        errors.append("enriched_row: opening_debit should not be negative")
    if row.get("net_campaign_basis") is not None and row.get("net_campaign_basis") < 0:
        errors.append("enriched_row: net_campaign_basis is negative — verify ledger math")
    return len(errors)==0, errors

def validate_ledger_snapshot(snap: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(snap,LEDGER_SNAPSHOT_REQUIRED,"ledger_snapshot")
    basis=_get(snap,"net_campaign_basis")
    if basis is not None and basis < 0:
        errors.append("ledger_snapshot: net_campaign_basis is negative — verify accounting")
    recovered=_get(snap,"campaign_recovered_pct")
    if recovered is not None and not (0 <= recovered <= 100):
        errors.append(f"ledger_snapshot: campaign_recovered_pct={recovered:.2f} out of range [0,100]")
    # Basis formula check
    od=_get(snap,"opening_debit") or 0; oc=_get(snap,"opening_credit") or 0
    rcc=_get(snap,"realized_credit_collected") or 0; rcc_=_get(snap,"realized_close_cost") or 0
    rp=_get(snap,"repair_debit_paid") or 0
    expected_basis=round(od-oc-rcc+rcc_+rp,4)
    if basis is not None and abs(expected_basis-basis)>0.01:
        errors.append(f"ledger_snapshot: basis formula mismatch — expected {expected_basis:.4f} got {basis:.4f}")
    return len(errors)==0, errors

def validate_lifecycle_decision(decision: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(decision,LIFECYCLE_DECISION_REQUIRED,"lifecycle_decision")
    state=_get(decision,"campaign_state"); action=_get(decision,"campaign_action")
    tt=_get(decision,"selected_transition_type")
    errors+=_check_value(state,VALID_CAMPAIGN_STATES,"campaign_state","lifecycle_decision")
    errors+=_check_value(action,VALID_CAMPAIGN_ACTIONS,"campaign_action","lifecycle_decision")
    if tt is not None: errors+=_check_value(tt,VALID_PATH_CODES,"selected_transition_type","lifecycle_decision")
    urgency=_get(decision,"campaign_urgency")
    if urgency is not None and not (0<=urgency<=100):
        errors.append(f"lifecycle_decision: campaign_urgency={urgency} out of range [0,100]")
    return len(errors)==0, errors

def validate_ranked_path(path: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(path,RANKED_PATH_REQUIRED,"ranked_path")
    pc=_get(path,"path_code")
    errors+=_check_value(pc,VALID_PATH_CODES,"path_code","ranked_path")
    score=_get(path,"path_total_score")
    if score is not None and not (0<=score<=100):
        errors.append(f"ranked_path: path_total_score={score:.2f} out of range [0,100]")
    return len(errors)==0, errors

def validate_queue_row(row: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(row,QUEUE_ROW_REQUIRED,"queue_row")
    bpc=_get(row,"best_path_code"); band=_get(row,"queue_priority_band")
    if bpc is not None: errors+=_check_value(bpc,VALID_PATH_CODES,"best_path_code","queue_row")
    if band is not None: errors+=_check_value(band,VALID_PRIORITY_BANDS,"queue_priority_band","queue_row")
    score=_get(row,"queue_priority_score")
    if score is not None and not (0<=score<=100):
        errors.append(f"queue_row: queue_priority_score={score:.2f} out of range [0,100]")
    return len(errors)==0, errors

def validate_workspace(ws: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(ws,WORKSPACE_REQUIRED_KEYS,"workspace")
    econ=_get(ws,"campaign_economics")
    if isinstance(econ,dict):
        errors+=_check_fields(econ,WORKSPACE_ECONOMICS_REQUIRED,"workspace.campaign_economics")
    rp=_get(ws,"roll_panel")
    if isinstance(rp,dict):
        errors+=_check_fields(rp,WORKSPACE_ROLL_PANEL_REQUIRED,"workspace.roll_panel")
    sel=_get(ws,"selected_path")
    if sel is not None and isinstance(sel,dict):
        pc=sel.get("path_code")
        if pc: errors+=_check_value(pc,VALID_PATH_CODES,"selected_path.path_code","workspace")
    return len(errors)==0, errors

def validate_ticket(ticket: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(ticket,TICKET_REQUIRED,"ticket")
    auth=_get(ticket,"authority")
    errors+=_check_value(auth,VALID_TICKET_AUTHORITIES,"authority","ticket")
    sel=_get(ticket,"selected_path")
    if sel is not None: errors+=_check_value(sel,VALID_PATH_CODES,"selected_path","ticket")
    return len(errors)==0, errors

def validate_trade_summary(summary: dict) -> tuple[bool,list[str]]:
    errors=_check_fields(summary,TRADE_SUMMARY_REQUIRED,"trade_summary")
    basis=summary.get("net_campaign_basis")
    if basis is not None and basis < 0:
        errors.append("trade_summary: net_campaign_basis is negative — verify logger accounting")
    return len(errors)==0, errors

def validate_research_row(row: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(row,RESEARCH_ROW_REQUIRED,"research_row")
    src=_get(row,"row_source")
    errors+=_check_value(src,VALID_ROW_SOURCES,"row_source","research_row")
    return len(errors)==0, errors

def validate_journal_row(row: Any) -> tuple[bool,list[str]]:
    errors=_check_fields(row,JOURNAL_ROW_REQUIRED,"journal_row")
    status=_get(row,"journal_status")
    errors+=_check_value(status,VALID_JOURNAL_STATUSES,"journal_status","journal_row")
    return len(errors)==0, errors

# ─── Full pipeline validator ───────────────────────────────────────────────────
def validate_campaign_pipeline_stage(stage: str, obj: Any) -> tuple[bool,list[str]]:
    """Single dispatch — call with stage name and object."""
    dispatch = {
        "scanner_candidate": validate_scanner_candidate,
        "enriched_row": validate_enriched_row,
        "ledger_snapshot": validate_ledger_snapshot,
        "lifecycle_decision": validate_lifecycle_decision,
        "ranked_path": validate_ranked_path,
        "queue_row": validate_queue_row,
        "workspace": validate_workspace,
        "ticket": validate_ticket,
        "trade_summary": validate_trade_summary,
        "research_row": validate_research_row,
        "journal_row": validate_journal_row,
    }
    fn=dispatch.get(stage)
    if fn is None:
        return False,[f"Unknown stage: '{stage}'"]
    return fn(obj)
