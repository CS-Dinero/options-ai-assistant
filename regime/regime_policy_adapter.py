"""regime/regime_policy_adapter.py — Map regime → XSP scanner config."""
from regime.regime_definitions import XSP_CREDIT_REGIMES, XSP_DEBIT_REGIMES
from policy.xsp_policy_loader import load_xsp_policy
from scanner.xsp_credit_spread_scanner import XSPCreditSpreadScannerConfig
from scanner.xsp_debit_spread_scanner import XSPDebitSpreadScannerConfig

def xsp_credit_scanner_config(regime: str) -> XSPCreditSpreadScannerConfig:
    p = load_xsp_policy(regime)
    return XSPCreditSpreadScannerConfig(
        short_dte_min=p.credit_short_dte_min,
        short_dte_max=p.credit_short_dte_max,
        short_delta_min=p.credit_short_delta_min,
        short_delta_max=p.credit_short_delta_max,
        spread_widths=p.credit_spread_widths,
        min_credit=p.credit_min_credit,
        min_credit_width_ratio=p.credit_min_cwr,
        min_open_interest=p.min_open_interest,
        max_bid_ask_width=p.max_bid_ask_width,
    )

def xsp_debit_scanner_config(regime: str) -> XSPDebitSpreadScannerConfig:
    p = load_xsp_policy(regime)
    return XSPDebitSpreadScannerConfig(
        dte_min=p.debit_dte_min, dte_max=p.debit_dte_max,
        long_delta_min=p.debit_long_delta_min,
        long_delta_max=p.debit_long_delta_max,
        spread_widths=p.debit_spread_widths,
        min_debit=p.debit_min, max_debit=p.debit_max,
        min_reward_risk=p.debit_min_reward_risk,
        min_open_interest=p.min_open_interest,
        max_bid_ask_width=p.max_bid_ask_width,
    )

def run_xsp_credit_or_debit(regime: str) -> dict:
    r = regime.upper()
    return {
        "run_credit": r in XSP_CREDIT_REGIMES,
        "run_debit":  r in XSP_DEBIT_REGIMES,
    }
