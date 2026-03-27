"""compare/path_tradeoff_engine.py — Explains tradeoffs between paths."""
from __future__ import annotations
from typing import Any

NOTES: dict = {
    "CONTINUE_HARVEST":  "Higher recovery potential, but more execution dependence and campaign complexity.",
    "ROLL_SAME_SIDE":    "Strong recovery path if rollability remains healthy, but still depends on decent execution.",
    "COLLAPSE_TO_SPREAD":"Lower complexity and cleaner capital usage, but gives up future harvest optionality.",
    "BANK_AND_REDUCE":   "Best simplicity and capital relief, but may leave recovery upside on the table.",
    "DEFER_AND_WAIT":    "Best when execution conditions are weak, but slows recovery and may reduce queue productivity.",
}

def explain_path_tradeoffs(scored_paths: list[dict[str,Any]]) -> list[dict[str,Any]]:
    return [{"path_code":p["path_code"],"tradeoff_note":NOTES.get(p["path_code"],"No tradeoff note.")} for p in scored_paths]
