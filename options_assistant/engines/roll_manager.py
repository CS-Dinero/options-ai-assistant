"""
engines/roll_manager.py
Generates structured roll suggestions for open positions.

Handles:
  - Credit spreads (tested or near expiry)
  - Calendars (roll short, convert to diagonal, exit long)

Each suggestion carries the action, urgency, target strikes/DTEs,
and rationale — ready for dashboard display and CSV logging.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Literal, Optional


RollAction = Literal[
    "HOLD", "ROLL_OUT", "ROLL_UP", "ROLL_DOWN",
    "ROLL_OUT_AND_AWAY", "CLOSE",
    "CONVERT_TO_DIAGONAL", "EXIT_OR_ROLL_LONG",
]


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None, "") else d
    except (TypeError, ValueError):
        return d


@dataclass
class RollSuggestion:
    symbol:              str
    strategy:            str
    action:              RollAction
    urgency:             str
    rationale:           str
    current_spot:        float = 0.0
    short_strike:        float = 0.0
    long_strike:         float = 0.0
    short_dte:           int   = 0
    long_dte:            int   = 0
    expected_move:       float = 0.0
    target_short_strike: Optional[float] = None
    target_long_strike:  Optional[float] = None
    target_short_dte:    Optional[int]   = None
    target_long_dte:     Optional[int]   = None
    notes:               str   = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────
# CREDIT SPREAD EVALUATOR
# ─────────────────────────────────────────────

def evaluate_credit_roll(
    *, symbol: str, strategy: str, spot: float,
    short_strike: float, long_strike: float,
    short_dte: int, expected_move: float,
) -> RollSuggestion:
    tested = (
        (strategy in ("bull_put", "bull_put_credit") and spot <= short_strike) or
        (strategy in ("bear_call", "bear_call_credit") and spot >= short_strike)
    )
    near   = short_dte <= 5
    offset = max(round(expected_move * 0.35), 2.0)

    if tested and near:
        if "put" in strategy:
            return RollSuggestion(
                symbol=symbol, strategy=strategy, action="ROLL_OUT_AND_AWAY", urgency="HIGH",
                rationale="Tested and near expiry — roll out in time, move strikes lower.",
                current_spot=spot, short_strike=short_strike, long_strike=long_strike,
                short_dte=short_dte, expected_move=expected_move,
                target_short_strike=round(short_strike - offset, 2),
                target_long_strike=round(long_strike - offset, 2),
                target_short_dte=10,
                notes="Same width preferred. Collect at least 1/3 original credit.",
            )
        return RollSuggestion(
            symbol=symbol, strategy=strategy, action="ROLL_OUT_AND_AWAY", urgency="HIGH",
            rationale="Tested and near expiry — roll out in time, move strikes higher.",
            current_spot=spot, short_strike=short_strike, long_strike=long_strike,
            short_dte=short_dte, expected_move=expected_move,
            target_short_strike=round(short_strike + offset, 2),
            target_long_strike=round(long_strike + offset, 2),
            target_short_dte=10,
        )

    if tested:
        action = "ROLL_DOWN" if "put" in strategy else "ROLL_UP"
        small_offset = max(round(expected_move * 0.25), 2.0)
        if "put" in strategy:
            ts = round(short_strike - small_offset, 2)
            tl = round(long_strike  - small_offset, 2)
        else:
            ts = round(short_strike + small_offset, 2)
            tl = round(long_strike  + small_offset, 2)
        return RollSuggestion(
            symbol=symbol, strategy=strategy, action=action, urgency="MEDIUM",
            rationale="Tested but time remains — adjust strikes further OTM if credit acceptable.",
            current_spot=spot, short_strike=short_strike, long_strike=long_strike,
            short_dte=short_dte, expected_move=expected_move,
            target_short_strike=ts, target_long_strike=tl,
            notes="Close instead if no acceptable credit found.",
        )

    if near:
        return RollSuggestion(
            symbol=symbol, strategy=strategy, action="ROLL_OUT", urgency="MEDIUM",
            rationale="Not tested, but short DTE low — roll out to avoid late-stage gamma.",
            current_spot=spot, short_strike=short_strike, long_strike=long_strike,
            short_dte=short_dte, expected_move=expected_move,
            target_short_strike=short_strike, target_long_strike=long_strike,
            target_short_dte=10,
        )

    return RollSuggestion(
        symbol=symbol, strategy=strategy, action="HOLD", urgency="LOW",
        rationale="Not tested and sufficient DTE — let theta work.",
        current_spot=spot, short_strike=short_strike, long_strike=long_strike,
        short_dte=short_dte, expected_move=expected_move,
    )


# ─────────────────────────────────────────────
# CALENDAR EVALUATOR
# ─────────────────────────────────────────────

def evaluate_calendar_roll(
    *, symbol: str, spot: float, strike: float,
    short_dte: int, long_dte: int, expected_move: float,
) -> RollSuggestion:
    dist   = abs(spot - strike)
    broken = dist > expected_move
    convert_zone = (expected_move * 0.35) <= dist < expected_move
    long_exit = long_dte <= 35

    if long_exit:
        return RollSuggestion(
            symbol=symbol, strategy="calendar", action="EXIT_OR_ROLL_LONG", urgency="HIGH",
            rationale=f"Long leg at {long_dte} DTE — in 35 DTE exit window.",
            current_spot=spot, short_strike=strike, long_strike=strike,
            short_dte=short_dte, long_dte=long_dte, expected_move=expected_move,
            target_short_dte=7, target_long_dte=55,
            notes="Rebuild near ATM if environment still supports time spreads.",
        )

    if broken:
        return RollSuggestion(
            symbol=symbol, strategy="calendar", action="CLOSE", urgency="HIGH",
            rationale="Price beyond expected move — original pin assumption broken.",
            current_spot=spot, short_strike=strike, long_strike=strike,
            short_dte=short_dte, long_dte=long_dte, expected_move=expected_move,
        )

    if convert_zone:
        tgt = (round(strike + expected_move * 0.35, 2)
               if spot > strike else round(strike - expected_move * 0.35, 2))
        return RollSuggestion(
            symbol=symbol, strategy="calendar", action="CONVERT_TO_DIAGONAL", urgency="MEDIUM",
            rationale="Price drifted — convert short leg directionally, keep long anchor.",
            current_spot=spot, short_strike=strike, long_strike=strike,
            short_dte=short_dte, long_dte=long_dte, expected_move=expected_move,
            target_short_strike=tgt, target_long_strike=strike,
            target_short_dte=7, target_long_dte=long_dte,
        )

    if short_dte <= 5:
        return RollSuggestion(
            symbol=symbol, strategy="calendar", action="ROLL_OUT", urgency="MEDIUM",
            rationale="Short leg near expiry while thesis intact — re-sell at same strike.",
            current_spot=spot, short_strike=strike, long_strike=strike,
            short_dte=short_dte, long_dte=long_dte, expected_move=expected_move,
            target_short_strike=strike, target_long_strike=strike,
            target_short_dte=7, target_long_dte=long_dte,
        )

    return RollSuggestion(
        symbol=symbol, strategy="calendar", action="HOLD", urgency="LOW",
        rationale="Calendar centered and within valid management window.",
        current_spot=spot, short_strike=strike, long_strike=strike,
        short_dte=short_dte, long_dte=long_dte, expected_move=expected_move,
    )


# ─────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────

def evaluate_roll_for_position(pos: dict[str, Any]) -> dict[str, Any]:
    strategy = str(pos.get("strategy_type", pos.get("strategy", ""))).lower()
    sym      = str(pos.get("symbol", ""))
    spot     = _sf(pos.get("live_spot") or pos.get("spot"))
    em       = _sf(pos.get("expected_move"))
    short_k  = _sf(pos.get("short_strike"))
    long_k   = _sf(pos.get("long_strike"))
    s_dte    = _si(pos.get("short_dte"))
    l_dte    = _si(pos.get("long_dte"))

    if strategy in ("bull_put", "bull_put_credit", "bear_call", "bear_call_credit"):
        return evaluate_credit_roll(
            symbol=sym, strategy=strategy, spot=spot,
            short_strike=short_k, long_strike=long_k,
            short_dte=s_dte, expected_move=em,
        ).to_dict()

    if strategy in ("calendar", "diagonal"):
        return evaluate_calendar_roll(
            symbol=sym, spot=spot, strike=short_k,
            short_dte=s_dte, long_dte=l_dte, expected_move=em,
        ).to_dict()

    # Decision from cal/diag lifecycle engine
    decision = pos.get("decision", {})
    if isinstance(decision, dict):
        action = decision.get("action", "HOLD")
        return RollSuggestion(
            symbol=sym, strategy=strategy, action=action,  # type: ignore
            urgency=decision.get("urgency", "LOW"),
            rationale=decision.get("rationale", ""),
            current_spot=spot, short_strike=short_k, long_strike=long_k,
            short_dte=s_dte, long_dte=l_dte, expected_move=em,
        ).to_dict()

    return RollSuggestion(
        symbol=sym, strategy=strategy, action="HOLD", urgency="LOW",
        rationale="No roll policy defined for this strategy.",
    ).to_dict()


def build_roll_suggestions(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [evaluate_roll_for_position(p) for p in positions]
