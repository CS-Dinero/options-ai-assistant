"""doctrine/tradeoff_policy_engine.py — Resolves competing priorities via charter ordering."""
from __future__ import annotations
from typing import Any

def resolve_tradeoff(charter: dict[str,Any], left_priority: str, right_priority: str) -> str:
    order=charter.get("tradeoff_order",[])
    li=order.index(left_priority)  if left_priority  in order else 999
    ri=order.index(right_priority) if right_priority in order else 999
    return left_priority if li<=ri else right_priority

def resolve_tradeoff_with_reason(charter: dict[str,Any], left: str, right: str) -> dict[str,Any]:
    winner=resolve_tradeoff(charter,left,right)
    return {"winner":winner,"loser":right if winner==left else left,
            "reason":f"'{winner}' has higher charter priority than '{right if winner==left else left}'"}
