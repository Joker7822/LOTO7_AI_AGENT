"""Synthetic lifecycle tests. All prospective activity is isolated to tmp_path.

The real repository is never given invented draw 700/701 outcomes.
"""
from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

import continuous_learning_agent as loop
from loto7_evolving_agent import make_history, read_csv_flexible


JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 10, 18, 10, 30, tzinfo=JST)


def write_result_report(root: Path, *, verified: bool) -> Path:
    x, clean = make_history(read_csv_flexible(root / "loto7.csv"))
    latest = clean.iloc[-1]
    rid = len(x)
    record = {
        "round": rid,
        "date": latest["抽せん日"].date().isoformat(),
        "main": [int(n+1) for n in np.flatnonzero(x[-1])],
        "bonus": [int(n) for n in str(latest["ボーナス数字"]).split()],
    }
    report = {
        "status": "ok" if verified else "degraded",
        "verification": "verified_two_result_sources" if verified else "degraded_single_result_source",
        "latest": record,
        "sources": {"rakuten_bank": dict(record)},
    }
    path = root / "source_validation_test.json"
    path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return path


def append_round(root: Path, target: int):
    csv_path = root / "loto7.csv"
    data = list(csv.DictReader(csv_path.open(encoding="utf-8-sig", newline="")))
    if len(data) != target - 1:
        raise ValueError("synthetic append must be sequential")
    # Fake, clearly tagged synthetic draw; user-visible real repo is untouched.
    new = {k: "" for k in data[0]}
    new.update({
        "抽せん日": "2026-10-23" if target == 700 else (
            "2026-10-30" if target == 701 else "2026-11-06"
        ),
        "本数字": "01 02 03 04 05 06 07" if target == 700 else "08 09 10 11 12 13 14",
        "ボーナス数字": "18 19",
        "回別": "第" + str(target) + "回",
    })
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writerow(new)


@pytest.fixture()
def sandbox(tmp_path):
    root = tmp_path / "synthetic-experiment"
    root.mkdir()
    (root / "out").mkdir()
    for name in (*loop.FILES_LOCKED, "loto7.csv"):
        shutil.copyfile(Path(name), root / name)
    return root


def execute(root: Path, verified: bool = True, *, clock=NOW):
    source = write_result_report(root, verified=verified)
    return loop.run(root, root / "out", source, now=clock)


def test_real_699_remains_unfrozen_and_registration_is_idempotent(sandbox):
    first = execute(sandbox)
    assert first["trusted_draws"] == 0
    assert first["current_prefrozen_target"] is None
    assert first["status"] == "waiting_for_verified_round_700_prefix"
    assert first["production_promotion_eligible"] is False
    assert first["p_value_authorized"] is False
    out = sandbox / "out"
    registered = (out / loop.REGISTRATION).read_bytes()
    second = execute(sandbox)
    assert first == second
    assert (out / loop.REGISTRATION).read_bytes() == registered
    assert not (out / loop.REGISTRY).exists()
    assert not (out / loop.FREEZES).exists()


def test_full_sequential_forecast_then_grade_then_evolve(sandbox):
    execute(sandbox)
    append_round(sandbox, 700)
    waiting = execute(sandbox, False)
    assert waiting["status"] == "awaiting_two_source_round_700"
    assert not (sandbox / "out" / loop.REGISTRY).exists()

    first = execute(sandbox, True)
    out = sandbox / "out"
    assert first["current_prefrozen_target"] == 701
    assert first["trusted_draws"] == 0
    frozen = loop.read_chain(out / loop.FREEZES, kind="freeze")
    assert len(frozen) == 1
    assert frozen[0]["base_round"] == 700
    assert len(frozen[0]["inclusion_p_canonical"]) == 37
    assert abs(sum(map(float, frozen[0]["inclusion_p_canonical"])) - 7) < 1e-9
    freeze_sha = frozen[0]["record_sha256"]
    assert execute(sandbox, True) == first
    assert loop.read_chain(out / loop.FREEZES, kind="freeze")[0]["record_sha256"] == freeze_sha

    append_round(sandbox, 701)
    not_yet = execute(sandbox, False)
    assert not_yet["status"] == "awaiting_two_source_verification"
    assert not (out / loop.RESULTS).exists()
    assert not_yet["current_prefrozen_target"] == 701

    progressed = execute(sandbox, True, clock=NOW + timedelta(days=12))
    assert progressed["trusted_draws"] == 1
    assert progressed["current_prefrozen_target"] == 702
    grades = loop.read_chain(out / loop.RESULTS, kind="grading")
    assert grades[0]["frozen_record_sha256"] == freeze_sha
    assert grades[0]["actual_numbers"] == list(range(8, 15))
    freezes = loop.read_chain(out / loop.FREEZES, kind="freeze")
    assert len(freezes) == 2
    assert freezes[1]["base_round"] == 701
    assert freezes[1]["target_round"] == 702
    assert freezes[0]["inclusion_p_sha256"] != freezes[1]["inclusion_p_sha256"]
    assert progressed["drift_monitoring"]["recent_observed_draws"] == 1
    assert execute(sandbox, True, clock=NOW + timedelta(days=12)) == progressed


def test_reject_frozen_vector_edits_even_when_source_is_trusted(sandbox):
    execute(sandbox)
    append_round(sandbox, 700)
    execute(sandbox)
    path = sandbox / "out" / loop.REGISTRY
    frozen = json.loads(path.read_text(encoding="utf-8"))
    frozen["top7_numbers"] = [1, 2, 3, 4, 5, 6, 7]
    path.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="registry changed"):
        execute(sandbox)


def test_algorithm_sha_lock_fails_closed_after_registration(sandbox):
    execute(sandbox)
    path = sandbox / "predictive_expert_agent.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n# illegal post-registration drift\n")
    with pytest.raises(ValueError, match="SHA drift"):
        execute(sandbox)


def test_reject_confirmed_source_numbers_that_conflict_with_csv(sandbox):
    execute(sandbox)
    path = write_result_report(sandbox, verified=True)
    data = json.loads(path.read_text())
    data["latest"]["main"] = [1, 2, 3, 4, 5, 6, 7]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="conflicts"):
        loop.run(sandbox, sandbox / "out", path, now=NOW)


def test_skip_to_already_observed_701_without_initial_freeze_is_blocked(sandbox):
    execute(sandbox)
    append_round(sandbox, 700)
    append_round(sandbox, 701)
    with pytest.raises(ValueError, match="without pre-draw freeze"):
        execute(sandbox)


def test_existing_graded_history_checked_against_independent_csv(sandbox):
    execute(sandbox)
    append_round(sandbox, 700)
    execute(sandbox)
    append_round(sandbox, 701)
    execute(sandbox)
    path = sandbox / "out" / loop.RESULTS
    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["actual_numbers"] = [1, 2, 3, 4, 5, 6, 7]
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="hash mismatch|record content/hash"):
        execute(sandbox)


def test_research_only_paths_and_governance(sandbox):
    result = execute(sandbox)
    assert result["production_promotion_eligible"] is False
    assert sorted(p.name for p in (sandbox / "out").iterdir()) == sorted(
        (loop.REGISTRATION, loop.STATE, loop.SUMMARY, loop.REPORT)
    )
    assert not any("model_champion" in p.name or "joint_set_v2_signal_oos" in p.name
                   for p in (sandbox / "out").iterdir())


def test_no_registration_after_first_target_already_observed(sandbox):
    append_round(sandbox, 700)
    append_round(sandbox, 701)
    with pytest.raises(ValueError, match="too late to register"):
        execute(sandbox)
