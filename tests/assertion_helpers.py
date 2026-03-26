"""tests/assertion_helpers.py — Readable test assertions."""
from __future__ import annotations

class ValidationFailure(Exception):
    pass

def assert_true(cond: bool, msg: str) -> None:
    if not cond: raise ValidationFailure(msg)

def assert_false(cond: bool, msg: str) -> None:
    if cond: raise ValidationFailure(msg)

def assert_equal(actual, expected, msg: str) -> None:
    if actual != expected:
        raise ValidationFailure(f"{msg} | actual={actual} expected={expected}")

def assert_in(item, container, msg: str) -> None:
    if item not in container:
        raise ValidationFailure(f"{msg} | missing={item}")

def assert_gte(actual: float, expected: float, msg: str) -> None:
    if float(actual) < float(expected):
        raise ValidationFailure(f"{msg} | actual={actual} expected>={expected}")

def assert_lte(actual: float, expected: float, msg: str) -> None:
    if float(actual) > float(expected):
        raise ValidationFailure(f"{msg} | actual={actual} expected<={expected}")

def assert_raises(exc_type, fn, *args, **kwargs) -> None:
    try:
        fn(*args, **kwargs)
        raise ValidationFailure(f"Expected {exc_type.__name__} but no exception raised")
    except exc_type:
        pass
