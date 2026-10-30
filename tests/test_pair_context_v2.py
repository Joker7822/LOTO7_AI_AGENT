"""Regression tests for an explicitly versioned, non-promotable numerical repair."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

import pair_context_v2 as v2
from loto7_evolving_agent import expert_probabilities, make_history, read_csv_flexible
from agent_operations_planner import build_plan
from tests.test_agent_operations_planner import snapshot


def test_int8_matrix_overflow_is_fixed_before_multiplication():
    x = np.zeros((128, 37), dtype=np.int8)
    x[:, :7] = 1
    legacy_co = x.T @ x
    assert np.all(legacy_co[:7, :7] == -128)
    correct = v2.exact_cooccurrence(x)
    assert np.all(correct[:7, :7] == 128)
    assert np.count_nonzero(legacy_co.astype(np.int64) != correct) == 49
    actual = v2.probability(x)
    assert actual.shape == (37,)
    assert np.isfinite(actual).all()
    assert (actual > 0).all()
    assert actual.sum() == pytest.approx(1.0, abs=1e-12)
    assert not np.allclose(actual, v2.legacy_probability(x))


def test_fixed_math_agrees_with_original_before_int8_wrap():
    rng = np.random.default_rng(774)
    x = np.zeros((80, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, size=7, replace=False)] = 1
    np.testing.assert_allclose(
        v2.probability(x), expert_probabilities(x)["pair_context"], rtol=0, atol=1e-14
    )
    np.testing.assert_allclose(
        v2.legacy_probability(x), expert_probabilities(x)["pair_context"], rtol=0, atol=1e-14
    )


def test_corrected_candidate_cannot_use_future_result():
    rng = np.random.default_rng(299)
    x = np.zeros((160, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, size=7, replace=False)] = 1
    original = v2.probability(x[:139])
    modified = x.copy()
    modified[139:] = 0
    modified[139:, :7] = 1
    np.testing.assert_array_equal(original, v2.probability(modified[:139]))


@pytest.mark.parametrize("bad", [
    np.zeros((20, 37), dtype=np.int8),
    np.ones((25, 36), dtype=np.int8),
    np.ones((19, 37), dtype=np.int8),
    np.full((30, 37), 2, dtype=np.int64),
    np.ones((28, 37), dtype=float),
])
def test_rejects_malformed_prospective_inputs(bad):
    with pytest.raises(ValueError):
        v2.probability(bad)


def test_real_draws_are_examined_without_evidence_changes(tmp_path):
    csv = Path("loto7.csv")
    before = csv.read_bytes()
    report = v2.diagnostics(csv, last_n=15)
    assert report["version"] == v2.VERSION
    assert report["history_draws"] >= 699
    assert report["int64_corrupted_cooccurrence_cells"] == 0
    assert report["int8_corrupted_cooccurrence_cells"] >= 0
    assert report["evaluated_rounds"] == list(range(
        report["history_draws"] - 14, report["history_draws"] + 1
    ))
    assert report["chronological_prior_only"]
    assert report["historical_selection_only"]
    assert not report["independent_evidence"]
    assert not report["prospective_edge_confirmed"]
    assert report["legacy_runtime_still_uses_v1"]
    assert not report["production_changed"]
    assert not report["future_oos_changed"]
    assert not report["promotion_authorized"]
    assert len(report["latest_v2_p_sha256"]) == 64
    assert csv.read_bytes() == before
    assert not list(tmp_path.iterdir())


def test_registered_frozen_experiment_implementation_is_not_changed():
    # Existing baseline and official frozen forecasts must replay identically.
    # A separate v2 module means old one is still addressable.
    legacy = Path("loto7_evolving_agent.py").read_text(encoding="utf-8")
    assert "co = hist.T @ hist" in legacy
    assert "from loto7_evolving_agent import" in Path("loto7_v2_runner.py").read_text()
    assert "pair_context_v2" not in Path("loto7_v2_runner.py").read_text()
    assert "pair_context_v2" not in Path("weekly_production_prediction.py").read_text()


def test_26_draws_waiting_is_informational_after_both_701_freezes():
    data = snapshot()
    data["sources"]["source"]["latest"]["round"] = 700
    data["sources"]["holdout"]["trusted_draws"] = 7
    data["sources"]["signal"]["current_target_round"] = 701
    data["sources"]["learning"]["current_prefrozen_target"] = 701
    plan = build_plan(data)
    assert plan["counts"]["watch"] == 0
    assert plan["counts"]["info"] == 1
    assert plan["overall"] == "ok"
    item = next(t for t in plan["tasks"] if t["code"] == "COUNCIL:NO_EARLY_PORTFOLIO_CLAIM")
    assert item["priority"] == "info"
    assert not plan["authority"]["model_promotions"]


def test_missing_701_freeze_does_not_hide_holdout_warning():
    data = snapshot()
    data["sources"]["source"]["latest"]["round"] = 700
    data["sources"]["signal"]["current_target_round"] = 701
    data["sources"]["learning"]["current_prefrozen_target"] = None
    plan = build_plan(data)
    assert any(t["code"] == "COUNCIL:NO_EARLY_PORTFOLIO_CLAIM"
               and t["priority"] == "watch" for t in plan["tasks"])
    assert any(t["code"] == "FIRST_FREEZE_REQUIRED:learning" for t in plan["tasks"])


def test_never_label_incomplete_horizon_as_confirmed():
    data = snapshot()
    data["sources"]["source"]["latest"]["round"] = 700
    data["sources"]["signal"]["current_target_round"] = 701
    data["sources"]["learning"]["current_prefrozen_target"] = 701
    data["sources"]["holdout"]["trusted_draws"] = 6
    data["series"]["portfolio"].pop()
    plan = build_plan(data)
    assert plan["checkpoints"]["portfolio"]["trusted_draws"] == 6
    assert plan["checkpoints"]["portfolio"]["fixed_horizon"] == 26
    assert plan["overall"] == "ok"
    assert "confirmed" not in json.dumps(plan).lower()


@pytest.mark.parametrize("draws", [127, 128, 255, 256, 512, 700])
def test_independent_reference_exact_across_integer_wrap_boundaries(draws):
    x = np.zeros((draws, 37), dtype=np.int8)
    x[:, :7] = 1
    independent = v2.independent_cooccurrence(x)
    np.testing.assert_array_equal(v2.checked_cooccurrence(x), independent)
    assert independent.dtype == np.int64
    assert np.all(independent[:7, :7] == draws)
    assert np.all(independent[7:, :] == 0)
    np.testing.assert_array_equal(
        v2.checked_cooccurrence(x.astype(np.int16)), independent
    )
    np.testing.assert_array_equal(
        v2.checked_cooccurrence(x.astype(np.int64)), independent
    )
    legacy = x.T @ x
    if draws >= 128:
        assert np.any(legacy.astype(np.int64) != independent)


def test_independent_oracle_catches_silent_integer_wrap(monkeypatch):
    x = np.zeros((256, 37), dtype=np.int8)
    x[:, :7] = 1
    # Simulate a plausible regression: a future contributor returns the
    # wrapped legacy matrix as if it were the corrected int64 calculation.
    monkeypatch.setattr(
        v2, "exact_cooccurrence",
        lambda history: (v2.validated_history(history).astype(np.int8).T @
                         v2.validated_history(history).astype(np.int8)).astype(np.int64),
    )
    with pytest.raises(ArithmeticError, match="independent int64 verification"):
        v2.checked_cooccurrence(x)


def test_validation_never_publishes_false_pass_when_numeric_kernel_regresses(tmp_path, monkeypatch):
    import sys

    out = tmp_path / "pair_context_v2_validation.json"
    before = Path("loto7.csv").read_bytes()
    monkeypatch.setattr(
        v2, "exact_cooccurrence",
        lambda history: np.zeros((37, 37), dtype=np.int64),
    )
    monkeypatch.setattr(
        sys, "argv", ["pair_context_v2.py", "--csv", "loto7.csv",
                      "--out", str(out), "--last-n", "3"],
    )
    with pytest.raises(ArithmeticError, match="independent int64 verification"):
        v2.main()
    assert not out.exists()
    assert Path("loto7.csv").read_bytes() == before


def test_numeric_diagnostic_has_auditable_independent_oracle():
    report = v2.diagnostics(Path("loto7.csv"), last_n=3)
    check = report["numerical_verification"]
    assert check["status"] == "pass"
    assert check["independent_method"] == "pairwise_boolean_intersection_counts"
    assert check["matrix_cells_checked"] == 37 * 37
    assert check["diagonal_marginals_verified"] is True
    assert check["symmetry_verified"] is True
    assert check["int64_cast_before_matrix_product"] is True
    assert check["fail_closed_on_any_mismatch"] is True
    assert check["historical_only"] is True
    assert check["automatic_model_promotion_authorized"] is False
    assert report["int64_corrupted_cooccurrence_cells"] == 0
    assert report["prospective_edge_confirmed"] is False
    assert report["promotion_authorized"] is False


def test_scheduled_publisher_script_parses_as_valid_bash():
    # PR workflows skip publishing. Validate the exact production run-block
    # without running any git commands or touching repository content.
    import subprocess

    yaml = Path(".github/workflows/pair_context_v2.yml").read_text(encoding="utf-8")
    marker = "      - name: Persist only versioned diagnostic (never old forecasts)\n"
    assert yaml.count(marker) == 1
    block = yaml.split(marker, 1)[1].split("        run: |\n", 1)[1]
    assert block.lstrip().startswith("set -euo pipefail")
    shell_lines = block.splitlines()
    assert all(not line.strip() or line.startswith("          ")
               for line in shell_lines)
    shell = "\n".join(line[10:] for line in shell_lines) + "\n"
    result = subprocess.run(["bash", "-n"], input=shell, text=True,
                            capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "python - <<'PY'" in shell
    assert "\nPY\n" in shell
