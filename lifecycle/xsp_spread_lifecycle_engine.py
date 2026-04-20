"""lifecycle/xsp_spread_lifecycle_engine.py — HOLD / HARVEST / FORCE_CLOSE for XSP spreads."""
from __future__ import annotations
from dataclasses import dataclass, field
from lifecycle.xsp_lifecycle_rules import (
    XSPLifecycleConfig, XSP_STATE_HOLD, XSP_STATE_HARVEST, XSP_STATE_FORCE_CLOSE
)

@dataclass(slots=True)
class XSPSpreadLifecycleDecision:
    ticker: str; structure: str; state: str; action: str
    urgency: int; reason: str; profit_percent: float; dte: int
    short_strike: float | None; distance_to_strike: float | None
    expected_move: float | None; notes: list[str] = field(default_factory=list)

def evaluate_xsp_spread_lifecycle(
    ticker: str,
    structure: str,
    profit_percent: float,
    dte: int,
    short_strike: float | None = None,
    spot_price: float | None = None,
    expected_move: float | None = None,
    cfg: XSPLifecycleConfig | None = None,
) -> XSPSpreadLifecycleDecision:
    cfg = cfg or XSPLifecycleConfig()

    distance_to_strike = None
    threatened = False
    if short_strike is not None and spot_price is not None:
        distance_to_strike = abs(float(spot_price) - float(short_strike))
        if expected_move is not None:
            threatened = distance_to_strike < cfg.threatened_em_fraction * float(expected_move)

    # Force close: near expiry + threatened
    if dte <= cfg.force_exit_dte and threatened:
        return XSPSpreadLifecycleDecision(
            ticker=ticker, structure=structure, state=XSP_STATE_FORCE_CLOSE,
            action="CLOSE", urgency=95,
            reason="Threatened spread in close window — force exit.",
            profit_percent=profit_percent, dte=dte,
            short_strike=short_strike, distance_to_strike=distance_to_strike,
            expected_move=expected_move,
        )

    # Harvest: profit target reached
    if profit_percent >= cfg.profit_take_target:
        return XSPSpreadLifecycleDecision(
            ticker=ticker, structure=structure, state=XSP_STATE_HARVEST,
            action="CLOSE", urgency=75,
            reason=f"Profit target {cfg.profit_take_target*100:.0f}% reached.",
            profit_percent=profit_percent, dte=dte,
            short_strike=short_strike, distance_to_strike=distance_to_strike,
            expected_move=expected_move,
        )

    # Force close: DTE window regardless
    if dte <= cfg.force_exit_dte:
        return XSPSpreadLifecycleDecision(
            ticker=ticker, structure=structure, state=XSP_STATE_FORCE_CLOSE,
            action="CLOSE", urgency=85,
            reason=f"Force-close window reached — {dte} DTE.",
            profit_percent=profit_percent, dte=dte,
            short_strike=short_strike, distance_to_strike=distance_to_strike,
            expected_move=expected_move,
        )

    # Early harvest at minimum
    if profit_percent >= cfg.profit_take_min:
        return XSPSpreadLifecycleDecision(
            ticker=ticker, structure=structure, state=XSP_STATE_HARVEST,
            action="CONSIDER_CLOSE", urgency=50,
            reason=f"Profit above minimum {cfg.profit_take_min*100:.0f}% — eligible to harvest.",
            profit_percent=profit_percent, dte=dte,
            short_strike=short_strike, distance_to_strike=distance_to_strike,
            expected_move=expected_move,
        )

    return XSPSpreadLifecycleDecision(
        ticker=ticker, structure=structure, state=XSP_STATE_HOLD,
        action="HOLD", urgency=20,
        reason="No lifecycle action required.",
        profit_percent=profit_percent, dte=dte,
        short_strike=short_strike, distance_to_strike=distance_to_strike,
        expected_move=expected_move,
    )
