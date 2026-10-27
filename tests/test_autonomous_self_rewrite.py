"""Automatic research-code rewriting without unverified Production promotion."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

import autonomous_evolution_lab as old
import autonomous_self_rewrite as rw

ROOT = Path(__file__).resolve().parents[1]


def root_if_consistent():
    # The project's broad CI intentionally installs *pinned 699 history*
    # while retaining latest 700 autonomous ledgers. Research source must
    # not try to rewrite from a mixed snapshot.
    state_path = ROOT / "loto7_agent_output" / old.STATE
    if not state_path.exists():
        pytest.skip("pinned regression fixture omits the live autonomous learning state")
    s = json.loads(state_path.read_text())
    draw = hashlib.sha256((ROOT / "loto7.csv").read_bytes()).hexdigest()
    if s["data_sha256"] != draw:
        pytest.skip("pinned-699 fixture has stale 700 learned candidate")
    return ROOT


def test_exact_generated_source_is_parseable_research_only():
    data_sha = "a" * 64
    state_sha = "f" * 64
    code = rw.generate_source(config={"window": 30, "prior": 100, "blend": 0.25},
                              candidate_id="f" * 20, data_sha=data_sha,
                              source_state_sha=state_sha)
    tree = ast.parse(code)
    assert tree.body[-1].name == "probability_vector"
    assert "from autonomous_evolution_lab import prior_probabilities" in code
    assert "DRAW_HISTORY_SHA256 = " in code
    assert "def probability_vector(prior_history)" in code
    assert "model_champion" not in code
    assert "os.system" not in code
    assert code == rw.generate_source(
        config={"window": 30, "prior": 100, "blend": 0.25},
        candidate_id="f" * 20, data_sha=data_sha, source_state_sha=state_sha
    )


@pytest.mark.parametrize("config", [
    {"window": 19, "prior": 100, "blend": 0.25},
    {"window": 181, "prior": 100, "blend": 0.25},
    {"window": 30, "prior": 49, "blend": 0.25},
    {"window": 30, "prior": 401, "blend": 0.25},
    {"window": 30, "prior": 100, "blend": 1.0},
    {"window": 30, "prior": 100, "blend": float("nan")},
    {"window": "30", "prior": 100, "blend": 0.25},
    {"window": 30, "prior": 100, "blend": 0.25, "code": "exec(...)"},
])
def test_reject_unbounded_research_code_mutation(config):
    with pytest.raises(ValueError):
        rw.validate_model(config)


def test_prevent_untrusted_source_injection_and_bad_sha():
    with pytest.raises(ValueError):
        rw.generate_source(config={"window": 30, "prior": 100, "blend": 0.25},
                           candidate_id="__import__('os').system('pwd')",
                           data_sha="a" * 64, source_state_sha="b" * 64)


def test_current_learned_state_is_consistent_and_rewritable(tmp_path):
    root = root_if_consistent()
    report = rw.apply(root, tmp_path)
    assert report["decision"] == "GENERATE_RESEARCH_SOURCE_ONLY"
    assert report["auto_research_source_rewrite"]
    assert report["trusted_latest_source"]
    assert report["learned_candidate_id"]
    assert report["new_experiment_trials"] == 0
    assert report["historical_only_not_independent"]
    assert not report["champion_changed"]
    assert not report["frozen_future_oos_modified"]
    path = tmp_path / rw.SOURCE
    assert path.exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == report["source_sha256"]
    saved = json.loads((tmp_path / rw.MANIFEST).read_text())
    assert saved == report
    assert saved["promotion"]["operational_promotion_path"] == (
        "existing_research_v4_no_production_strict_oos"
    )
    assert not saved["promotion"]["candidate_research_source_itself_eligible"]


def test_rewrite_is_deterministic_across_runs(tmp_path):
    root = root_if_consistent()
    a = rw.apply(root, tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    b = rw.apply(root, tmp_path)
    assert a == b
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_rewritten_program_produces_valid_prior_only_probabilities(tmp_path):
    root = root_if_consistent()
    r = rw.apply(root, tmp_path)
    # Only the known locally generated module is imported. Never import
    # arbitrary web/paper/user code from a mutable source path.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "read_only_generated_research_strategy", tmp_path / rw.SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from loto7_evolving_agent import make_history, read_csv_flexible
    x, _ = make_history(read_csv_flexible(root / "loto7.csv"))
    actual = module.probability_vector(x[:-1])
    expected = old.prior_probabilities(x[:-1], r["learned_config"])
    import numpy as np
    np.testing.assert_array_equal(actual, expected)
    assert len(actual) == 37 and abs(actual.sum() - 7) < 1e-10


def test_stale_learned_history_is_quarantined(tmp_path, monkeypatch):
    root = root_if_consistent()
    inspect = rw.lab.inspect
    def fake(root):
        info, history = inspect(root)
        info = {**info, "data_sha256": "0" * 64}
        return info, history
    monkeypatch.setattr(rw.lab, "inspect", fake)
    report = rw.apply(root, tmp_path)
    assert report["decision"] == "WAIT_FOR_TRUSTED_RESEARCH_LEADER"
    assert not report["auto_research_source_rewrite"]
    assert not (tmp_path / rw.SOURCE).exists()


def test_bad_journal_leader_is_rejected(monkeypatch):
    root = root_if_consistent()
    original = rw.lab.load_required
    def broken(path):
        doc = original(path)
        if path.name == rw.lab.STATE:
            doc = copy.deepcopy(doc)
            doc["diagnostic_leader"] = "0" * 20
        return doc
    monkeypatch.setattr(rw.lab, "load_required", broken)
    with pytest.raises(ValueError, match="leader mismatch"):
        rw.plan(root)


def test_forged_positive_historical_score_is_rejected(monkeypatch):
    root = root_if_consistent()
    original = rw.lab.load_required
    def forged(path):
        doc = original(path)
        if path.name == rw.lab.STATE:
            doc = copy.deepcopy(doc)
            for trial in doc["trials"]:
                trial["diagnostic"]["mean_log_edge"] = 9.9
        return doc
    monkeypatch.setattr(rw.lab, "load_required", forged)
    with pytest.raises(ValueError, match="cannot be independently reproduced"):
        rw.plan(root)


def test_existing_oos_promotion_never_passes_false_high_score_only(tmp_path):
    root = root_if_consistent()
    info, _ = rw.lab.inspect(root)
    status = rw.prospective_promotion_status(root, info)
    assert status["automated_when_new_verified_draw_is_graded"] is True
    assert status["early_retroactive_promotion_allowed"] is False
    assert status["source_verified_for_current_read"] is True
    assert status["candidate_research_source_itself_eligible"] is False
    assert isinstance(status["eligible_existing_oos_candidates"], list)


def test_any_candidate_promotion_still_needs_real_prefrozen_oos(monkeypatch):
    root = root_if_consistent()
    info, _ = rw.lab.inspect(root)
    def fake(*args):
        return [(100.0, {
            "candidate_version": "forged-historical-winner",
            "champion_version": "baseline-5fdb8dc2ad",
            "config": {"name": "baseline", "eta": 3, "decay": 0.995,
                       "expert_uniform_mix": .15, "final_uniform_mix": .2,
                       "overlap_penalty": .65},
            "trusted_draws": 99, "matched_ensemble_trusted_draws": 99,
            "strict_random_valid": True, "strict_matched_ensemble_valid": True,
        })]
    monkeypatch.setattr(rw.ensemble, "promotion_candidates", fake)
    with pytest.raises(ValueError, match="inconsistent OOS promotion evidence"):
        rw.prospective_promotion_status(root, info)


def test_research_run_never_changes_protected_paths(tmp_path):
    root = root_if_consistent()
    protected = [
        "loto7.csv", "loto7_agent_output/model_champion.json",
        "loto7_agent_output/source_validation.json",
        "loto7_agent_output/autonomous_evolution_journal.jsonl",
        "research/disjoint_future_oos/freeze_0701.json",
        "loto7_agent_output/future_holdout_state.json",
    ]
    before = {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
              for p in protected}
    rw.apply(root, tmp_path)
    after = {p: hashlib.sha256((root / p).read_bytes()).hexdigest()
             for p in protected}
    assert after == before
