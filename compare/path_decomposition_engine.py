"""compare/path_decomposition_engine.py — Expands each path into a short operational sequence."""
from __future__ import annotations
from typing import Any

DECOMPOSITIONS: dict = {
    "CONTINUE_HARVEST":  {"steps":["Keep current campaign shape","Harvest next short premium","Reassess rollability after decay"]},
    "ROLL_SAME_SIDE":    {"steps":["Roll short same side","Reduce basis through additional credit","Preserve future harvestability"]},
    "COLLAPSE_TO_SPREAD":{"steps":["Simplify current structure","Reduce complexity and tail churn","Manage as defined-risk premium position"]},
    "BANK_AND_REDUCE":   {"steps":["Lock in campaign progress","Reduce capital tied to structure","Limit future execution friction"]},
    "DEFER_AND_WAIT":    {"steps":["Do not execute immediately","Wait for timing/surface improvement","Re-evaluate later with better conditions"]},
}

def decompose_path(path_code: str, row: dict[str,Any]) -> dict[str,Any]:
    d=DECOMPOSITIONS.get(path_code,DECOMPOSITIONS["DEFER_AND_WAIT"])
    return {"path_code":path_code,"steps":d["steps"]}
