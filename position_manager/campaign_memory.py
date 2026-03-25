"""
position_manager/campaign_memory.py
Ledger for each position's full lifecycle — from entry to final exit.
Tracks cumulative credits/debits, harvest cycles, flips, rebuilds, and basis.
"""
from __future__ import annotations
from typing import Any
import uuid

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def initialize_campaign_memory(position_row: dict[str,Any]) -> dict[str,Any]:
    entry_cost = _sf(position_row.get("entry_net_debit")
                     or position_row.get("entry_debit_credit")
                     or position_row.get("entry_price")
                     or position_row.get("avg_price"))
    pos_id = str(position_row.get("trade_id") or position_row.get("id") or uuid.uuid4())
    return {
        "campaign_id":                str(position_row.get("campaign_id") or pos_id),
        "root_position_id":           pos_id,
        "symbol":                     str(position_row.get("symbol","")),
        "original_structure_type":    str(position_row.get("strategy_type","calendar")),
        "original_entry_cost":        abs(entry_cost),
        "cumulative_realized_credit": 0.0,
        "cumulative_realized_debit":  0.0,
        "cumulative_fees":            0.0,
        "harvest_cycles":             0,
        "flip_count":                 0,
        "rebuild_count":              0,
        "transition_count":           0,
        "latest_structure_type":      str(position_row.get("strategy_type","")),
        "latest_position_id":         pos_id,
        "lineage":                    [],
        "status":                     "OPEN",
    }

def append_campaign_event(memory: dict[str,Any], event: dict[str,Any]) -> dict[str,Any]:
    m = dict(memory)
    m.setdefault("lineage",[]).append(event)
    m["latest_structure_type"] = event.get("new_structure_type", m.get("latest_structure_type",""))
    m["latest_position_id"]    = event.get("position_id", m.get("latest_position_id",""))
    m["transition_count"]      = int(_sf(m.get("transition_count")))+1
    action = str(event.get("action",""))
    if "HARVEST" in action or event.get("event_class")=="HARVEST":
        m["harvest_cycles"] = int(_sf(m.get("harvest_cycles")))+1
    if "FLIP" in action:
        m["flip_count"] = int(_sf(m.get("flip_count")))+1
    if event.get("rebuild_class")=="REPLACE_LONG":
        m["rebuild_count"] = int(_sf(m.get("rebuild_count")))+1
    m["cumulative_realized_credit"] = round(_sf(m.get("cumulative_realized_credit"))+_sf(event.get("realized_credit")),4)
    m["cumulative_realized_debit"]  = round(_sf(m.get("cumulative_realized_debit"))+_sf(event.get("realized_debit")),4)
    m["cumulative_fees"]            = round(_sf(m.get("cumulative_fees"))+_sf(event.get("fees")),4)
    return m

def compute_campaign_net_basis(memory: dict[str,Any]) -> float:
    return round(
        _sf(memory.get("original_entry_cost"))
        - _sf(memory.get("cumulative_realized_credit"))
        + _sf(memory.get("cumulative_realized_debit"))
        + _sf(memory.get("cumulative_fees")), 4)

def compute_recovered_pct(memory: dict[str,Any]) -> float:
    orig = _sf(memory.get("original_entry_cost"))
    if orig <= 0: return 0.0
    recovered = (_sf(memory.get("cumulative_realized_credit"))
                 - _sf(memory.get("cumulative_realized_debit"))
                 - _sf(memory.get("cumulative_fees")))
    return round((recovered/orig)*100, 2)
