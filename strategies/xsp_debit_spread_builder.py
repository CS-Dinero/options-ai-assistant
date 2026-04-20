"""strategies/xsp_debit_spread_builder.py — XSP bull call / bear put debit spread builder."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(slots=True)
class XSPDebitSpreadCandidate:
    ticker: str
    structure: str        # BULL_CALL_SPREAD | BEAR_PUT_SPREAD
    option_type: str
    long_strike: float
    short_strike: float
    expiry: str
    long_dte: int
    long_delta: float
    short_delta: float
    long_mid: float
    short_mid: float
    debit: float
    width: float
    max_profit: float
    max_loss: float
    reward_risk: float
    liquidity_score: float
    candidate_score: float
    notes: list[str] = field(default_factory=list)

def build_xsp_debit_spread(
    ticker: str,
    option_type: str,
    long_leg,
    short_leg,
    liquidity_score: float,
    regime_alignment_score: float,
) -> XSPDebitSpreadCandidate | None:
    ot        = option_type.upper()
    structure = "BULL_CALL_SPREAD" if ot == "CALL" else "BEAR_PUT_SPREAD"

    long_mid  = float(long_leg.mid)
    short_mid = float(short_leg.mid)
    debit     = round(long_mid - short_mid, 4)
    if debit <= 0:
        return None

    width      = round(abs(float(long_leg.strike) - float(short_leg.strike)), 4)
    max_profit = round((width - debit) * 100, 2)
    max_loss   = round(debit * 100, 2)
    rr         = round(max_profit / max(0.01, max_loss), 4)

    candidate_score = round(
        min(100.0, rr * 50)      * 0.40
        + liquidity_score        * 0.35
        + regime_alignment_score * 0.25,
        2,
    )

    return XSPDebitSpreadCandidate(
        ticker=ticker, structure=structure, option_type=ot,
        long_strike=float(long_leg.strike), short_strike=float(short_leg.strike),
        expiry=str(long_leg.expiry), long_dte=int(getattr(long_leg, "dte", 0)),
        long_delta=round(abs(float(long_leg.delta or 0)), 4),
        short_delta=round(abs(float(short_leg.delta or 0)), 4),
        long_mid=round(long_mid, 4), short_mid=round(short_mid, 4),
        debit=debit, width=width, max_profit=max_profit, max_loss=max_loss,
        reward_risk=rr, liquidity_score=round(liquidity_score, 2),
        candidate_score=candidate_score,
        notes=[f"debit={debit:.2f}", f"rr={rr:.2f}", f"width={width:.1f}"],
    )
