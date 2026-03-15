"""
utils/printers.py
All console output formatting.
No logic here — pure presentation layer.
"""

from calculator.trade_scoring import get_score_breakdown
from config.settings          import SCORE_STRONG, SCORE_TRADABLE


STRATEGY_LABELS = {
    "bear_call":       "Bear Call Credit Spread",
    "bull_put":        "Bull Put Credit Spread",
    "bull_call_debit": "Bull Call Debit Spread",
    "bear_put_debit":  "Bear Put Debit Spread",
    "calendar":        "ATM Calendar Spread",
    "bull_diagonal":   "Bull Call Diagonal",
    "bear_diagonal":   "Bear Put Diagonal",
}


def score_label(score: int) -> str:
    if score >= SCORE_STRONG:
        return "★ STRONG"
    elif score >= SCORE_TRADABLE:
        return "○ TRADABLE"
    return "✗ SKIP"


def print_market_summary(market: dict, derived: dict) -> None:
    spot  = market["spot_price"]
    em    = derived["expected_move"]
    ratio = derived["em_atr_ratio"]

    regime_label = (
        "range-bound" if ratio > 3
        else "breakout risk" if ratio < 2
        else "balanced"
    )

    print("=" * 60)
    print(f"  OPTIONS AI ASSISTANT — {market['symbol']} ANALYSIS")
    print("=" * 60)
    print(f"  Spot Price     : ${spot:.2f}")
    print(f"  Expected Move  : ±${em:.2f}  ({derived['em_method']})")
    print(f"  Upper EM       : ${derived['upper_em']:.2f}")
    print(f"  Lower EM       : ${derived['lower_em']:.2f}")
    print(f"  ATR (14)       : ${market['atr_14']:.2f}  trend={derived['atr_trend']}")
    print(f"  EM/ATR Ratio   : {ratio:.2f}  ({regime_label})")
    print(f"  IV Percentile  : {market['iv_percentile']:.0f}  regime={derived['iv_regime']}")
    print(f"  Term Structure : {derived['term_structure']}  (slope={derived['term_slope']:.1f})")
    print(f"  Skew (25Δ)     : {derived.get('skew_value', 'N/A')}  state={derived['skew_state']}")
    print(f"  Gamma Regime   : {derived['gamma_regime']}")
    if derived.get("gamma_flip"):
        print(f"  Gamma Flip     : ${derived['gamma_flip']:.0f}")
    if derived.get("gamma_trap"):
        print(f"  Gamma Trap     : ${derived['gamma_trap']:.0f}")
    print()


def print_trade(rank: int, t: dict) -> None:
    label  = STRATEGY_LABELS.get(t["strategy_type"], t["strategy_type"])
    credit = t["entry_debit_credit"]

    print(f"  ─── Trade #{rank}  {score_label(t['confidence_score'])} ───")
    print(f"  Strategy    : {label}  ({t['direction'].upper()})")
    print(f"  Symbol      : {t['symbol']}")
    print(f"  Expiration  : {t['short_expiration']}")

    if t["strategy_type"] in ("bear_call", "bull_put"):
        print(f"  Short Strike: ${t['short_strike']:.0f}  Δ={t['short_delta']:.2f}")
        print(f"  Long Strike : ${t['hedge_strike']:.0f}  Δ={t['hedge_delta']:.2f}")
        print(f"  Width       : ${t['width']:.0f}")
        print(f"  Credit      : ${credit:.2f}  (${credit*100:.0f}/contract)")
    else:
        print(f"  Long Strike : ${t['long_strike']:.0f}  Δ={t['long_delta']:.2f}")
        print(f"  Short Strike: ${t['short_strike']:.0f}  Δ={t['short_delta']:.2f}")
        print(f"  Width       : ${t['width']:.0f}")
        print(f"  Debit       : ${abs(credit):.2f}  (${abs(credit)*100:.0f}/contract)")

    print(f"  Max Profit  : ${t['max_profit']:.0f}/contract")
    print(f"  Max Loss    : ${t['max_loss']:.0f}/contract")
    print(f"  Target Exit : ${t['target_exit_value']:.2f}")
    print(f"  Stop Level  : ${t['stop_value']:.2f}")
    print(f"  Prob ITM    : {t['prob_itm_proxy']*100:.0f}%  Touch: {t['prob_touch_proxy']*100:.0f}%")
    print(f"  Contracts   : {t['contracts']}  (${t['max_loss'] * t['contracts']:.0f} total risk)")
    print(f"  Score       : {t['confidence_score']}/100  {score_label(t['confidence_score'])}")
    print(f"  Notes       : {t['notes']}")
    print()


def print_all_trades(ranked: list[dict], top_n: int = 3) -> None:
    print(f"  TOP {min(len(ranked), top_n)} RANKED TRADES")
    print()
    if not ranked:
        print("  No valid candidates generated. Check chain data or EM boundaries.")
        return
    for i, trade in enumerate(ranked[:top_n], start=1):
        print_trade(i, trade)


def print_score_breakdown(top_trade: dict, derived: dict) -> None:
    """Show factor-level scoring for one trade — makes the logic auditable."""
    breakdown = get_score_breakdown(top_trade, derived)

    print("  ─── Score Breakdown (Trade #1) ───")
    for name, info in breakdown.items():
        raw     = info["raw"]
        wt      = info["weight"]
        contrib = info["contrib"]
        raw_str     = "N/A" if raw is None else f"{raw:.2f}"
        contrib_str = "—"   if contrib is None else f"{contrib:.1f} pts"
        print(f"  {name:<18}: raw={raw_str:<6}  weight={wt:<3}  contrib={contrib_str}")

    print(f"  {'TOTAL':<18}: {top_trade['confidence_score']}/100")
    print()
