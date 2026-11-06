"""Strict prospective-only disjoint geometry registration and freezing tests."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

import disjoint_future_oos as oos
import balanced_uniform_portfolio as geometry

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "research" / "disjoint_future_oos"


def example(tmp_path):
    root = tmp_path / "independent_research_oos"
    root.mkdir()
    for name in ("registration.json", "freeze_0701.json"):
        shutil.copy2(REGISTRY / name, root / name)
    return root, oos.load(root / "registration.json")


def future_source(round_number=702, date="2026-11-06"):
    return {"sources": {"official_schedule": {
        "round": round_number, "date": date
    }}}


def now():
    return datetime(2026, 10, 31, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_real_registered_source_and_algorithm_lock():
    reg = oos.load(REGISTRY / "registration.json")
    oos.register_guard(reg, Path(oos.__file__).resolve(),
                       Path(geometry.__file__).resolve())
    freezes, grades = oos.archive_guard(REGISTRY, reg)
    # Historical frozen/graded targets are append-only, not fixed at the
    # initial 701 registration. A newly verified draw may add 702 safely.
    frozen_rounds = sorted(freezes)
    graded_rounds = sorted(grades)
    assert frozen_rounds == list(range(701, max(frozen_rounds) + 1))
    # A trusted draw can be graded even while the official *following*
    # schedule is unavailable: no retrospective next forecast is permitted.
    # The valid archive states are either all freezes graded, or exactly
    # one additional future-only freeze waiting for its verified outcome.
    assert graded_rounds == list(range(701, 701 + len(graded_rounds)))
    assert graded_rounds == frozen_rounds[:len(graded_rounds)]
    assert len(frozen_rounds) - len(graded_rounds) in (0, 1)
    if len(frozen_rounds) > len(graded_rounds):
        assert frozen_rounds[-1] == oos.START + len(graded_rounds)
    assert oos.summary(REGISTRY, reg)["trusted_draws"] == len(graded_rounds)
    assert len({n for t in freezes[701]["candidate_tickets"] for n in t}) == 35
    assert len(set(tuple(x) for x in freezes[701]["random_reference_tickets"])) == 5


def test_initial_freeze_precedes_unknown_outcome_and_uses_original_data():
    reg = oos.load(REGISTRY / "registration.json")
    freeze = oos.load(REGISTRY / "freeze_0701.json")
    assert freeze["verified_parent_round"] == 700
    assert freeze["registration_sha256"] == oos.digest(reg)
    assert freeze["parent_draw_csv_sha256"] == reg["registered_draw_csv_sha256"]
    assert freeze["draw_date"] == "2026-10-30"
    assert freeze["pre_outcome_freeze"]
    assert not freeze["promotion_authorized"]


def test_waits_without_new_draw_or_edits(tmp_path, monkeypatch):
    root, reg = example(tmp_path)
    monkeypatch.setattr(oos, "verified_latest",
                        lambda *args: (700, [], reg["registered_draw_csv_sha256"],
                                       future_source(701, "2026-10-30")))
    result = oos.advance(root, reg, Path("none"), Path("none"), now=now())
    assert result["status"] == "waiting_for_future_result"
    assert sorted(x.name for x in root.iterdir()) == [
        "freeze_0701.json", "registration.json"
    ]


def test_only_trusted_result_scores_and_freezes_new_target(tmp_path, monkeypatch):
    root, reg = example(tmp_path)
    monkeypatch.setattr(oos, "verified_latest", lambda *args: (
        701, [1, 3, 5, 7, 9, 11, 13], "a" * 64, future_source()
    ))
    report_file = root / "source.json"
    report_file.write_text(json.dumps(future_source()), encoding="utf-8")
    result = oos.advance(root, reg, Path("none"), report_file,
                         now=now())
    # The grade needs an actual source report file hash. It is never read from
    # target data when generating that target's prefrozen tickets.
    assert result["status"] == "trusted_graded"
    assert result["next_target"] == 702
    freezes, grades = oos.archive_guard(root, reg)
    assert sorted(freezes) == [701, 702]
    assert sorted(grades) == [701]
    assert grades[701]["freeze_sha256"] == oos.digest(freezes[701])
    assert freezes[702]["parent_draw_csv_sha256"] == "a" * 64
    assert oos.summary(root, reg)["trusted_draws"] == 1
    assert oos.summary(root, reg)["fixed_horizon_primary_mean_delta"] is None


def test_untrusted_source_does_not_grade(tmp_path, monkeypatch):
    root, reg = example(tmp_path)
    def no_trust(*args):
        raise RuntimeError("wait: result has not passed independent source verification")
    monkeypatch.setattr(oos, "verified_latest", no_trust)
    with pytest.raises(RuntimeError, match="independent source"):
        oos.advance(root, reg, Path("unused"), Path("unused"), now=now())
    assert not oos.grade_path(root, 701).exists()


def test_rejects_backfill_and_immutable_grade_changes(tmp_path, monkeypatch):
    root, reg = example(tmp_path)
    monkeypatch.setattr(oos, "verified_latest",
                        lambda *args: (702, [], "a" * 64, future_source(703)))
    with pytest.raises(RuntimeError, match="no backfill"):
        oos.advance(root, reg, Path("none"), Path("none"), now=now())
    assert not oos.grade_path(root, 701).exists()
    freeze = oos.load(oos.freeze_path(root, 701))
    freeze["candidate_tickets"][0][0] = 2
    oos.freeze_path(root, 701).write_text(json.dumps(freeze))
    with pytest.raises(ValueError, match="differs from deterministic"):
        oos.archive_guard(root, reg)


def test_schedule_cutoff_fail_closed():
    with pytest.raises(RuntimeError, match="cutoff"):
        oos.ensure_cutoff("2026-10-30", datetime(
            2026, 10, 30, 18, 0, tzinfo=ZoneInfo("Asia/Tokyo")
        ))
    oos.ensure_cutoff("2026-10-30", datetime(
        2026, 10, 25, 21, 0, tzinfo=ZoneInfo("Asia/Tokyo")
    ))


def test_prevent_unreviewed_algorithm_change():
    reg = oos.load(REGISTRY / "registration.json")
    changed = dict(reg, protocol_blob_sha1="0" * 40)
    with pytest.raises(RuntimeError, match="immutable implementation"):
        oos.register_guard(changed, Path(oos.__file__).resolve(),
                           Path(geometry.__file__).resolve())


def test_initial_next_freeze_not_retrospectively_generated(tmp_path, monkeypatch):
    root, reg = example(tmp_path)
    # A 701 result cannot be graded if the first 701 freeze file disappears.
    oos.freeze_path(root, 701).unlink()
    with pytest.raises(ValueError, match="no valid future prefrozen"):
        oos.advance(root, reg, Path("none"), Path("none"), now=now())


def test_random_control_is_distinct_and_deterministic():
    seed = 22411656
    a = oos.random_control(seed)
    assert a == oos.random_control(seed)
    assert len(a) == 5
    assert len(set(a)) == 5
    assert all(len(t) == 7 and len(set(t)) == 7 for t in a)


def test_no_existing_prod_paths_ever_modified(tmp_path, monkeypatch):
    root, reg = example(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(oos, "verified_latest", lambda *args: (
        700, [], reg["registered_draw_csv_sha256"], future_source(701, "2026-10-30")))
    oos.advance(root, reg, Path("none"), Path("none"), now=now())
    assert not Path("loto7_agent_output").exists()
    assert not Path("STATUS.md").exists()
    assert not Path("loto7.csv").exists()


def test_grading_is_legal_without_unsafe_next_freeze_and_can_resume(tmp_path, monkeypatch):
    # Reconstruct the *real, separately registered* 701/702 pre-outcome
    # freezes and the 701 grade in an isolated, disposable archive.
    # No recorded draw or canonical evidence is edited.
    root = tmp_path / "missing_official_schedule"
    root.mkdir()
    for name in ("registration.json", "freeze_0701.json",
                 "grade_0701.json", "freeze_0702.json"):
        shutil.copy2(REGISTRY / name, root / name)
    reg = oos.load(root / "registration.json")
    existing_freezes, existing_grades = oos.archive_guard(root, reg)
    assert sorted(existing_freezes) == [701, 702]
    assert sorted(existing_grades) == [701]

    actual_702 = [1, 5, 11, 14, 16, 30, 36]
    verified_data_sha = "c" * 64
    missing_schedule = {"sources": {"official_schedule": {
        "status": "not_parseable",
    }}}
    source_path = root / "synthetic_source.json"
    source_path.write_text(json.dumps(missing_schedule), encoding="utf-8")
    monkeypatch.setattr(oos, "verified_latest", lambda *args: (
        702, actual_702, verified_data_sha, missing_schedule
    ))
    status = oos.advance(root, reg, Path("unused"), source_path, now=now())
    assert status["status"] == "trusted_graded"
    assert status["target"] == 702
    assert status["next_freeze_status"] == "awaiting_verified_official_next_schedule"
    assert not oos.freeze_path(root, 703).exists()

    freezes, grades = oos.archive_guard(root, reg)
    assert sorted(freezes) == sorted(grades) == [701, 702]
    assert grades[702]["freeze_sha256"] == oos.digest(freezes[702])
    assert grades[702]["actual_main_numbers"] == actual_702

    # A repeated verified result must not append or overwrite the grade,
    # even while the following schedule remains unavailable.
    grade_bytes = oos.grade_path(root, 702).read_bytes()
    repeat = oos.advance(root, reg, Path("unused"), source_path, now=now())
    assert repeat["status"] == "awaiting_official_schedule"
    assert oos.grade_path(root, 702).read_bytes() == grade_bytes

    # Once an independently published schedule is available, ONLY the
    # next not-yet-observed round can be frozen (without rewriting grade 702).
    good_schedule = future_source(703, "2026-11-13")
    monkeypatch.setattr(oos, "verified_latest", lambda *args: (
        702, actual_702, verified_data_sha, good_schedule
    ))
    status = oos.advance(
        root, reg, Path("unused"), source_path,
        now=datetime(2026, 11, 7, 8, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    )
    assert status["status"] == "new_future_target_prefrozen"
    assert status["target"] == 703
    assert oos.grade_path(root, 702).read_bytes() == grade_bytes
    freezes, grades = oos.archive_guard(root, reg)
    assert sorted(freezes) == [701, 702, 703]
    assert sorted(grades) == [701, 702]
    assert freezes[703]["parent_draw_csv_sha256"] == verified_data_sha


def test_missing_prefreeze_still_refuses_retrospective_grade(tmp_path, monkeypatch):
    # Not permitting a next forecast does NOT authorize scoring an unseen
    # result when the preceding prediction was never frozen.
    root = tmp_path / "unfrozen_702"
    root.mkdir()
    for name in ("registration.json", "freeze_0701.json", "grade_0701.json"):
        shutil.copy2(REGISTRY / name, root / name)
    reg = oos.load(root / "registration.json")
    missing_schedule = {"sources": {"official_schedule": {
        "status": "not_parseable",
    }}}
    source_path = root / "synthetic_source.json"
    source_path.write_text(json.dumps(missing_schedule), encoding="utf-8")
    monkeypatch.setattr(oos, "verified_latest", lambda *args: (
        702, [1, 5, 11, 14, 16, 30, 36], "c" * 64, missing_schedule
    ))
    with pytest.raises(RuntimeError, match="not prefrozen"):
        oos.advance(root, reg, Path("unused"), source_path, now=now())
    assert not oos.grade_path(root, 702).exists()
