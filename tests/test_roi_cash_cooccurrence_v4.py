import numpy as np
import pytest
from research.roi_cash_agent_v2 import _public_cash
from research.roi_cash_robust_v3 import refine,ROUND_CAP_YEN
from research.roi_cash_cooccurrence_v4 import (
    interaction_weights,ticket_score,refine_cooccurrence,MAX_SWAPS,
)
from research.roi_cash_cooccurrence_v4_replay import summarize
from test_roi_cash_agent_v2 import sample,ranking


def test_cooccurrence_finite_and_reject_invalid_history():
    h,_,_=sample(208)
    a,b=interaction_weights(h)
    assert a.shape==(37,37) and b.shape==(37,37,37)
    assert np.isfinite(a).all() and np.isfinite(b).all()
    assert np.max(np.abs(a))<=1 and np.max(np.abs(b))<=1
    h[0]=0
    with pytest.raises(ValueError):
        interaction_weights(h)


def test_v4_deterministic_same35_and_no_in_sample_regression():
    h,b,p=sample(104)
    base,_=refine(h,b,p,ranking())
    out,meta=refine_cooccurrence(h,b,p,ranking(),start=base)
    assert (out,meta)==refine_cooccurrence(h,b,p,ranking(),start=base)
    assert sorted(n for t in out for n in t)==list(range(1,36))
    assert 0<=meta["swaps"]<=MAX_SWAPS
    for sl in (slice(0,52),slice(52,104)):
        weights=interaction_weights(h[sl])
        def measures(tickets):
            g=np.asarray(tickets)-1
            hits=h[sl][:,g].sum(axis=2).T
            extra=b[sl][:,g].sum(axis=2).T
            cash=np.minimum(_public_cash(hits,extra,p[sl],ROUND_CAP_YEN).sum(axis=0),ROUND_CAP_YEN)
            return cash.sum(),(hits.max(axis=0)>=3).sum(),ticket_score(g,weights).sum()
        a=measures(base); z=measures(out)
        assert z[0]>=a[0] and z[1]>=a[1] and z[2]>=a[2]-1e-10


def test_latest_104_only_and_bad_start_rejected():
    h,b,p=sample(105)
    base,_=refine(h,b,p,ranking())
    a,_=refine_cooccurrence(h,b,p,ranking(),start=base)
    z,_=refine_cooccurrence(h[1:],b[1:],p[1:],ranking(),start=base)
    assert a==z
    wrong=[list(t) for t in base]
    wrong[-1][-1]=37
    with pytest.raises(ValueError):
        refine_cooccurrence(h,b,p,ranking(),start=wrong)


def test_missing_public_cash_not_zero():
    record={"round":705,"v4_swaps":0}
    for arm in ("v4","v3","v2","rank","matched32"):
        record[arm]={"cash":None if arm=="v4" else 1000,"max_hits":2,"three_plus":0,"four_plus":0}
    result=summarize([record])
    assert result["arms"]["v4"]["roi"] is None
    assert result["paired"]["v3"]["delta_yen"] is None
