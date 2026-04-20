"""
providers/provider_smoke_test.py
Quick validation that all available providers work end-to-end.

Run: python providers/provider_smoke_test.py

For Massive live test, set MASSIVE_API_KEY env var before running.
For Tradier, set TRADIER_TOKEN and TRADIER_ACCOUNT_ID.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.provider_factory import build_provider
from providers.runtime_data_service import RuntimeDataService


def test_provider(name: str, **kwargs) -> bool:
    print(f"\n[{name}]")
    try:
        p   = build_provider(name, **kwargs)
        svc = RuntimeDataService(p)
        out = svc.run_portfolio(["SPY"])
        meta = out["portfolio_meta"]
        eng  = out["symbols"][0]["engine_output"]
        vga  = eng.get("vga", "?")
        spot = eng["market"].get("spot_price", 0)
        cands = len(eng.get("candidates", []))
        sel  = meta["selected_trades"]
        print(f"  provider  : {p.provider_name()}")
        print(f"  spot      : ${spot:.2f}")
        print(f"  vga       : {vga}")
        print(f"  candidates: {cands}  selected: {sel}")
        print(f"  ✓ PASS")
        return True
    except Exception as e:
        print(f"  ✗ FAIL — {e}")
        return False


def main() -> None:
    results = {}

    results["mock"] = test_provider("mock")
    results["csv"]  = test_provider("csv")

    massive_key = os.getenv("MASSIVE_API_KEY", "")
    if massive_key:
        results["massive"] = test_provider("massive", api_key=massive_key)
    else:
        print("\n[massive] SKIPPED — set MASSIVE_API_KEY to test")

    tradier_token = os.getenv("TRADIER_TOKEN", "")
    tradier_acct  = os.getenv("TRADIER_ACCOUNT_ID", "")
    if tradier_token and tradier_acct:
        results["tradier"] = test_provider(
            "tradier", access_token=tradier_token,
            account_id=tradier_acct, use_sandbox=True,
        )
    else:
        print("\n[tradier] SKIPPED — set TRADIER_TOKEN + TRADIER_ACCOUNT_ID to test")

    print()
    passed = sum(v for v in results.values())
    total  = len(results)
    print(f"Results: {passed}/{total} providers passed")


if __name__ == "__main__":
    main()
