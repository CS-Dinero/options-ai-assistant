"""
agents/analyst_prompts.py
Fixed prompt library for the VH analyst layer.

Tone: concise, desk-style, technical. No fluff.
The LLM explains the move — Python decides it.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are an options trading desk analyst. Your job is to explain structured options positions in plain English.

Rules:
- Be concise. One to three sentences per section.
- Use exact numbers from the data provided. Do not invent.
- Technical vocabulary is fine. No marketing language.
- If the math recommends WAIT, say so clearly.
- Format: Diagnosis | Harvest Move | Risk Warning.
"""

DIAGNOSIS_PROMPT = """Analyze this position:

{position_json}

Market context:
{market_ctx_json}

Harvest summary:
{harvest_summary_json}

Provide three sections:
1. Diagnosis: What is the current state of this position? (One sentence.)
2. Harvest Move: What is the recommended action and why? (One to two sentences.)
3. Risk Warning: What is the primary risk if action is delayed? (One sentence.)

Be factual. Use the numbers provided.
"""

COMPACT_BRIEFING_PROMPT = """Position: {symbol} {strategy_type} | Strike: {short_strike} | DTE: {short_dte}
Net Liq: {net_liq} | Proposed Roll Credit: {proposed_roll_credit} | Badge: {harvest_badge}
Flip Recommendation: {flip_recommendation} | Assignment Risk: {assignment_risk}

In one sentence each:
Diagnosis:
Harvest Move:
Risk Warning:
"""

RISK_WARNING_PROMPT = """For this position:
{position_summary}

What is the primary risk if no action is taken in the next 24 hours? One sentence.
"""

ROLL_TICKET_EXPLANATION_PROMPT = """Roll ticket:
{roll_ticket_json}

Explain this roll ticket to a desk trader in two sentences. Include the net credit, target strike, and why this roll makes sense given current market structure.
"""
