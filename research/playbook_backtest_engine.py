"""research/playbook_backtest_engine.py — Full backtest orchestrator."""
from __future__ import annotations
from typing import Any
from research.research_dataset_builder import build_research_dataset
from research.playbook_scenario_replayer import replay_playbook_scenarios
from research.playbook_stats_engine import compute_playbook_stats

def run_playbook_backtest(evaluated_journals, slippage_entries=None,
                          playbook_code=None, symbol=None, regime_filter=None) -> dict[str,Any]:
    dataset  = build_research_dataset(evaluated_journals, slippage_entries)
    filtered = replay_playbook_scenarios(dataset, playbook_code=playbook_code,
                                          symbol=symbol, regime_filter=regime_filter)
    stats    = compute_playbook_stats(filtered)
    return {"dataset_count":len(dataset),"filtered_count":len(filtered),"stats":stats,"rows":filtered}
