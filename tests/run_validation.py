"""tests/run_validation.py — Runs all validation suites and returns pass/fail summary."""
from __future__ import annotations
from tests.test_registry import TEST_REGISTRY
from tests.assertion_helpers import ValidationFailure


def run_all_validations() -> dict:
    suite_results=[]; total_pass=0; total_fail=0
    for suite_name, suite_fn in TEST_REGISTRY:
        try:
            results = suite_fn()
            for item in results:
                total_pass += 1
                suite_results.append({"suite":suite_name,**item})
        except Exception as e:
            total_fail += 1
            suite_results.append({"suite":suite_name,"test":f"{suite_name}_suite",
                                   "status":"FAIL","error":str(e)})
    return {"total_pass":total_pass,"total_fail":total_fail,"results":suite_results}

if __name__ == "__main__":
    result = run_all_validations()
    print(f"\n{'='*60}")
    print(f"  VALIDATION SUITE: {result['total_pass']} passed | {result['total_fail']} failed")
    print(f"{'='*60}")
    for r in result["results"]:
        icon = "✓" if r.get("status")=="PASS" else "✗"
        err = f" — {r.get('error','')[:60]}" if r.get("status")!="PASS" else ""
        print(f"  {icon} [{r['suite']}] {r.get('test','?')}{err}")
    print()
