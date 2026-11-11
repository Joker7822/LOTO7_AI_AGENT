"""No-overwrite evidence and mutable-view tests for stable v3 research replay."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

import online_v3_replay_runtime as runtime


def dummy_frozen():
    return {
        "prefix_sha256": "a" * 64,
        "top7": [1, 2, 3, 4, 5, 6, 7],
        "drift_guard": False,
        "probabilities": [0.18, 0.19, 0.20],
        "expert_vectors": [[0.18, 0.19, 0.20]],
        "rate_expert_weights": [[0.4, 0.6]],
        "temperature_weights": [0.5, 0.5],
        "prior_verified_scores": 0,
        "e_process_values_before": [],
    }


def test_exact_and_tiny_float_replay_preserve_immutable_frozen_numbers():
    frozen = dummy_frozen()
    exact = copy.deepcopy(frozen)
    assert runtime.compare_registered_forecast(frozen, exact) == (0, 0.0)

    rounded = copy.deepcopy(frozen)
    rounded["probabilities"][0] += 1e-14
    rounded["expert_vectors"][0][1] -= 1e-14
    changes, delta = runtime.compare_registered_forecast(frozen, rounded)
    assert changes == 2
    assert 0 < delta < runtime.ABS_REPLAY_TOL

    orig = lambda *args: copy.deepcopy(rounded)
    old_event = {"kind": "freeze", "target_round": 703, "prediction": frozen}
    adapter = runtime.replay_adapter([old_event], orig)
    original = copy.deepcopy(frozen)
    result = adapter(np.zeros((702, 37), dtype=np.int64),
                     None, None, None, None)
    assert result == original
    assert frozen == original


def test_material_forecast_changes_are_rejected_not_hidden():
    frozen = dummy_frozen()
    for change in ("probability", "top7", "prefix", "flag", "schema"):
        current = copy.deepcopy(frozen)
        if change == "probability":
            current["probabilities"][0] += 0.001
        elif change == "top7":
            current["top7"][0] = 8
        elif change == "prefix":
            current["prefix_sha256"] = "b" * 64
        elif change == "flag":
            current["drift_guard"] = True
        elif change == "schema":
            current["new_malicious_field"] = 1
        with pytest.raises(ValueError, match="MATERIAL replay change"):
            runtime.compare_registered_forecast(frozen, current)


def test_adapter_computes_unfrozen_future_target_from_current_model():
    frozen = dummy_frozen()
    latest = copy.deepcopy(frozen)
    latest["top7"] = [1, 2, 3, 4, 5, 6, 37]
    old_event = {"kind": "freeze", "target_round": 703, "prediction": frozen}
    adapter = runtime.replay_adapter([old_event], lambda *args: latest)
    actual = adapter(np.zeros((703, 37), dtype=np.int64),
                     None, None, None, None)
    assert actual == latest
    assert actual != frozen


def fake_state(sha="b" * 64, top7=None, p=0.189):
    return {
        "events": [{
            "kind": "freeze", "target_round": 703,
            "scheduled_draw_date": "2026-11-13",
            "event_sha256": sha,
            "prediction": {
                "top7": top7 or [1, 6, 16, 22, 23, 24, 36],
                "probabilities": [p] * 37,
                "prefix_sha256": "a" * 64,
            }
        }],
    }


def test_current_view_is_overwritten_only_on_change_with_revision_history(
        tmp_path: Path, monkeypatch):
    monkeypatch.setattr(runtime, "read_csv_flexible", lambda _: None)
    monkeypatch.setattr(runtime, "make_history",
                        lambda _: (np.zeros((702, 37), dtype=np.int8), None))
    now = datetime(2026, 11, 11, 22, 30,
                   tzinfo=timezone(timedelta(hours=9)))
    original_freeze = fake_state()
    first = runtime.refresh_latest_view(tmp_path, original_freeze, now, None)
    assert first["preview_status"] == "created"
    view_path = tmp_path / runtime.VIEW
    old_bytes = view_path.read_bytes()
    frozen_bytes = json.dumps(original_freeze, sort_keys=True)
    assert json.loads(old_bytes)["revision"] == 1

    same = runtime.refresh_latest_view(tmp_path, original_freeze, now, None)
    assert same["preview_status"] == "unchanged"
    assert view_path.read_bytes() == old_bytes

    changed = fake_state("c" * 64, [2, 6, 16, 22, 23, 24, 36], p=0.188)
    second = runtime.refresh_latest_view(
        tmp_path, changed, now + timedelta(minutes=2), None)
    assert second["preview_status"] == "overwritten"
    assert second["revision"] == 2
    new_view = json.loads(view_path.read_text(encoding="utf-8"))
    old_rev = json.loads((tmp_path / runtime.REVISIONS /
                          "revision_000001.json").read_text(encoding="utf-8"))
    assert old_rev["revision"] == 1
    assert new_view["revision"] == 2
    assert new_view["identity"]["top7"] == [2, 6, 16, 22, 23, 24, 36]
    assert new_view["previous_revision_sha256"] == runtime.stable_digest(old_rev)
    assert (tmp_path / runtime.REVISIONS /
            "revision_000002.json").is_file()
    assert json.dumps(original_freeze, sort_keys=True) == frozen_bytes


def test_view_fails_closed_on_tampered_revision_or_after_draw(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "read_csv_flexible", lambda _: None)
    monkeypatch.setattr(runtime, "make_history",
                        lambda _: (np.zeros((702, 37), dtype=np.int8), None))
    now = datetime(2026, 11, 11, 22, 30,
                   tzinfo=timezone(timedelta(hours=9)))
    state = fake_state()
    runtime.refresh_latest_view(tmp_path, state, now, None)
    archive = tmp_path / runtime.REVISIONS / "revision_000001.json"
    original_archive = archive.read_bytes()
    data = json.loads(original_archive)
    data["identity"]["top7"][0] = 37
    archive.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match archival revision"):
        runtime.refresh_latest_view(tmp_path, state, now, None)
    archive.write_bytes(original_archive)

    # The presentation view MUST expire on its scheduled draw date, but
    # original SHA-locked predictions and historical revision 1 stay intact.
    after = runtime.refresh_latest_view(
        tmp_path, state, datetime(2026, 11, 13, 18, 0,
                                 tzinfo=timezone(timedelta(hours=9))), None)
    assert after["preview_status"] == "overwritten"
    assert after["view_status"] == "expired_on_or_after_draw_day"
    assert after["revision"] == 2
    new_view = json.loads((tmp_path / runtime.VIEW).read_text(encoding="utf-8"))
    assert new_view["identity"]["view_status"] == "expired_on_or_after_draw_day"
    assert new_view["identity"]["valid_before_jst_date"] == "2026-11-13"
    assert new_view["identity"]["frozen_event_sha256"] == state["events"][0]["event_sha256"]
    assert archive.read_bytes() == original_archive
    assert (tmp_path / runtime.REVISIONS / "revision_000002.json").is_file()
    repeat = runtime.refresh_latest_view(
        tmp_path, state, datetime(2026, 11, 13, 20, 0,
                                 tzinfo=timezone(timedelta(hours=9))), None)
    assert repeat["preview_status"] == "unchanged_expired"
    assert repeat["revision"] == 2
