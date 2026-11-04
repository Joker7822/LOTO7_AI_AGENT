"""Full paper -> independently checked formula -> research queue integration."""
import json

import pytest

import paper_method_autonomy as lab


DOI = "10.1006/jcss.1997.1504"
PAPER = {"doi": DOI, "title": "Learning through expert advice", "year": 1997}
SOURCE = ("We propose a weighted ensemble that combines recent frequency counts "
          "and pairwise co-occurrence signals for a predictive model. "
          "These data-driven signals use prior observed results only. " * 60)
QUOTE = "We aggregate expert forecasts using a multiplicative online update."


def identity(_):
    return {
        "doi": "https://doi.org/" + DOI,
        "best_oa_location": {
            "pdf_url": "https://proceedings.mlr.press/v1/paper.pdf",
            "is_oa": True,
        },
    }


def model(_):
    return {"choices": [{"message": {"content": json.dumps({
        "method": "Weighted historical signals",
        "exact_quote": QUOTE,
        "expression": "hot20 + 0.2 * gap",
        "limitation": "Lottery-domain adaptation, not published experiments",
    })}}]}


def test_full_discovery_registers_reproducible_candidate_without_production(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "bibliography", lambda root: [PAPER])
    monkeypatch.setattr(lab, "historical_prequential_screen",
                        lambda root, expression: {
                            "targets": 48, "screen_passed": True,
                            "retrospective_selection_bias": True,
                            "independent_future_evidence": False})
    first = lab.discover(
        tmp_path,
        lookup=identity,
        get_pdf=lambda url: (SOURCE.encode(), "text/plain"))
    assert first["status"] == "synthetic_and_historical_screen_passed"
    assert len(first["candidates"]) == 1
    c = first["candidate"]
    assert c["doi"] == DOI
    assert c["full_text_was_extracted"]
    assert c["method_engine"] == "independent-fulltext-rule-engine-v1"
    assert c["synthetic_reproducibility"]["replicated_deterministically"]
    assert c["retrospective_historical_screen"]["targets"] == 48
    assert c["eligible_for_future_only_shadow"] is True
    assert c["faithful_paper_replication_proven"] is False
    assert first["production_changed"] is False
    assert first["automatic_production_promotion"] is False
    second = lab.discover(tmp_path, lookup=identity,
                          get_pdf=lambda url: (SOURCE.encode(), "text/plain"))
    assert second["status"] == "no_unreviewed_verified_papers"
    assert len(json.loads((tmp_path / lab.REGISTRY).read_text())["candidates"]) == 1


def test_research_does_not_require_any_inference_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "bibliography", lambda root: [PAPER])
    monkeypatch.setattr(lab, "historical_prequential_screen",
                        lambda root, expression: {
                            "targets": 48, "screen_passed": True,
                            "retrospective_selection_bias": True,
                            "independent_future_evidence": False})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = lab.discover(
        tmp_path, lookup=identity,
        get_pdf=lambda url: (SOURCE.encode(), "text/plain"))
    assert result["status"] == "synthetic_and_historical_screen_passed"
    assert len(result["candidates"]) == 1


def test_openalex_tries_second_safe_oa_location():
    def alternate(_):
        return {"doi": "https://doi.org/" + DOI,
                "best_oa_location": {
                    "is_oa": True, "pdf_url": "https://example.com/book.pdf"},
                "locations": [
                    {"is_oa": False, "pdf_url": "https://arxiv.org/pdf/1234"},
                    {"is_oa": True, "pdf_url": "https://arxiv.org/pdf/1234"},
                ]}
    url, _ = lab.openalex_pdf(DOI, request_json=alternate)
    assert url == "https://arxiv.org/pdf/1234"

def test_temporary_openalex_failure_does_not_consume_paper(tmp_path, monkeypatch):
    import urllib.error
    monkeypatch.setattr(lab, "bibliography", lambda root: [PAPER])
    def broken(_):
        raise urllib.error.URLError("temporary API outage")
    result = lab.discover(tmp_path, model=model, lookup=broken)
    assert result["status"] == "retry_pending"
    assert result["attempted_dois"] == []
    assert json.loads((tmp_path / lab.REGISTRY).read_text())["candidate"] is None
