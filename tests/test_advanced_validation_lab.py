"""Advanced scientific research lab: fail closed, never alter existing OOS evidence."""
from __future__ import annotations

import copy
import itertools
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

import advanced_validation_lab as lab
import accuracy_extension_agent as candidate

CLOCK = datetime(2026, 10, 19, 11, 0, tzinfo=timezone(timedelta(hours=9)))


@pytest.fixture()
def lab_root(tmp_path):
    root = tmp_path / "lab"
    out = root / "loto7_agent_output"
    out.mkdir(parents=True)
    for path in (
        "loto7.csv", lab.__file__, *candidate.FILES_LOCKED
    ):
        name = Path(path).name
        shutil.copyfile(Path(path), root / name)
    for name in (candidate.REG, candidate.STATE, candidate.SUMMARY):
        shutil.copyfile(Path("loto7_agent_output") / name, out / name)
    return root


def fake_frozen(*, target=701, actual=None):
    if actual is None:
        actual = list(range(1, 8))
    p = np.full(37, 7 / 37, dtype=float)
    frozen = {
        "target_round": target, "record_sha256": "e" * 64,
        "inclusion_p_canonical": [str(v) for v in p],
    }
    grade = {
        "target_round": target, "actual_numbers": actual,
        "source_verification": candidate.SOURCE_TRUST,
        "frozen_record_sha256": frozen["record_sha256"],
    }
    return frozen, grade


def test_uniform_frozen_vector_has_exact_e_one_for_any_7_distinct_numbers():
    p = np.full(37, 7 / 37, dtype=float)
    for subset in (range(7), range(30, 37), (1, 7, 12, 20, 24, 25, 29)):
        factor = lab.frozen_multiplier(p, np.array(list(subset)))
        assert factor == pytest.approx(1.0, abs=1e-12)


def test_conditional_exact_fair_null_works_with_without_replacement():
    # For each of the 37 numbers under a uniform 7-of-37 outcome,
    # E[I_n] = 7/37. Dependence between inclusion indicators is irrelevant.
    p = np.linspace(0.10, 0.30, 37)
    p *= 7 / p.sum()
    assert 0 < p.min() < p.max() < 1
    analytic_expected_numerator = sum(p) * 7 / 37
    assert analytic_expected_numerator == pytest.approx(49 / 37)
    # Check every possible pair of two numbers from a smaller 5-ball urn:
    # the exact finite-population expectation is still k/m sum(p), not
    # an independent-Bernoulli approximation.
    small = np.array([.12, .31, .53, .66, .38])
    observed = [small[list(ids)].sum() for ids in itertools.combinations(range(5), 2)]
    assert np.mean(observed) == pytest.approx(2 / 5 * small.sum())


def test_future_e_process_is_one_before_any_draw_and_does_not_invent_results():
    x = lab.future_e_process([], [])
    assert x["verified_prefrozen_draws"] == 0
    assert x["current_e_value"] == 1
    assert x["max_e_value"] == 1
    assert x["series"] == []
    assert x["threshold_crossed"] is False


def test_future_multiplication_uses_prior_frozen_vector_not_post_hoc_choice():
    frozen, grade = fake_frozen()
    series = lab.future_e_process([frozen], [grade])
    assert series["series"][0]["factor"] == pytest.approx(1)
    assert series["current_e_value"] == pytest.approx(1)
    grade["actual_numbers"] = [1, 2, 3, 4, 5, 6, 6]
    with pytest.raises(ValueError, match="7-of-37"):
        lab.future_e_process([frozen], [grade])


def test_future_e_sequential_threshold_is_not_authority_to_promote():
    p = np.full(37, (7 - 7 * .30) / 30)
    p[:7] = .30
    frozen, grade = fake_frozen()
    frozen["inclusion_p_canonical"] = [str(q) for q in p]
    freezes = [dict(frozen, target_round=701 + i, record_sha256=str(i)) for i in range(12)]
    grades = [dict(grade, target_round=701 + i, frozen_record_sha256=str(i)) for i in range(12)]
    values = lab.future_e_process(freezes, grades)
    assert values["threshold_crossed"] is True
    assert values["max_e_value"] >= 20
    assert values["ongoing_descriptive_not_auto_promotion"] is True


def test_future_e_refuses_untrusted_unsynchronized_or_missing_predictions():
    frozen, grade = fake_frozen()
    modified = dict(grade, source_verification="degraded_single_result_source")
    with pytest.raises(ValueError, match="trusted pre-frozen"):
        lab.future_e_process([frozen], [modified])
    modified = dict(grade, frozen_record_sha256="fake")
    with pytest.raises(ValueError, match="trusted pre-frozen"):
        lab.future_e_process([frozen], [modified])
    with pytest.raises(ValueError, match="grade count"):
        lab.future_e_process([], [grade])


def test_block_bootstrap_is_paired_time_ordered_and_deterministic():
    a = np.linspace(-0.001, 0.001, 60)
    b = a + .0001
    x = lab.paired_circular_block_ci(a, b)
    y = lab.paired_circular_block_ci(a, b)
    assert x == y
    assert x["mean_five_minus_four"] == pytest.approx(.0001)
    assert x["low95"] == pytest.approx(.0001)
    assert x["high95"] == pytest.approx(.0001)
    assert lab.historical_stability(a, b)["worst_fifteen_draw_edge"] == pytest.approx(.0001)
    with pytest.raises(ValueError, match="60"):
        lab.paired_circular_block_ci(a[:20], b[:20])


def test_registration_is_sha_locked_does_not_modify_registered_fifth_expert(lab_root):
    out = lab_root / "loto7_agent_output"
    previous = {p.name: p.read_bytes() for p in out.iterdir()}
    candidate_registration = json.loads((out / candidate.REG).read_text())
    first = lab.register(lab_root, out, candidate_registration, 699, CLOCK)
    assert first["promotion_role"] == "read_only_diagnostic"
    assert first["algorithm_manifest"]["single_future_e_hypothesis"] == lab.EXPECTED_HYPOTHESIS
    assert first == lab.register(lab_root, out, candidate_registration, 699, CLOCK)
    for name, original in previous.items():
        assert (out / name).read_bytes() == original
    path = lab_root / "advanced_validation_lab.py"
    path.write_text(path.read_text() + "\n# code changed after preregistration\n")
    with pytest.raises(ValueError, match="protocol drift"):
        lab.register(lab_root, out, candidate_registration, 699, CLOCK)


def test_cannot_register_future_hypothesis_after_first_possible_result(lab_root):
    out = lab_root / "loto7_agent_output"
    candidate_registration = json.loads((out / candidate.REG).read_text())
    with pytest.raises(ValueError, match="after first possible"):
        lab.register(lab_root, out, candidate_registration, 701, CLOCK)


def test_full_readonly_pipeline_with_real_original_699_evidence(lab_root, monkeypatch):
    out = lab_root / "loto7_agent_output"
    original = {p.name: p.read_bytes() for p in out.iterdir()}
    # The costly fair-world experiment is verified in dedicated CI's PR real
    # dry-run; unit tests isolate ledger semantics and no-write permissions.
    synthetic = {
        "scope": "reused_history_exploratory_not_independent_evidence",
        "round_start": 640, "round_end": 699,
        "original_four": {"mean_log_edge": .001},
        "candidate_five": {"mean_log_edge": -.002},
        "paired_block_bootstrap": {"low95": -.004, "high95": .003},
        "stability_diagnostics": {"fifteen_draw_mean_edges_five_minus_four": [0.0] * 4},
        "matched_full_budget_fair_draws": {
            "worlds": lab.WORLD_COUNT,
            "max_statistic_selection_adjusted_empirical_tail_p": 1
        }
    }
    monkeypatch.setattr(lab, "historical_research", lambda _x: copy.deepcopy(synthetic))
    result = lab.run(lab_root, out, now=CLOCK)
    assert result["future_e_monitor"]["verified_prefrozen_draws"] == 0
    assert result["future_e_monitor"]["current_e_value"] == 1
    assert not result["automatic_model_selection"]
    assert not result["production_changed"]
    assert not result["champion_changed"]
    assert not result["registered_existing_shadows_changed"]
    assert result["latest_seen_round"] == 699
    for name, data in original.items():
        assert (out / name).read_bytes() == data
    assert {p.name for p in out.iterdir()} - original.keys() == {lab.REG, lab.SUMMARY, lab.REPORT}



def test_missing_first_prefreeze_after_round_701_cannot_be_audited_as_zero_evidence(lab_root, monkeypatch):
    out = lab_root / "loto7_agent_output"
    candidate_registration = json.loads((out / candidate.REG).read_text())
    # Preregister the advanced evaluator before any synthetic future outcome.
    lab.register(lab_root, out, candidate_registration, 699, CLOCK)
    original_validator = lab.ledger.validated_draws
    x, clean, _ = original_validator(lab_root / "loto7.csv")
    # Synthetic future clock/round, not the live repository's CSV or registrations.
    monkeypatch.setattr(lab.ledger, "validated_draws", lambda _: (x, clean, 701))
    with pytest.raises(ValueError, match="missing required prospective target freeze"):
        lab.run(lab_root, out, now=CLOCK + timedelta(days=12))
