"""Synthetic strictly future-only online v2 lifecycle; no real result edits."""
from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

import online_learning_boost_v2 as v2
from loto7_evolving_agent import fingerprint_file


def sample_root(tmp_path: Path) -> Path:
    root = tmp_path / "simulation"
    root.mkdir()
    for name in v2.LOCKED_CODE:
        shutil.copyfile(Path(name), root / name)
    rng = np.random.default_rng(78221105)
    initial_date = datetime(2026, 10, 30) - timedelta(days=700 * 7)
    with (root / "loto7.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["回別", "抽せん日", "本数字", "ボーナス数字"])
        writer.writeheader()
        for i in range(701):
            nums = rng.choice(37, 9, replace=False) + 1
            writer.writerow({
                "回別": "第" + str(i + 1) + "回",
                "抽せん日": (initial_date + timedelta(days=7 * i)).date().isoformat(),
                "本数字": " ".join(f"{n:02d}" for n in sorted(nums[:7])),
                "ボーナス数字": " ".join(f"{n:02d}" for n in sorted(nums[7:])),
            })
    write_source(root, 701, "2026-11-06")
    return root


def latest_data(root: Path) -> dict:
    with (root / "loto7.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    last = rows[-1]
    return {
        "round": len(rows), "date": last["抽せん日"],
        "main": [int(v) for v in last["本数字"].split()],
        "bonus": [int(v) for v in last["ボーナス数字"].split()],
    }


def write_source(root: Path, next_round: int, next_date: str, trusted: bool = True):
    last = latest_data(root)
    record = {
        "status": "ok" if trusted else "degraded",
        "verification": "verified_two_result_sources"
                        if trusted else "unverified_single_source",
        "latest": last,
        "sources": {
            "independent_synthetic_publisher": dict(last),
            "official_schedule": {"round": next_round + 1, "date": next_date},
        },
        "verification_provenance": {
            "draw_csv_sha256": fingerprint_file(root / "loto7.csv")},
    }
    (root / "source.json").write_text(json.dumps(record), encoding="utf-8")


def append_result_702(root: Path):
    with (root / "loto7.csv").open("a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow([
            "第702回", "2026-11-06",
            "02 04 06 08 10 12 14", "21 35",
        ])
    write_source(root, 702, "2026-11-13")


def execute(root: Path, date: str = "2026-11-05"):
    return v2.run(root, root / v2.DESTINATION, root / "source.json",
                  now=datetime.fromisoformat(date + "T10:00:00+09:00"))


def test_v2_freezes_exactly_one_unseen_future_target_and_is_idempotent(tmp_path):
    root = sample_root(tmp_path)
    first = execute(root)
    assert first["target_round"] == 702 and first["trusted_grades"] == 0
    assert first["production_modified"] is False
    assert first["model_promotion_authorized"] is False
    p = root / v2.DESTINATION
    bytes_before = p.read_bytes()
    second = execute(root)
    assert second == first and p.read_bytes() == bytes_before
    book = json.loads(p.read_text())
    assert len(book["events"]) == 1
    pred = book["events"][0]["prediction"]
    assert len(pred["probabilities"]) == 37
    assert sum(pred["probabilities"]) == pytest.approx(7, abs=1e-9)
    assert pred["expert_score_before"] == [0] * 4
    assert pred["prior_verified_grades"] == 0
    assert pred["uniform_anchor"] == 0.30


def test_verified_result_scores_old_freeze_then_online_updates_next(tmp_path):
    root = sample_root(tmp_path)
    first = execute(root)
    old_sha = json.loads((root / v2.DESTINATION).read_text())["events"][0]["event_sha256"]
    append_result_702(root)
    second = execute(root, "2026-11-07")
    assert second["target_round"] == 703 and second["trusted_grades"] == 1
    ledger = json.loads((root / v2.DESTINATION).read_text())
    assert [event["kind"] for event in ledger["events"]] == ["freeze", "grade", "freeze"]
    assert ledger["events"][1]["grade"]["frozen_event_sha256"] == old_sha
    assert ledger["events"][1]["grade"]["actual_numbers"] == [2, 4, 6, 8, 10, 12, 14]
    assert any(abs(t) > 1e-12 for t in ledger["events"][2]["prediction"]["expert_score_before"])
    second_time = (root / v2.DESTINATION).read_bytes()
    assert execute(root, "2026-11-07") == second
    assert (root / v2.DESTINATION).read_bytes() == second_time


def test_unverified_outcome_never_enters_learning(tmp_path):
    root = sample_root(tmp_path)
    execute(root)
    p = root / v2.DESTINATION
    before = p.read_bytes()
    append_result_702(root)
    write_source(root, 702, "2026-11-13", trusted=False)
    result = execute(root, "2026-11-07")
    assert result["status"] == "awaiting_independent_result_verification"
    assert result["trusted_grades"] == 0 and p.read_bytes() == before


def test_no_late_registration_or_backdated_freeze(tmp_path):
    root = sample_root(tmp_path)
    with pytest.raises(ValueError, match="scheduled draw date"):
        execute(root, "2026-11-06")
    assert not (root / v2.DESTINATION).exists()
    append_result_702(root)
    with pytest.raises(ValueError, match="backdate"):
        execute(root, "2026-11-07")


def test_tampering_and_registered_code_changes_fail_closed(tmp_path):
    root = sample_root(tmp_path)
    execute(root)
    p = root / v2.DESTINATION
    state = json.loads(p.read_text())
    state["events"][0]["prediction"]["probabilities"][0] += 0.01
    p.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="hash invalid"):
        execute(root)
    p.write_text(json.dumps({**state, "events": []}))
    with pytest.raises(ValueError, match="one ungraded freeze"):
        execute(root)
    p.unlink()
    execute(root)
    code = root / "online_learning_boost_v2.py"
    code.write_text(code.read_text() + "\n# unauthorized change\n")
    with pytest.raises(ValueError, match="algorithm changed"):
        execute(root)


def test_predeclared_drift_fallback_and_no_future_outcome_dependency():
    rng = np.random.default_rng(99)
    x = np.zeros((130, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, size=7, replace=False)] = 1
    es, ms, edges = v2.initial_state()
    normal = v2.prediction(x, es, ms, edges)
    drift = v2.prediction(x, es, ms, [-0.1] * v2.DRIFT_WINDOW)
    assert normal["uniform_anchor"] == v2.NORMAL_UNIFORM_ANCHOR
    assert drift["uniform_anchor"] == v2.DRIFT_UNIFORM_ANCHOR
    assert drift["drift_guard_active"] is True
    assert normal["drift_guard_active"] is False
    assert drift["prefix_sha256"] == normal["prefix_sha256"]
    changed_future = np.vstack([x, np.zeros(37, dtype=np.int8)])
    assert v2.prediction(changed_future[:-1], es, ms, edges) == normal
