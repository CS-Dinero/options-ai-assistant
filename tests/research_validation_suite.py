"""tests/research_validation_suite.py — Research stats, ranking, and governance tests."""
from __future__ import annotations
from tests.assertion_helpers import assert_true, assert_equal
from research.playbook_stats_engine import compute_playbook_stats
from research.playbook_rank_engine import build_playbook_rankings
from research.playbook_status_engine import assign_playbook_status
from research.playbook_governance_engine import apply_playbook_governance

def _pass(t): return {"test":t,"status":"PASS"}

def run_research_validation_suite() -> list[dict]:
    results=[]
    rows = [
        {"playbook_code":"PB001","outcome_score":78,"transition_credit":1.1,
         "campaign_basis_before":5.0,"campaign_basis_after":3.9,
         "recovered_pct_before":40,"recovered_pct_after":53,
         "fill_score":75,"slippage_dollars":-0.05,"avg_path_score":72,"worst_path_score":50,"success":True},
        {"playbook_code":"PB001","outcome_score":74,"transition_credit":1.0,
         "campaign_basis_before":4.5,"campaign_basis_after":3.5,
         "recovered_pct_before":44,"recovered_pct_after":56,
         "fill_score":78,"slippage_dollars":-0.03,"avg_path_score":70,"worst_path_score":49,"success":True},
    ]
    stats = compute_playbook_stats(rows)
    assert_true("PB001" in stats["by_playbook"], "stats includes PB001")
    rankings = build_playbook_rankings(stats)
    assert_true("PB001" in rankings["rankings"], "rankings includes PB001")
    statuses = assign_playbook_status(rankings, stats)
    assert_true("PB001" in statuses["playbook_statuses"], "status assigned to PB001")
    results.append(_pass("research ranking pipeline"))

    # Governance: weak sample softens status
    from research.playbook_policy_registry import build_playbook_policy_registry
    from playbooks.playbook_registry import PLAYBOOKS
    from research.playbook_regime_dependency_engine import analyze_playbook_regime_dependency
    from research.playbook_symbol_dependency_engine import analyze_playbook_symbol_dependency
    rd = analyze_playbook_regime_dependency(rows); sd = analyze_playbook_symbol_dependency(rows)
    policy_reg = build_playbook_policy_registry(PLAYBOOKS, statuses, rd, sd)
    governed = apply_playbook_governance(policy_reg, rankings)
    assert_true("PB001" in governed["governed_playbook_policy_registry"], "governance covers PB001")
    results.append(_pass("playbook governance"))

    return results
