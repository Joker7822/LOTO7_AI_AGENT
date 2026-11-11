"""Reproducible registered-v2 replay; past v2 predictions are never rewritten."""
from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

import online_learning_boost_v2 as v2
import online_v2_replay_runtime as compat
from online_v3_replay_runtime import ABS_REPLAY_TOL


@pytest.fixture
def recorded_research(tmp_path):
    # The repository-wide regression suite intentionally substitutes a
    # canonical 699-draw fixture. It MUST NOT pretend that its CSV verifies
    # the separately committed real 702/703 prospective record. Dedicated
    # online-v2 CI checks the complete real archive on untouched main data.
    source = json.loads(Path("loto7_agent_output/source_validation.json").read_text(
        encoding="utf-8"))
    if source.get("latest", {}).get("round") != 702:
        pytest.skip("real 702/703 SHA-locked archive requires the live current dataset")
    root = tmp_path / "sealed_v2"
    root.mkdir()
    for name in v2.LOCKED_CODE:
        shutil.copyfile(Path(name), root / name)
    shutil.copyfile("loto7.csv", root / "loto7.csv")
    (root / "loto7_agent_output").mkdir()
    shutil.copyfile(
        "loto7_agent_output/source_validation.json",
        root / "loto7_agent_output/source_validation.json")
    (root / "research/online_learning_v2").mkdir(parents=True)
    shutil.copyfile(
        "research/online_learning_v2/state.json",
        root / "research/online_learning_v2/state.json")
    return root


def today():
    return datetime.fromisoformat("2026-11-12T09:30:00+09:00")


def test_registered_v2_real_702_grade_703_freeze_idempotent(recorded_research):
    root = recorded_research
    f = root / v2.DESTINATION
    before = f.read_bytes()
    result = compat.run(root, now=today())
    assert result["target_round"] == 703
    assert result["trusted_grades"] == 1
    assert result["frozen_past_events_rewritten"] is False
    assert result["registered_algorithm_modified"] is False
    assert f.read_bytes() == before
    assert compat.run(root, now=today())["target_round"] == 703
    assert f.read_bytes() == before


def test_micro_float_mismatch_in_replay_is_accepted_without_changing_state(
        recorded_research, monkeypatch):
    root = recorded_research
    f = root / v2.DESTINATION
    before = f.read_bytes()
    orig_predict, orig_assess = v2.prediction, v2.assessment

    def tiny_predict(*a):
        generated = orig_predict(*a)
        generated["probabilities"][0] += 1e-14
        generated["track_predictions"][1][3] -= 1e-14
        return generated

    def tiny_assess(*a):
        grade = orig_assess(*a)
        grade["model_brier_edge_vs_uniform"] += 1e-14
        return grade

    monkeypatch.setattr(v2, "prediction", tiny_predict)
    monkeypatch.setattr(v2, "assessment", tiny_assess)
    result = compat.run(root, now=today())
    assert result["target_round"] == 703
    assert f.read_bytes() == before
    assert abs(1e-14) < ABS_REPLAY_TOL


@pytest.mark.parametrize("corruption", [
    "probabilities", "top7", "prefix", "drift",
    "grade", "shape", "nonfinite",
])
def test_real_prediction_or_grade_change_blocks_replay(
        recorded_research, monkeypatch, corruption):
    root = recorded_research
    file = root / v2.DESTINATION
    original = file.read_bytes()
    orig_predict, orig_assess = v2.prediction, v2.assessment
    if corruption == "grade":
        def altered_grade(*args):
            d = orig_assess(*args)
            d["model_log_edge_vs_uniform"] += 1e-4
            return d
        monkeypatch.setattr(v2, "assessment", altered_grade)
    else:
        def altered_predict(*args):
            d = orig_predict(*args)
            if corruption == "probabilities":
                d["probabilities"][1] += 1e-5
            elif corruption == "top7":
                d["top7"] = list(range(1, 8))
            elif corruption == "prefix":
                d["prefix_sha256"] = "x" * 64
            elif corruption == "drift":
                d["drift_guard_active"] = True
            elif corruption == "shape":
                d["probabilities"].append(0.1)
            else:
                d["probabilities"][0] = float("nan")
            return d
        monkeypatch.setattr(v2, "prediction", altered_predict)
    with pytest.raises((ValueError, RuntimeError),
                       match="MATERIAL|nonfinite|replay|changed|exact|drift"):
        compat.run(root, now=today())
    assert file.read_bytes() == original


def test_sha_chain_tampering_remains_fatal(recorded_research):
    root = recorded_research
    file = root / v2.DESTINATION
    d = json.loads(file.read_text(encoding="utf-8"))
    d["events"][0]["prediction"]["top7"] = [1, 2, 3, 4, 5, 6, 7]
    file.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="hash invalid"):
        compat.run(root, now=today())


def test_existing_prefreeze_can_safely_resume_702_grade(recorded_research):
    root = recorded_research
    file = root / v2.DESTINATION
    d = json.loads(file.read_text(encoding="utf-8"))
    original_sha = d["events"][0]["event_sha256"]
    d["events"] = d["events"][:1]  # valid authentic pre-draw 702 freeze
    d["trusted_grades"] = 0
    file.write_text(json.dumps(d), encoding="utf-8")
    result = compat.run(root, now=today())
    saved = json.loads(file.read_text(encoding="utf-8"))
    assert result["target_round"] == 703
    assert [(e["kind"], e["target_round"]) for e in saved["events"]] == [
        ("freeze", 702), ("grade", 702), ("freeze", 703)]
    assert saved["events"][0]["event_sha256"] == original_sha


def test_missing_prior_freeze_does_not_enable_retrospective_grading(
        recorded_research):
    root = recorded_research
    file = root / v2.DESTINATION
    d = json.loads(file.read_text(encoding="utf-8"))
    d["events"] = [d["events"][1]]  # orphan grade with no preceding freeze
    d["trusted_grades"] = 0
    before = json.dumps(d)
    file.write_text(before, encoding="utf-8")
    with pytest.raises(ValueError, match="hash invalid|not frozen|future target|missing"):
        compat.run(root, now=today())
    assert file.read_text(encoding="utf-8") == before
