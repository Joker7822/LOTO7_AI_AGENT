"""Deterministic, isolated future-only tests for advanced online v3."""
from __future__ import annotations

import csv
import itertools
import json
import math
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

import advanced_online_v3 as v3
from loto7_evolving_agent import fingerprint_file


CLOCK = datetime.fromisoformat("2026-11-06T10:13:00+09:00")
SCHEDULE_703 = "2026-11-13"
SCHEDULE_704 = "2026-11-20"


def make_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "v3-synthetic-world"
    root.mkdir()
    for name in v3.ALLOWED_FILES:
        shutil.copyfile(Path(name), root / name)
    (root / "loto7_agent_output").mkdir()
    rng = np.random.default_rng(250360)
    first_day = datetime(2026, 10, 30) - timedelta(days=7 * 700)
    with (root / "loto7.csv").open("w", newline="", encoding="utf-8") as fd:
        writer = csv.DictWriter(fd, fieldnames=[
            "回別", "抽せん日", "本数字", "ボーナス数字"])
        writer.writeheader()
        for i in range(701):
            balls = rng.choice(37, 9, replace=False) + 1
            writer.writerow({
                "回別": "第" + str(i + 1) + "回",
                "抽せん日": (first_day + timedelta(days=7 * i)).date().isoformat(),
                "本数字": " ".join(str(v) for v in sorted(balls[:7])),
                "ボーナス数字": " ".join(str(v) for v in sorted(balls[7:])),
            })
    write_source(root, next_round=702, schedule="2026-11-06")
    return root


def latest(root: Path) -> dict:
    with (root / "loto7.csv").open(newline="", encoding="utf-8") as fd:
        rows = list(csv.DictReader(fd))
    last = rows[-1]
    return {
        "round": len(rows), "date": last["抽せん日"],
        "main": [int(v) for v in last["本数字"].split()],
        "bonus": [int(v) for v in last["ボーナス数字"].split()],
    }


def write_source(root: Path, next_round: int, schedule: str,
                 trusted: bool = True) -> None:
    result = latest(root)
    obj = {
        "status": "ok" if trusted else "degraded",
        "verification": ("verified_two_result_sources" if trusted
                         else "unverified_single_source"),
        "latest": result,
        "sources": {
            "independent_synthetic_publisher": dict(result),
            "official_schedule": {"round": next_round, "date": schedule},
        },
        "verification_provenance": {
            "draw_csv_sha256": fingerprint_file(root / "loto7.csv")
        },
    }
    (root / "loto7_agent_output/source_validation.json").write_text(
        json.dumps(obj), encoding="utf-8")


def append_round(root: Path, round_number: int, date: str,
                 main: str = "02 04 06 08 10 12 14") -> None:
    with (root / "loto7.csv").open("a", newline="", encoding="utf-8") as fd:
        csv.writer(fd).writerow([
            "第" + str(round_number) + "回", date, main, "27 35"])
    write_source(root, round_number + 1,
                 SCHEDULE_703 if round_number == 702 else SCHEDULE_704)


def prepare_703(root: Path) -> dict:
    assert v3.run(root, now=CLOCK)["status"] == "awaiting_verified_round_702"
    append_round(root, 702, "2026-11-06")
    return v3.run(root, now=datetime.fromisoformat(
        "2026-11-06T19:20:00+09:00"))


def test_exact_seven_of_37_subset_likelihood_is_normalized():
    uniform = np.ones(37)
    assert v3.set_likelihood_ratio(uniform, np.arange(7), 7) == pytest.approx(1)
    assert v3.set_likelihood_ratio(uniform, np.arange(17, 24), 7) == pytest.approx(1)
    # Exhaustive eight-of-three analogy verifies the elementary-symmetric
    # partition function and E_0[LR] = 1 independently of drawing outcomes.
    w = np.array([.4, 1.8, 1.5, 2.0, .5, 1.1, 1.3, .7])
    all_lr = [v3.set_likelihood_ratio(w, np.array(a), 3)
              for a in itertools.combinations(range(8), 3)]
    assert np.mean(all_lr) == pytest.approx(1.0, abs=1e-12)
    assert len(set(round(v, 4) for v in all_lr)) > 3
    with pytest.raises(ValueError, match="invalid fixed-size"):
        v3.set_likelihood_ratio(w, np.array([0, 0, 1]), 3)
    with pytest.raises(ValueError, match="invalid fixed-size"):
        v3.set_likelihood_ratio(w, np.array([0, 1, 8]), 3)


def test_pre_registration_cannot_rewrite_existing_v1_v2_or_claim_702(tmp_path):
    root = make_fixture(tmp_path)
    first = v3.run(root, now=CLOCK)
    assert first["status"] == "awaiting_verified_round_702"
    reg_file = root / v3.REGISTRATION
    reg = json.loads(reg_file.read_text())
    assert reg["first_target_round"] == 703
    assert reg["registered_latest_round"] == 701
    assert reg["production_promotion_authorized"] is False
    assert not (root / v3.STATE).exists()
    before = reg_file.read_bytes()
    assert v3.run(root, now=CLOCK) == first
    assert reg_file.read_bytes() == before


def test_first_703_freeze_then_graded_703_and_new_704_freeze(tmp_path):
    root = make_fixture(tmp_path)
    summary = prepare_703(root)
    assert summary["target_round"] == 703
    assert summary["future_verified_grades"] == 0
    assert summary["exact_set_e_value_capped"] == pytest.approx(1)
    assert not summary["research_evidence_gate_met"]
    assert not summary["production_modified"]
    record = json.loads((root / v3.STATE).read_text())
    issued = record["events"][0]
    assert issued["kind"] == "freeze"
    assert issued["scheduled_draw_date"] == SCHEDULE_703
    assert len(issued["prediction"]["expert_vectors"]) == 6
    assert len(issued["prediction"]["rate_predictions"]) == 3
    assert len(issued["prediction"]["temperature_candidates"]) == 3
    assert sum(issued["prediction"]["probabilities"]) == pytest.approx(7, abs=1e-9)
    immutable = (root / v3.STATE).read_bytes()
    assert v3.run(root, now=CLOCK)["target_round"] == 703
    assert (root / v3.STATE).read_bytes() == immutable
    append_round(root, 703, SCHEDULE_703)
    future = v3.run(root, now=datetime.fromisoformat(
        "2026-11-14T10:00:00+09:00"))
    assert future["target_round"] == 704
    assert future["future_verified_grades"] == 1
    record = json.loads((root / v3.STATE).read_text())
    assert [e["kind"] for e in record["events"]] == [
        "freeze", "grade", "freeze"]
    grade = record["events"][1]["metrics"]
    assert grade["actual_numbers"] == [2, 4, 6, 8, 10, 12, 14]
    assert grade["frozen_event_sha256"] == issued["event_sha256"]
    assert grade["exact_7_of_37_set_likelihood_ratio"] > 0
    assert math.isfinite(grade["e_process_log_mixture"])
    assert record["events"][2]["prediction"]["prior_verified_scores"] == 1


def test_unverified_result_cannot_advance(tmp_path):
    root = make_fixture(tmp_path)
    prepare_703(root)
    prior_bytes = (root / v3.STATE).read_bytes()
    append_round(root, 703, SCHEDULE_703)
    write_source(root, 704, SCHEDULE_704, trusted=False)
    result = v3.run(root, now=datetime.fromisoformat(
        "2026-11-14T10:00:00+09:00"))
    assert result["status"] == "awaiting_two_source_trusted_target"
    assert (root / v3.STATE).read_bytes() == prior_bytes


def test_corrupted_freeze_and_algorithm_drift_fail_closed(tmp_path):
    root = make_fixture(tmp_path)
    prepare_703(root)
    path = root / v3.STATE
    good = path.read_bytes()
    state = json.loads(good)
    state["events"][0]["prediction"]["probabilities"][0] += 0.001
    path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="chain tampered"):
        v3.run(root, now=CLOCK)
    path.write_bytes(good)
    model = root / "advanced_online_v3.py"
    model.write_text(model.read_text() + "\n# post-registration change\n")
    with pytest.raises(ValueError, match="protocol.*drift|source.*changed|registered"):
        v3.run(root, now=CLOCK)


def test_first_freeze_cannot_be_backdated_or_recovered(tmp_path):
    root = make_fixture(tmp_path)
    v3.run(root, now=CLOCK)
    append_round(root, 702, "2026-11-06")
    with pytest.raises(ValueError, match="backdate"):
        v3.run(root, now=datetime.fromisoformat(
            "2026-11-13T10:00:00+09:00"))
    assert not (root / v3.STATE).exists()
    append_round(root, 703, SCHEDULE_703)
    with pytest.raises(ValueError, match="already occurred"):
        v3.run(root, now=datetime.fromisoformat(
            "2026-11-14T10:00:00+09:00"))


def test_calibration_and_drift_depend_only_on_past_scores(tmp_path):
    root = make_fixture(tmp_path)
    prepare_703(root)
    from loto7_evolving_agent import make_history, read_csv_flexible
    x, _ = make_history(read_csv_flexible(root / "loto7.csv"))
    es, ms, ts, edges, wealth = v3.empty_scores()
    normal = v3.model_forecast(x, es, ms, ts, edges)
    drift = v3.model_forecast(
        x, es, ms, ts, [-0.2] * v3.DRIFT_WINDOW)
    assert normal["anchor_fraction"] == v3.UNIFORM_ANCHOR
    assert drift["anchor_fraction"] == v3.DRIFT_ANCHOR
    assert drift["drift_guard"]
    assert not normal["drift_guard"]
    assert drift["prefix_sha256"] == normal["prefix_sha256"]
    assert normal["probabilities"] != drift["probabilities"]
    changed_future = np.vstack([x, np.zeros(37, dtype=np.int8)])
    assert v3.model_forecast(
        changed_future[:-1], es, ms, ts, edges) == normal


def test_offline_math_has_no_external_inference_api(tmp_path):
    source = Path("advanced_online_v3.py").read_text(encoding="utf-8")
    assert "api.openai.com" not in source
    assert "OPENAI_API_KEY" not in source
    assert "models.github.ai" not in source
