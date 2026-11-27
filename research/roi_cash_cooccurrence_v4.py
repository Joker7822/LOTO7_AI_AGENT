"""Research-only v4: shrunk pair and triple interaction refinement of v3.

The null is sampling seven labels uniformly without replacement. Log-ratio
interaction scores are regularized descriptive training features, not p-values.
Never changes the ranked 35, deployed model, or issued ledger.
"""
from itertools import combinations
from math import comb
import numpy as np
from balanced_uniform_portfolio import validate_portfolio
from research.roi_cash_agent_v2 import CashAgentConfig, _validate_inputs, _public_cash
from research.roi_cash_robust_v3 import ROUND_CAP_YEN, LOOKBACK, refine

VERSION = "research-shrunk-pair-triple-combination-v4"
PAIR_PRIOR = 104
TRIPLE_PRIOR = 416
TRIPLE_WEIGHT = 0.5
MAX_SWAPS = 2
MIN_GAIN = 1e-6
PAIRS = np.array(list(combinations(range(7), 2)))
TRIPLES = np.array(list(combinations(range(7), 3)))
P1, P2, P3 = (comb(7,k)/comb(37,k) for k in (1,2,3))


def interaction_weights(history):
    """Shrink joint frequencies to fair-draw rates; remove lower-order effects."""
    h = np.asarray(history)
    if h.ndim != 2 or h.shape[1] != 37 or not len(h):
        raise ValueError("invalid interaction history shape")
    if not np.all((h==0)|(h==1)) or not np.all(h.sum(axis=1)==7):
        raise ValueError("invalid 7-of-37 history")
    h=h.astype(np.int64)
    n=len(h)
    one=h.sum(axis=0)
    two=h.T@h
    selected=np.flatnonzero(h).reshape(n,7)%37
    tri=selected[:,TRIPLES]
    three=np.zeros((37,37,37),dtype=np.int64)
    np.add.at(three,(tri[:,:,0],tri[:,:,1],tri[:,:,2]),1)
    def ratio(count,p,prior):
        return np.log((count+prior*p)/((n+prior)*p))
    single=ratio(one,P1,PAIR_PRIOR)
    pair=np.clip(ratio(two,P2,PAIR_PRIOR)-single[:,None]-single[None,:],-1,1)
    # The triple feature removes the three pair terms and adds the singleton
    # terms back once; use the stronger prior consistently at all three orders.
    single3=ratio(one,P1,TRIPLE_PRIOR)
    pair3=ratio(two,P2,TRIPLE_PRIOR)
    triple=ratio(three,P3,TRIPLE_PRIOR) - pair3[:,:,None] - pair3[:,None,:] - pair3[None,:,:]
    triple+=single3[:,None,None]+single3[None,:,None]+single3[None,None,:]
    return pair,np.clip(triple,-1,1)


def ticket_score(groups, weights):
    pair,triple=weights
    g=np.sort(np.asarray(groups,dtype=int),axis=1)
    a=g[:,PAIRS]
    t=g[:,TRIPLES]
    return pair[a[:,:,0],a[:,:,1]].mean(axis=1)+TRIPLE_WEIGHT*triple[t[:,:,0],t[:,:,1],t[:,:,2]].mean(axis=1)


def refine_cooccurrence(history, bonus, payouts, ranking, *, start=None):
    h,b,p=_validate_inputs(history,bonus,payouts,ranking,CashAgentConfig())
    if len(h)!=LOOKBACK:
        raise ValueError("v4 needs 104 strictly preceding draws")
    if start is None:
        start,_=refine(history,bonus,payouts,ranking)
    validate_portfolio(start)
    if sorted(n for t in start for n in t)!=sorted(ranking[:35]):
        raise ValueError("starting portfolio changed selected labels")
    assigned=np.asarray(start,dtype=int).reshape(-1)-1
    half=LOOKBACK//2
    windows=(interaction_weights(h[:half]),interaction_weights(h[half:]))
    ids=np.arange(35)//7
    i,j=np.triu_indices(35,k=1)
    mask=ids[i]!=ids[j]
    i,j=i[mask],j[mask]
    gi,gj=ids[i],ids[j]
    swapped=0
    total_gain=np.zeros(2)
    for _ in range(MAX_SWAPS):
        groups=assigned.reshape(5,7)
        hits=h[:,groups].sum(axis=2).T
        extras=b[:,groups].sum(axis=2).T
        cash=_public_cash(hits,extras,p,ROUND_CAP_YEN)
        if not np.isfinite(cash).all():
            break
        ai,aj=assigned[i],assigned[j]
        left,right=groups[gi].copy(),groups[gj].copy()
        left[np.arange(len(i)),i%7]=aj
        right[np.arange(len(i)),j%7]=ai
        gains=[]
        for weight in windows:
            prev=ticket_score(groups,weight)
            gains.append(ticket_score(left,weight)+ticket_score(right,weight)-prev[gi]-prev[gj])
        gains=np.stack(gains,axis=1)
        hi=hits[gi]+h[:,aj].T-h[:,ai].T
        hj=hits[gj]+h[:,ai].T-h[:,aj].T
        bi=extras[gi]+b[:,aj].T-b[:,ai].T
        bj=extras[gj]+b[:,ai].T-b[:,aj].T
        ci=_public_cash(hi,bi,p,ROUND_CAP_YEN)
        cj=_public_cash(hj,bj,p,ROUND_CAP_YEN)
        delta=np.minimum(cash.sum(axis=0)-cash[gi]-cash[gj]+ci+cj,ROUND_CAP_YEN)-np.minimum(cash.sum(axis=0),ROUND_CAP_YEN)
        other=np.zeros_like(hi)
        for group in range(5):
            other=np.maximum(other,np.where(((gi!=group)&(gj!=group))[:,None],hits[group],0))
        concentration=(np.maximum(np.maximum(hi,hj),other)>=3).astype(int)-(hits.max(axis=0)>=3).astype(int)
        eligible=(np.isfinite(delta).all(axis=1)&(gains.min(axis=1)>MIN_GAIN))
        for sl in (slice(0,half),slice(half,None)):
            eligible &= (delta[:,sl].sum(axis=1)>=0)&(concentration[:,sl].sum(axis=1)>=0)
        merit=np.where(eligible,gains.min(axis=1),-np.inf)
        idx=int(np.argmax(merit))
        if not np.isfinite(merit[idx]):
            break
        x,y=int(i[idx]),int(j[idx])
        assigned[x],assigned[y]=assigned[y],assigned[x]
        total_gain+=gains[idx]
        swapped+=1
    tickets=[tuple(sorted((row+1).tolist())) for row in assigned.reshape(5,7)]
    validate_portfolio(tickets)
    if sorted(n for t in tickets for n in t)!=sorted(ranking[:35]):
        raise AssertionError("v4 changed selected labels")
    return tickets,{"version":VERSION,"swaps":swapped,"half_interaction_gains":total_gain.tolist(),"history_rows":len(history)}
