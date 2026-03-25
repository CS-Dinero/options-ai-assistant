"""analyst/rejection_explainer.py — Summarizes why top alternatives were rejected."""
from __future__ import annotations
from typing import Any
from collections import Counter

def explain_rejections(rejected: list[dict[str,Any]]) -> dict[str,Any]:
    if not rejected:
        return {"rejection_summary":"No meaningful rejected alternatives recorded.","top_rejection_reasons":[]}
    reasons=[str(c.get("reason","Unknown")) for c in rejected]
    top=Counter(reasons).most_common(3)
    parts=[f"{r} ({n})" for r,n in top]
    return {"rejection_summary":"Main alternatives rejected due to: "+"; ".join(parts)+".","top_rejection_reasons":parts}
