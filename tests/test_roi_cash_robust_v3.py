import numpy as np
from research.roi_cash_robust_v3 import refine, MAX_SWAPS, ROUND_CAP_YEN
from research.roi_cash_agent_v2 import candidate_from_cash_history, _public_cash
from research.roi_cash_robust_v3_replay import matched, summarize
from test_roi_cash_agent_v2 import sample, ranking

def test_refinement_is_deterministic_and_conservative():
    h,b,p=sample(104)
    base,_=candidate_from_cash_history(h,b,p,ranking())
    out,meta=refine(h,b,p,ranking())
    assert (out,meta)==refine(h,b,p,ranking())
    assert sorted(n for t in out for n in t)==list(range(1,36))
    assert 0<=meta["swaps"]<=MAX_SWAPS
    def metrics(tickets):
        g=np.asarray(tickets)-1
        hits=h[:,g].sum(axis=2).T
        bonus=b[:,g].sum(axis=2).T
        cash=np.minimum(_public_cash(hits,bonus,p,ROUND_CAP_YEN).sum(axis=0),ROUND_CAP_YEN)
        return cash, hits.max(axis=0)>=3
    a,c=metrics(base); x,z=metrics(out)
    for sl in (slice(0,52),slice(52,104)):
        assert x[sl].sum()>=a[sl].sum()
        assert z[sl].sum()>=c[sl].sum()

def test_warmup_keeps_v2():
    h,b,p=sample(100)
    a,_=candidate_from_cash_history(h,b,p,ranking())
    x,meta=refine(h,b,p,ranking())
    assert x==a and meta["status"]=="warmup_v2"

def test_matched_controls_same_35_deterministic():
    a=list(matched(ranking(),705))
    assert len(a)==32 and a==list(matched(ranking(),705))
    assert all(sorted(n for t in arm for n in t)==list(range(1,36)) for arm in a)

def test_missing_cash_never_becomes_zero_roi():
    r={"round":705,"swaps":0}
    for name in ("v3","v2","rank","matched32"):
        r[name]={"cash":None if name=="v3" else 1000,"max_hits":2,"three_plus":0,"four_plus":0}
    x=summarize([r])
    assert not x["complete_public_cash"]
    assert x["arms"]["v3"]["roi"] is None
    assert x["comparisons"]["v2"]["delta_yen"] is None
