"""External paper content never gains execution or Production authority."""
import json
import numpy as np
import pytest

import paper_method_autonomy as lab
import paper_method_future_shadow as future


def rows(n=105, seed=10):
    rng = np.random.default_rng(seed)
    x = np.zeros((n, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, 7, replace=False)] = 1
    return x


def test_fulltext_not_metadata_is_required():
    with pytest.raises(ValueError, match="no extractable full paper"):
        lab.paper_text(b"abstract only", "text/plain")
    body = "Detailed publication method weighted regression. " * 60
    result, count = lab.paper_text(body.encode(), "text/plain")
    assert count == 0 and len(result) > 1500


def test_llm_output_must_quote_actual_paper_and_stay_in_safe_ast():
    source = ("We propose online allocation using a multiplicative weight update "
              "for two predictive expert models. " * 45)
    paper = {"doi": "10.1006/jcss.1997.1504", "title": "Hedge", "year": 1997}
    quote = "We propose online allocation using a multiplicative weight update"
    good = {
        "method": "Weighted aggregation", "exact_quote": quote,
        "expression": "tanh(hot20 + gap)", "limitation": "adaptation only",
    }
    def mock(value):
        assert "untrusted" in value["messages"][0]["content"]
        return {"choices": [{"message": {"content": json.dumps(good)}}]}
    assert lab.model_proposal(source, paper, request_model=mock)["expression"] == good["expression"]
    malformed = dict(good, expression="__import__('os').system('bad')")
    with pytest.raises(ValueError):
        lab.model_proposal(source, paper, request_model=lambda _:
            {"choices": [{"message": {"content": json.dumps(malformed)}}]})
    malformed = dict(good, exact_quote="nonexistent quote " * 3)
    with pytest.raises(ValueError):
        lab.model_proposal(source, paper, request_model=lambda _:
            {"choices": [{"message": {"content": json.dumps(malformed)}}]})


def test_safe_math_adaptation_has_synthetic_repro_and_no_lookahead():
    report = lab.reproducibility("hot20 + 0.2 * gap")
    assert report["replicated_deterministically"]
    assert report["prior_only_dependency_test"]
    assert not report["paper_original_experiments_reproduced"]
    with pytest.raises(ValueError, match="equivalent to uniform"):
        lab.reproducibility("uniform")


def test_openalex_checks_paper_identity_and_allowlisted_fulltext():
    doi = "10.1006/jcss.1997.1504"
    def mock(_):
        return {"doi": "https://doi.org/" + doi,
                "best_oa_location": {"pdf_url":
                    "https://www.eecs.harvard.edu/cs286r/courses/fall10/papers/hedge.pdf"}}
    url, work = lab.openalex_pdf(doi, request_json=mock)
    assert url.endswith("hedge.pdf")
    with pytest.raises(ValueError):
        lab.openalex_pdf(doi, request_json=lambda _:
            {"doi": "https://doi.org/" + doi,
             "best_oa_location": {"pdf_url": "https://127.0.0.1/admin.pdf"}})
    with pytest.raises(ValueError):
        lab.openalex_pdf(doi, request_json=lambda _:
            {"doi": "https://doi.org/10.1000/wrong",
             "best_oa_location": {"pdf_url": url}})
    with pytest.raises(ValueError):
        lab.fetch("https://127.0.0.1/anything")


def test_future_research_freeze_is_future_and_scored_only_after_outcome():
    x = rows()
    scheduled = "2026-11-20"
    prediction = future.forecast_payload(x, 106, "hot20", scheduled)
    assert prediction["target_round"] == 106
    assert prediction["prefix_history_sha256"]
    assert len(prediction["model_probabilities"]) == 37
    frozen = future.event({
        "kind": "forecast", "target_round": 106,
        "issued_at_utc": "2026-11-17T00:00:00+00:00",
        "prediction": prediction, "prediction_sha256": future.digest(prediction),
    }, "GENESIS", 1)
    state = {
        "version": future.VERSION, "horizon": future.HORIZON,
        "registration": {
            "first_target_round": 106, "expression": "hot20",
            "expression_sha256": future.hashlib.sha256(b"hot20").hexdigest(),
            "alpha": future.ALPHA,
        },
        "events": [frozen], "trusted_grades": 0,
        "anytime_e_value": 1.0,
        "research_adopted": False,
        "production_modified": False, "original_future_ledgers_modified": False,
    }
    dates = ["2026-10-01"] * 105
    future.assert_chain(state, x, dates)
    y = rows(106)[-1]
    changed = np.vstack([x, y])
    edge = future.brier_edge(prediction["model_probabilities"], y)
    grade = future.event({
        "kind": "grade", "target_round": 106,
        "forecast_event_sha256": frozen["event_sha256"],
        "actual_numbers": (np.flatnonzero(y) + 1).tolist(),
        "brier_edge_vs_uniform": edge,
        "anytime_e_value": 1.0 + edge,
    }, frozen["event_sha256"], 2)
    state["events"].append(grade)
    state["trusted_grades"] = 1
    state["anytime_e_value"] = 1 + edge
    future.assert_chain(state, changed, dates + [scheduled])
    state["events"][0]["prediction"]["model_probabilities"][0] += 0.02
    with pytest.raises(ValueError):
        future.assert_chain(state, changed, dates + [scheduled])


def test_paper_research_never_masquerades_as_proven_production():
    assert future.REQUIRED_E == 40.0
    assert future.HORIZON == 26
    assert future.VERSION != lab.VERSION
