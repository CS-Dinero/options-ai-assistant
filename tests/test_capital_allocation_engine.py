"""tests/test_capital_allocation_engine.py"""
from allocation.capital_allocation_models import AllocationInput
from allocation.capital_allocation_engine import allocate_xsp_position

def test_basic_approval():
    inp = AllocationInput(5000.0,"NEUTRAL_TIME_SPREADS","BULL_PUT_SPREAD",100.0,0.0)
    d = allocate_xsp_position(inp)
    assert d.allow_new_entries is True
    assert d.max_contracts >= 1

def test_exposure_cap_blocks():
    inp = AllocationInput(5000.0,"NEUTRAL_TIME_SPREADS","BULL_PUT_SPREAD",100.0,2000.0)
    d = allocate_xsp_position(inp)
    assert d.allow_new_entries is False

def test_high_vol_smaller():
    normal = allocate_xsp_position(AllocationInput(5000.0,"NEUTRAL_TIME_SPREADS","BULL_PUT_SPREAD",100.0,0.0))
    hv     = allocate_xsp_position(AllocationInput(5000.0,"HIGH_VOL_DEFENSE","BULL_PUT_SPREAD",100.0,0.0))
    assert hv.max_contracts <= normal.max_contracts
