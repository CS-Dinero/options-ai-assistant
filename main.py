"""
main.py
Options AI Assistant — orchestration entry point.

Pipeline:
  1. Load market context + option chain (mock or live)
  2. Compute derived analytics
  3. Generate trade candidates
  4. Score and rank
  5. Print market summary + top trades
  6. Run validation + normalization tests

DATA_MODE controls the data source:
  "mock"    — static SPY data (default, no API keys needed)
  "tradier" — live Tradier API (set TRADIER_TOKEN + TRADIER_BASE_URL env vars)
  "massive" — live Massive (Polygon) API (set MASSIVE_API_KEY env var)

Switching to live Tradier data:
  export TRADIER_TOKEN=your_token_here
  export TRADIER_BASE_URL=https://sandbox.tradier.com/v1
  Then set DATA_MODE = "tradier" below and run: python main.py SPY
"""

import sys
from dotenv import load_dotenv
load_dotenv()

# ── Data mode switch — only thing you change between mock and live ────────────
DATA_MODE = "mock"    # "mock" | "tradier" | "massive"

# ── Imports ───────────────────────────────────────────────────────────────────
from data.mock_data import load_mock_market, build_mock_chain

from engines.expected_move  import compute_expected_move
from engines.atr_engine     import classify_atr_trend, em_atr_ratio
from engines.iv_regime      import classify_iv_regime
from engines.term_structure import compute_term_slope, classify_term_structure
from engines.skew_engine    import compute_skew, classify_skew
from engines.context_builder import build_derived

from strategies.bear_call       import generate_bear_call_spreads
from strategies.bull_put        import generate_bull_put_spreads
from strategies.bull_call_debit import generate_bull_call_debit_spreads
from strategies.bear_put_debit  import generate_bear_put_debit_spreads
from strategies.calendar        import generate_calendar_candidates
from strategies.diagonal        import generate_diagonal_candidates

from calculator.trade_scoring import rank_candidates

from utils.printers import (
    print_market_summary,
    print_all_trades,
    print_score_breakdown,
)

from validation.checks import (
    run_validation_checks,
    print_validation_results,
    run_normalization_tests,
    run_calendar_validation,
    run_diagonal_validation,
)


# ─────────────────────────────────────────────
# DERIVED ANALYTICS BUILDER
# ─────────────────────────────────────────────



# ─────────────────────────────────────────────
# TRADIER LIVE MARKET BUILDER
# ─────────────────────────────────────────────

def _build_tradier_market_and_chain(symbol: str) -> tuple[dict, list[dict]]:
    """
    Build market context and combined option chain from live Tradier data.

    Steps:
      1. Get spot price
      2. Get available expirations
      3. Pick short + long expiration dates
      4. Fetch both chains
      5. Extract ATM straddle + IV + skew estimates from chain rows
      6. Return populated market dict + combined chain

    Market dict starts from the mock template so all required keys
    are always present — live values overwrite where available.
    GEX inputs are set to None (Tradier doesn't provide GEX directly).
    The scorer handles missing gamma via proportional weight redistribution.
    """
    from data_sources.tradier_api import (
        get_spot_price,
        get_expirations,
        get_option_chain,
        pick_short_expiration,
        pick_long_expiration,
        extract_atm_straddle,
        extract_front_iv,
        extract_skew_25d,
        _compute_dte,
        TradierAPIError,
    )

    print(f"  [tradier] Fetching spot price for {symbol}...")
    spot = get_spot_price(symbol)
    print(f"  [tradier] Spot: ${spot:.2f}")

    print(f"  [tradier] Fetching expirations for {symbol}...")
    expirations = get_expirations(symbol)
    if not expirations:
        raise TradierAPIError(f"No expirations returned for {symbol}")
    print(f"  [tradier] {len(expirations)} expirations available")

    short_exp = pick_short_expiration(expirations)
    long_exp  = pick_long_expiration(expirations)
    if not short_exp or not long_exp:
        raise TradierAPIError("Could not select short/long expirations")
    print(f"  [tradier] Short exp: {short_exp}  |  Long exp: {long_exp}")

    print(f"  [tradier] Fetching chain: {short_exp}...")
    short_chain = get_option_chain(symbol, short_exp)
    print(f"  [tradier] Fetching chain: {long_exp}...")
    long_chain  = get_option_chain(symbol, long_exp)

    chain = short_chain + long_chain
    print(f"  [tradier] Combined chain rows: {len(chain)}")

    # Build market context from live data, using mock template as base
    market = load_mock_market()
    market["symbol"]    = symbol.upper()
    market["spot_price"] = spot

    short_dte = _compute_dte(short_exp)
    long_dte  = _compute_dte(long_exp)
    market["front_dte"]        = short_dte
    market["short_dte_target"] = short_dte
    market["long_dte_target"]  = long_dte

    # ATM straddle prices → expected move
    straddle = extract_atm_straddle(short_chain, spot, short_dte)
    market["atm_call_mid"] = straddle["atm_call_mid"]
    market["atm_put_mid"]  = straddle["atm_put_mid"]

    # IV estimates → term structure
    front_iv = extract_front_iv(short_chain, short_dte)
    back_iv  = extract_front_iv(long_chain,  long_dte)
    if front_iv:
        market["front_iv"]      = front_iv
        # iv_percentile unknown without historical window — scorer normalizes
        market["iv_percentile"] = 50.0
    if back_iv:
        market["back_iv"] = back_iv

    # 25-delta skew → skew classifier
    skew = extract_skew_25d(short_chain, short_dte)
    market["put_25d_iv"]  = skew.get("put_25d_iv")
    market["call_25d_iv"] = skew.get("call_25d_iv")

    # GEX not available via Tradier — scorer will reweight gamma factor
    market["total_gex"]         = None
    market["gamma_flip"]        = None
    market["gamma_trap_strike"] = None

    return market, chain


# ─────────────────────────────────────────────
# MASSIVE LIVE MARKET BUILDER
# ─────────────────────────────────────────────

def _build_massive_market_and_chain(symbol: str) -> tuple[dict, list[dict]]:
    """
    Build market context and combined chain from live Massive API data.

    Key difference from Tradier:
      - Single snapshot call returns the entire chain (all strikes)
      - Greeks included per contract (on options-enabled plans)
      - Pagination handled automatically in massive_api.py
      - GEX not available — scorer normalizes missing gamma weight
    """
    from data_sources.massive_api import (
        get_spot_price,
        get_expirations,
        get_option_chain,
        pick_short_expiration,
        pick_long_expiration,
        extract_atm_straddle,
        extract_front_iv,
        extract_skew_25d,
        _compute_dte,
        MassiveAPIError,
    )

    print(f"  [massive] Fetching spot price for {symbol}...")
    spot = get_spot_price(symbol)
    print(f"  [massive] Spot: ${spot:.2f}")

    print(f"  [massive] Fetching expirations for {symbol}...")
    expirations = get_expirations(symbol)
    if not expirations:
        raise MassiveAPIError(f"No expirations returned for {symbol}")
    print(f"  [massive] {len(expirations)} expirations available")

    short_exp = pick_short_expiration(expirations)
    long_exp  = pick_long_expiration(expirations)
    if not short_exp or not long_exp:
        raise MassiveAPIError("Could not select short/long expirations")
    print(f"  [massive] Short exp: {short_exp}  |  Long exp: {long_exp}")

    print(f"  [massive] Fetching chain: {short_exp}...")
    short_chain = get_option_chain(symbol, short_exp)
    print(f"  [massive] Fetching chain: {long_exp}...")
    long_chain  = get_option_chain(symbol, long_exp)

    chain = short_chain + long_chain
    print(f"  [massive] Combined chain rows: {len(chain)}")

    # Build market context from live data
    market = load_mock_market()
    market["symbol"]     = symbol.upper()
    market["spot_price"] = spot

    short_dte = _compute_dte(short_exp)
    long_dte  = _compute_dte(long_exp)
    market["front_dte"]        = short_dte
    market["short_dte_target"] = short_dte
    market["long_dte_target"]  = long_dte

    # ATM straddle for expected move
    straddle = extract_atm_straddle(short_chain, spot, short_dte)
    market["atm_call_mid"] = straddle["atm_call_mid"]
    market["atm_put_mid"]  = straddle["atm_put_mid"]

    # IV for term structure
    front_iv = extract_front_iv(short_chain, short_dte)
    back_iv  = extract_front_iv(long_chain, long_dte)
    if front_iv:
        market["front_iv"]      = front_iv
        market["iv_percentile"] = 50.0   # unknown without history
    if back_iv:
        market["back_iv"] = back_iv

    # 25-delta skew
    skew = extract_skew_25d(short_chain, short_dte)
    market["put_25d_iv"]  = skew.get("put_25d_iv")
    market["call_25d_iv"] = skew.get("call_25d_iv")

    # GEX not available — scorer reweights gamma factor automatically
    market["total_gex"]         = None
    market["gamma_flip"]        = None
    market["gamma_trap_strike"] = None

    return market, chain


# ─────────────────────────────────────────────
# DATA LOADER (mode-aware)
# ─────────────────────────────────────────────

def load_market_and_chain(symbol: str = "SPY") -> tuple[dict, list[dict]]:
    """
    Route data loading based on DATA_MODE.
    All branches return (market: dict, chain: list[dict]) in identical schema.
    """
    if DATA_MODE == "mock":
        return load_mock_market(), build_mock_chain()

    elif DATA_MODE == "tradier":
        return _build_tradier_market_and_chain(symbol)

    elif DATA_MODE == "massive":
        return _build_massive_market_and_chain(symbol)

    else:
        raise ValueError(
            f"Unknown DATA_MODE: {DATA_MODE!r}. "
            "Valid options: 'mock', 'tradier', 'polygon'."
        )


# ─────────────────────────────────────────────
# CANDIDATE PIPELINE
# ─────────────────────────────────────────────

def generate_all_candidates(
    market: dict,
    chain: list[dict],
    derived: dict,
) -> list[dict]:
    """Run all active strategy generators and return ranked candidates."""
    candidates: list[dict] = []
    candidates += generate_bear_call_spreads(market, chain, derived)
    candidates += generate_bull_put_spreads(market, chain, derived)
    candidates += generate_bull_call_debit_spreads(market, chain, derived)
    candidates += generate_bear_put_debit_spreads(market, chain, derived)
    candidates += generate_calendar_candidates(market, chain, derived)
    candidates += generate_diagonal_candidates(market, chain, derived)
    return rank_candidates(candidates)


# ─────────────────────────────────────────────
# LIVE VALIDATION (relaxed tolerances for real data)
# ─────────────────────────────────────────────

def _run_live_validation(
    chain: list[dict],
    ranked: list[dict],
    derived: dict,
) -> tuple[bool, list[tuple[str, bool]]]:
    """
    Relaxed checks for live data — real chains may have partial Greeks,
    no gamma data, and fewer rows than a full mock chain.
    """
    top = ranked[0] if ranked else None

    checks = [
        ("Chain loaded with rows",     len(chain) > 0),
        ("Expected move computed",     derived["expected_move"] > 0),
        ("EM boundaries valid",        derived["upper_em"] > derived["lower_em"]),
        ("IV regime classified",       derived["iv_regime"] in
                                        ("cheap", "moderate", "elevated", "rich")),
        ("Term structure classified",  derived["term_structure"] in
                                        ("contango", "flat", "backwardation")),
        ("At least one candidate",     len(ranked) > 0),
        ("All scores bounded 0–100",   all(0 <= t["confidence_score"] <= 100
                                           for t in ranked)),
        ("Top trade score >= 50",      top is not None and
                                        top["confidence_score"] >= 50),
        ("Ranking is descending",      all(
                                            ranked[i]["confidence_score"] >=
                                            ranked[i + 1]["confidence_score"]
                                            for i in range(len(ranked) - 1)
                                        )),
    ]

    all_pass = all(ok for _, ok in checks)
    return all_pass, checks


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main(symbol: str = "SPY", run_tests: bool = True) -> list[dict]:
    print()
    print(f"  [options_assistant] DATA_MODE={DATA_MODE!r}  symbol={symbol!r}")
    print()

    print("  Loading market context and option chain...")
    market, chain = load_market_and_chain(symbol)

    if chain:
        strikes = sorted(set(r["strike"] for r in chain))
        exps    = sorted(set(r["expiration"] for r in chain))
        print(f"  Chain rows: {len(chain)}  "
              f"(strikes ${strikes[0]:.0f}–${strikes[-1]:.0f}, "
              f"expirations: {exps})")
    else:
        print("  WARNING: Empty chain returned.")
    print()

    derived = build_derived(market, chain)
    ranked  = generate_all_candidates(market, chain, derived)
    print(f"  Candidates generated: {len(ranked)}")
    print()

    print_market_summary(market, derived)
    print_all_trades(ranked, top_n=3)

    if ranked:
        print_score_breakdown(ranked[0], derived)

    if run_tests:
        if DATA_MODE == "mock":
            all_pass, core_results = run_validation_checks(chain, ranked, derived)
            print_validation_results(core_results, all_pass, label="Core Validation")

            norm_pass, norm_results = run_normalization_tests(chain)
            print_validation_results(norm_results, norm_pass, label="Normalization Tests")

            cal_pass, cal_results   = run_calendar_validation(ranked)
            print_validation_results(cal_results, cal_pass, label="Calendar Validation")

            diag_pass, diag_results = run_diagonal_validation(ranked)
            print_validation_results(diag_results, diag_pass, label="Diagonal Validation")

            if all_pass and norm_pass and cal_pass and diag_pass:
                print("  ✓ Engine validated. Ready for live data.")
            else:
                print("  ✗ Failures detected — review before going live.")
                sys.exit(1)
        else:
            all_pass, live_results = _run_live_validation(chain, ranked, derived)
            print_validation_results(live_results, all_pass, label="Live Data Validation")
            if all_pass:
                print("  ✓ Live engine validated.")
            else:
                print("  ✗ Live validation failures — check API token and chain quality.")

    return ranked


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    main(symbol=symbol)
