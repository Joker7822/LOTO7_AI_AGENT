"""Research replay invariants: round-2 coverage, chronology and non-promotion."""
import copy

import numpy as np
import pytest

import research_cycle_round2_replay as task


def draws(n=105, seed=19):
    rng = np.random.default_rng(seed)
    x = np.zeros((n, task.NUMBERS), dtype=np.int8)
    for row in x:
        row[rng.choice(task.NUMBERS, size=task.PICKS, replace=False)] = 1
    return x


def test_every_round_recomputed_and_early_targets_uniform():
    result = task.replay(draws(), "hot20", seed=1234)
    assert result["evaluated_rounds"] == 104
    assert [r["round"] for r in result["rounds"]] == list(range(2, 106))
    assert result["summary"]["cold_start_2_to_100"]["count"] == 99
    assert result["summary"]["evolved_101_onward"]["count"] == 5
    assert all(r["regime"] == "uniform_cold_start" for r in result["rounds"][:99])
    for row in result["rounds"][:99]:
        assert row["research_top7"] == row["uniform_top7"]
        assert row["research_tickets"] == row["uniform_tickets"]
        assert row["proper_scores"]["log_edge_vs_uniform"] == 0.0
    assert result["expression_selected_with_hindsight"]
    assert not result["independent_prospective_evidence"]
    assert not result["historical_issued_predictions_replaced"]
    assert not result["promotion_authorized"]


def test_replay_reproducible_with_complete_preoutcome_fingerprint():
    history = draws()
    first = task.replay(history, "hot20", seed=91)
    assert first == task.replay(history, "hot20", seed=91)
    for item in first["rounds"]:
        for field in ("research_tickets", "uniform_tickets"):
            assert len(item[field]) == 5
            assert len({tuple(ticket) for ticket in item[field]}) == 5
            assert all(len(ticket) == 7 and len(set(ticket)) == 7
                       and min(ticket) >= 1 and max(ticket) <= 37
                       for ticket in item[field])
        assert item["forecast_sha256"] == task.sha({
            "round": item["round"],
            "prior_draws": item["prior_draws"],
            "research_top7": item["research_top7"],
            "uniform_top7": item["uniform_top7"],
            "research_tickets": item["research_tickets"],
            "uniform_tickets": item["uniform_tickets"],
            "research_inclusion_probabilities": item[
                "research_inclusion_probabilities"],
        })


def test_last_outcome_cannot_change_prediction_for_same_model():
    original = draws()
    changed = original.copy()
    changed[-1] = 0
    changed[-1, 27:34] = 1
    first = task.replay(original, "hot20", seed=17)["rounds"][-1]
    second = task.replay(changed, "hot20", seed=17)["rounds"][-1]
    assert first["actual_numbers"] != second["actual_numbers"]
    assert first["forecast_sha256"] == second["forecast_sha256"]
    assert first["research_top7"] == second["research_top7"]
    assert first["research_tickets"] == second["research_tickets"]


def test_reject_expression_execution_or_bad_draws():
    with pytest.raises(ValueError):
        task.replay(draws(), "__import__('os').system('echo unsafe')")
    with pytest.raises(ValueError):
        task.replay(draws(100), "hot20")
    malformed = draws()
    malformed[0] = 0
    with pytest.raises(ValueError):
        task.replay(malformed, "hot20")
    with pytest.raises(ValueError):
        task.replay(draws(), "hot20", dates=["2026-11-03"])


def test_checkpoint_must_match_verified_draw_sha(monkeypatch, tmp_path):
    fingerprint = "f" * 64
    champion = {
        "expression": "hot20", "generation": 9,
        "research_data_sha256": fingerprint,
        "assessment": {"historical_selection_only": True,
                       "prospective_improvement_proven": False},
    }
    state = {
        "version": task.EVOLUTION_VERSION,
        "evaluation_data_sha256": fingerprint,
        "independent_source_verified": True,
        "latest_verification": "verified_two_result_sources",
        "recorded_rounds": 105,
        "last_record_sha256": "a" * 64,
        "research_champion": champion,
        "generations_total": 11,
        "authority": {"production_predictions": False,
                      "retrospective_oos_freezes": False},
    }
    monkeypatch.setattr(task, "reload_checkpoint",
                        lambda _: (state, [{"record_sha256": "a" * 64}]))
    assert task.load_candidate(tmp_path, fingerprint, 105)["generation"] == 9
    altered = copy.deepcopy(state)
    altered["authority"]["production_predictions"] = True
    monkeypatch.setattr(task, "reload_checkpoint",
                        lambda _: (altered, [{"record_sha256": "a" * 64}]))
    with pytest.raises(ValueError):
        task.load_candidate(tmp_path, fingerprint, 105)
    monkeypatch.setattr(task, "reload_checkpoint",
                        lambda _: (state, [{"record_sha256": "b" * 64}]))
    with pytest.raises(ValueError):
        task.load_candidate(tmp_path, fingerprint, 105)
    with pytest.raises(ValueError):
        task.load_candidate(tmp_path, "e" * 64, 105)


def test_bibliography_is_metadata_not_automatic_adoption(tmp_path):
    assert task.bibliography_audit(tmp_path)["new_executable_methods_authorized"] is False
    folder = tmp_path / "loto7_agent_output"
    folder.mkdir()
    (folder / "research_verified_publications.json").write_text(
        '{"verifications":[{"status":"two_provider_bibliography_matched"},'
        '{"status":"conflict_do_not_use"}]}', encoding="utf-8")
    result = task.bibliography_audit(tmp_path)
    assert result["verified_works"] == 1
    assert not result["full_text_method_reproduction"]
    assert not result["new_executable_methods_authorized"]
