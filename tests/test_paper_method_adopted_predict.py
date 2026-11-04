"""Prospective success is required before any paper model can serve predictions."""
import hashlib

import pytest

from research_paper_adopted_predict import choose_model
from paper_method_autonomy import model_proposal


def candidate():
    expression = "hot20 + 0.2 * gap"
    return {
        "doi": "10.1006/jcss.1997.1504",
        "fulltext_sha256": "f" * 64,
        "candidate_expression": expression,
        "candidate_expression_sha256": hashlib.sha256(expression.encode()).hexdigest(),
        "eligible_for_future_only_shadow": True,
    }


def state():
    c = candidate()
    return {
        "research_adopted": True,
        "trusted_grades": 26,
        "anytime_e_value": 40.0,
        "registration": {
            "doi": c["doi"],
            "paper_sha256": c["fulltext_sha256"],
            "expression": c["candidate_expression"],
            "expression_sha256": c["candidate_expression_sha256"],
            "paper_experiments_reproduced": False,
        },
    }


def test_adoption_requires_full_registered_prospective_evidence():
    s = state()
    c = candidate()
    assert choose_model(s, {"candidate": c}) == c
    assert choose_model(s, {"candidates": [c]}) == c
    assert choose_model({**s, "research_adopted": False}, {"candidate": c}) is None
    assert choose_model({**s, "trusted_grades": 25}, {"candidate": c}) is None
    assert choose_model({**s, "anytime_e_value": 39.99}, {"candidate": c}) is None


def test_adoption_rejects_unmatched_paper_sha_or_expression():
    s = state()
    c = candidate()
    for change in ({"fulltext_sha256": "e" * 64},
                   {"candidate_expression": "hot80"},
                   {"eligible_for_future_only_shadow": False}):
        with pytest.raises(ValueError, match="does not match audited"):
            choose_model(s, {"candidate": {**c, **change}})
    with pytest.raises(ValueError):
        choose_model(s, {"candidates": [c, c]})
    s["registration"]["paper_experiments_reproduced"] = True
    with pytest.raises(ValueError, match="overclaims"):
        choose_model(s, {"candidate": c})


def test_local_engine_rejects_unsupported_paper_without_an_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    paper = {"doi": "10.1006/jcss.1997.1504", "title": "Test", "year": 1997}
    with pytest.raises(ValueError, match="locally supported"):
        model_proposal("This publication has no relevant algorithm. " * 55, paper)
