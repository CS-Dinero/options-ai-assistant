"""tests/fixture_factory.py — Deterministic mock objects for test suites."""
from __future__ import annotations
from typing import Any

def make_position_row(**overrides) -> dict[str,Any]:
    row = {
        "id":"pos_001","trade_id":"pos_001","symbol":"SPY","bias":"bullish_neutral",
        "strategy_type":"deep_itm_call_calendar","structure_type":"deep_itm_call_calendar",
        "campaign_id":"camp_001","campaign_net_basis":4.80,"campaign_recovered_pct":42.0,
        "campaign_harvest_cycles":2,"campaign_flip_count":0,"campaign_rebuild_count":0,
        "unrealized_pnl":1.25,"contracts":1,"bot_priority":"P3","status":"OPEN",
        "recommended_contract_add":1,
        "long_leg":{"option_type":"call","expiry":"2026-06-19","strike":590.0,"delta":0.84,
                    "dte":86,"bid":24.2,"ask":24.8,"mid":24.5,"iv":0.19},
        "short_leg":{"option_type":"call","expiry":"2026-04-17","strike":610.0,"delta":0.31,
                     "dte":23,"bid":4.1,"ask":4.3,"mid":4.2,"iv":0.21},
        "transition_action":"FLIP_TO_CALL_DIAGONAL","transition_net_credit":1.20,
        "transition_future_roll_score":76.0,"transition_structure_score":80.0,
        "transition_campaign_improvement_score":78.0,"transition_avg_path_score":74.0,
        "transition_worst_path_score":51.0,"transition_allocator_score":73.0,
        "transition_recycling_score":60.0,"transition_timing_score":72.0,
        "transition_execution_surface_score":71.0,"transition_portfolio_fit_ok":True,
        "transition_timing_ok":True,"transition_execution_surface_ok":True,
        "transition_is_credit_approved":True,"transition_improves_campaign":True,
        "transition_path_robust":True,"transition_execution_policy":"FULL_NOW",
        "transition_queue_score":79.0,"transition_liquidity_score":72.0,
        "transition_rebuild_class":"KEEP_LONG","transition_latest_fill_score":80.0,
        "playbook_code":"PB001","playbook_name":"Deep ITM Calendar → Same-Side Diagonal Harvest",
        "playbook_family":"DIAGONAL_HARVEST","playbook_status":"WATCHLIST",
        "playbook_queue_bias":0.0,"capital_commitment_decision":"ALLOW_NORMAL",
        "capital_commitment_ok":True,"symbol_concurrency_ok":True,
        "playbook_concurrency_ok":True,"transition_final_contract_add":1,"state":"APPROVED",
    }
    row.update(overrides)
    return row

def make_campaign_memory(**overrides) -> dict[str,Any]:
    m = {"campaign_id":"camp_001","root_position_id":"pos_001","symbol":"SPY",
         "original_structure_type":"deep_itm_call_calendar","original_entry_cost":8.20,
         "cumulative_realized_credit":3.40,"cumulative_realized_debit":0.0,"cumulative_fees":0.0,
         "harvest_cycles":2,"flip_count":0,"rebuild_count":0,"transition_count":2,
         "latest_structure_type":"call_diagonal","latest_position_id":"pos_001",
         "lineage":[],"status":"OPEN"}
    m.update(overrides); return m

def make_session_context(**overrides) -> dict[str,Any]:
    ctx = {"user_id":"user_001","display_name":"Test Operator","roles":["ANALYST"],"active_role":"ANALYST"}
    ctx.update(overrides); return ctx

def make_policy_bundle(**overrides) -> dict[str,Any]:
    bundle = {
        "playbook_policy_registry":{
            "PB001":{"status":"WATCHLIST","queue_bias":1.0},
            "PB002":{"status":"LIMITED_USE","queue_bias":-2.0},
        },
        "playbook_capital_policy":{
            "PROMOTED":   {"size_multiplier":1.15,"max_symbol_concurrency":3,"max_playbook_concurrency":4},
            "WATCHLIST":  {"size_multiplier":1.00,"max_symbol_concurrency":2,"max_playbook_concurrency":3},
            "LIMITED_USE":{"size_multiplier":0.65,"max_symbol_concurrency":1,"max_playbook_concurrency":2},
            "DEMOTED":    {"size_multiplier":0.35,"max_symbol_concurrency":1,"max_playbook_concurrency":1},
        },
        "symbol_concurrency_overrides":{},"execution_policy_overrides":{},
        "surface_threshold_override":65.0,
    }
    bundle.update(overrides); return bundle
