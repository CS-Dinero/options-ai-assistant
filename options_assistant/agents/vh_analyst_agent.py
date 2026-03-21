"""
agents/vh_analyst_agent.py
LLM wrapper for VH position analysis.

Python decides. LLM explains.

Uses Claude via Anthropic API (available in Streamlit artifacts).
Falls back to structured template output if API unavailable.
"""
from __future__ import annotations

import json
from typing import Any

from agents.analyst_prompts import (
    SYSTEM_PROMPT, DIAGNOSIS_PROMPT, COMPACT_BRIEFING_PROMPT, RISK_WARNING_PROMPT
)


def _js(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, default=str)
    except Exception:
        return str(obj)


def _template_fallback(position: dict, harvest_summary: dict, market_ctx: dict) -> dict[str, Any]:
    """Return a structured template response when LLM is unavailable."""
    sym    = position.get("symbol", "?")
    struct = position.get("strategy_type", "calendar")
    badge  = harvest_summary.get("harvest_badge", "—")
    credit = harvest_summary.get("proposed_roll_credit", 0)
    action = harvest_summary.get("roll_action", "WAIT")
    flip   = harvest_summary.get("flip_recommendation", "HOLD_STRUCTURE")
    assign = harvest_summary.get("assignment_risk", False)

    diagnosis = (
        f"{sym} {struct} is in {'harvest-ready' if badge in ('GOLD','GREEN') else 'hold'} state "
        f"with {harvest_summary.get('net_liq', 0):+.0f} net liq."
    )
    harvest_move = (
        f"Roll to collect ${credit:.2f} net credit ({action})."
        if credit >= 0.01 else "No creditworthy roll available — hold or wait."
    )
    risk_warning = (
        "Assignment risk present — act before expiry." if assign
        else f"{'Flip recommended: ' + flip if flip != 'HOLD_STRUCTURE' else 'Hold current structure.'}"
    )

    return {
        "diagnosis":     diagnosis,
        "harvest_move":  harvest_move,
        "risk_warning":  risk_warning,
        "confidence":    "TEMPLATE",
        "full_text":     f"Diagnosis: {diagnosis}\nHarvest Move: {harvest_move}\nRisk Warning: {risk_warning}",
        "source":        "template_fallback",
    }


async def analyze_position_async(
    position:         dict[str, Any],
    market_ctx:       dict[str, Any],
    harvest_summary:  dict[str, Any],
) -> dict[str, Any]:
    """
    Async version for Streamlit artifact contexts.
    Falls back to template if fetch fails.
    """
    try:
        prompt = DIAGNOSIS_PROMPT.format(
            position_json=_js(position),
            market_ctx_json=_js(market_ctx),
            harvest_summary_json=_js(harvest_summary),
        )
        response = await _call_claude_async(prompt)
        return _parse_response(response, position, harvest_summary)
    except Exception:
        return _template_fallback(position, harvest_summary, market_ctx)


async def _call_claude_async(prompt: str) -> str:
    """Call Anthropic API asynchronously."""
    import httpx
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            timeout=15,
        )
        data = resp.json()
        return data["content"][0]["text"]


def analyze_position_sync(
    position:        dict[str, Any],
    market_ctx:      dict[str, Any],
    harvest_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Synchronous version for non-async contexts.
    Falls back to template if API unavailable.
    """
    try:
        import requests
        prompt = DIAGNOSIS_PROMPT.format(
            position_json=_js(position),
            market_ctx_json=_js(market_ctx),
            harvest_summary_json=_js(harvest_summary),
        )
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = requests.post("https://api.anthropic.com/v1/messages",
                             json=payload, timeout=15)
        text = resp.json()["content"][0]["text"]
        return _parse_response(text, position, harvest_summary)
    except Exception:
        return _template_fallback(position, harvest_summary, market_ctx)


def _parse_response(text: str, position: dict, harvest_summary: dict) -> dict[str, Any]:
    """Parse the three-section analyst response."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    diagnosis = harvest_move = risk_warning = ""
    for line in lines:
        ll = line.lower()
        if ll.startswith("diagnosis"):
            diagnosis = line.split(":", 1)[-1].strip()
        elif ll.startswith("harvest"):
            harvest_move = line.split(":", 1)[-1].strip()
        elif ll.startswith("risk"):
            risk_warning = line.split(":", 1)[-1].strip()
    if not diagnosis:
        diagnosis = lines[0] if lines else "No diagnosis available."
    if not harvest_move and len(lines) > 1:
        harvest_move = lines[1]
    if not risk_warning and len(lines) > 2:
        risk_warning = lines[-1]
    return {
        "diagnosis":    diagnosis,
        "harvest_move": harvest_move,
        "risk_warning": risk_warning,
        "confidence":   "LLM",
        "full_text":    text,
        "source":       "claude",
    }


def analyze_position(
    position:        dict[str, Any],
    market_ctx:      dict[str, Any],
    harvest_summary: dict[str, Any],
    use_llm:         bool = False,
) -> dict[str, Any]:
    """
    Primary entry point. use_llm=True sends to Claude; False uses template.
    Dashboard always passes use_llm based on user toggle.
    """
    if use_llm:
        return analyze_position_sync(position, market_ctx, harvest_summary)
    return _template_fallback(position, harvest_summary, market_ctx)
