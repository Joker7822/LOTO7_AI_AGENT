"""Future-only first-prize evidence; never fabricate a backtest freeze."""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import first_prize_research as fp
import production_disjoint35_policy as geometry

JST = timezone(timedelta(hours=9))
ISSUANCE = datetime(2026, 11, 6, 14, 0, tzinfo=JST)


def csvfile(path, columns, data):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)


def fixture(tmp_path):
    source = tmp_path / "loto7.csv"
    out = tmp_path / "out"
    root = tmp_path / "prospective"
    out.mkdir()
    first = datetime(2026, 10, 30) - timedelta(days=7 * 700)
    # Realistic sequential test source: valid but synthetic and non-predictive.
    records = []
    for i in range(701):
        main = sorted(((i * 13 + j * 5) % 37) + 1 for j in range(7))
        remain = [n for n in range(1, 38) if n not in main]
        records.append({"抽せん日": (first + timedelta(days=7 * i)).date().isoformat(),
                        "本数字": " ".join(f"{n:02d}" for n in main),
                        "ボーナス数字": " ".join(f"{n:02d}" for n in remain[:2]),
                        "回別": f"第{i + 1}回"})
    csvfile(source, ["抽せん日", "本数字", "ボーナス数字", "回別"], records)
    sha = fp.sha_bytes(source.read_bytes())
    last = records[-1]
    report = {
        "status": "ok", "verification": fp.TRUST,
        "latest": {"round": 701, "date": last["抽せん日"],
                   "main": fp.numbers(last["本数字"], 7),
                   "bonus": fp.numbers(last["ボーナス数字"], 2)},
        "verification_provenance": {"draw_csv_sha256": sha},
        "checked_at_jst": ISSUANCE.isoformat(),
    }
    source_report = out / "source_validation.json"
    source_report.write_text(json.dumps(report), encoding="utf-8")
    target_date = (first + timedelta(days=7 * 701)).date().isoformat()
    issued = [{
        "prediction_id": f"issued-702-{i}",
        "prediction_created_at_jst": ISSUANCE.isoformat(),
        "base_round": "第701回",
        "target_round": "第702回",
        "target_draw_date_estimate": target_date,
        "ticket": str(i),
        "predicted_numbers": " ".join(f"{n:02d}" for n in ticket),
        "model_version": "baseline+" + geometry.VERSION,
        "data_sha256": sha,
    } for i, ticket in enumerate([
        tuple(range(k * 7 + 1, k * 7 + 8)) for k in range(5)
    ], 1)]
    csvfile(out / "predictions.csv", list(issued[0]), issued)
    csvfile(out / "prediction_corrections.csv", ["prediction_id", "action"], [])
    state = {
        "published": True, "target_round": "第702回",
        "reason": "frozen_to_canonical_prediction_ledger",
        "ticket_policy": geometry.VERSION,
        "published_at_jst": ISSUANCE.isoformat(),
        "model_version": "baseline+" + geometry.VERSION,
        "data_sha256": sha,
    }
    (out / "weekly_production_prediction_state.json").write_text(
        json.dumps(state), encoding="utf-8")
    return source, source_report, out, root


def test_first_prize_probability_is_exact_no_free_lunch():
    assert fp.DENOMINATOR == 10_295_472
    assert fp.PROSPECTIVE_FIRST_PRIZE_PROB == 5 / fp.DENOMINATOR


def test_prefreeze_is_future_only_deterministic_and_append_only(tmp_path):
    source, report, out, root = fixture(tmp_path)
    result = fp.freeze(source, report, out, root, now=ISSUANCE)
    assert result["status"] == "prefrozen"
    frozen = fp.load_json(fp.freeze_file(root, 702))
    assert frozen["base_round"] == 701
    assert len(frozen["production_tickets"]) == len(frozen["random_control_tickets"]) == 5
    assert len({n for ticket in frozen["random_control_tickets"] for n in ticket}) == 35
    original = fp.freeze_file(root, 702).read_bytes()
    assert fp.freeze(source, report, out, root, now=ISSUANCE)["status"] == "already_prefrozen"
    assert fp.freeze_file(root, 702).read_bytes() == original
    assert fp.summary(root, out)["graded_targets"] == 0


def test_never_freeze_after_draw_even_if_state_says_published(tmp_path):
    source, report, out, root = fixture(tmp_path)
    late = ISSUANCE.replace(hour=19)
    with pytest.raises(ValueError, match="retrospectively"):
        fp.freeze(source, report, out, root, now=late)
    assert not root.exists()


def test_never_create_prefreeze_for_701_or_past_targets(tmp_path):
    source, report, out, root = fixture(tmp_path)
    path = out / "weekly_production_prediction_state.json"
    obj = json.loads(path.read_text())
    obj["target_round"] = "第701回"
    path.write_text(json.dumps(obj), encoding="utf-8")
    assert fp.freeze(source, report, out, root, now=ISSUANCE)["status"] == "historical_no_backfill"
    assert not root.exists()


def test_republish_without_original_prefreeze_cannot_backfill(tmp_path):
    source, report, out, root = fixture(tmp_path)
    path = out / "weekly_production_prediction_state.json"
    obj = json.loads(path.read_text())
    obj["reason"] = "republished_frozen_ledger_prediction"
    path.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError, match="republished"):
        fp.freeze(source, report, out, root, now=ISSUANCE)


def test_changed_issued_numbers_or_policy_fails_archive_audit(tmp_path):
    source, report, out, root = fixture(tmp_path)
    fp.freeze(source, report, out, root, now=ISSUANCE)
    before = (out / "predictions.csv").read_bytes()
    tickets = fp.rows(out / "predictions.csv")
    tickets[1]["predicted_numbers"] = tickets[0]["predicted_numbers"]
    csvfile(out / "predictions.csv", list(tickets[0]), tickets)
    with pytest.raises(ValueError):
        fp.validate_archive(root, out)
    (out / "predictions.csv").write_bytes(before)
    freeze_path = fp.freeze_file(root, 702)
    frozen = fp.load_json(freeze_path)
    frozen["random_control_tickets"][0] = list(range(1, 8))
    freeze_path.write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(ValueError, match="control"):
        fp.validate_archive(root, out)


def test_grade_needs_trusted_exact_target_and_is_add_only(tmp_path):
    source, report, out, root = fixture(tmp_path)
    fp.freeze(source, report, out, root, now=ISSUANCE)
    assert fp.grade(source, report, out, root)["status"] == "awaiting_verified_result"
    history = fp.rows(source)
    target_date = fp.load_json(fp.freeze_file(root, 702))["target_draw_date"]
    history.append({"抽せん日": target_date, "本数字": "01 02 03 04 05 06 07",
                    "ボーナス数字": "08 09", "回別": "第702回"})
    csvfile(source, list(history[0]), history)
    # Deliberately stale independent source; it must not grade.
    with pytest.raises(ValueError, match="verified"):
        fp.grade(source, report, out, root)
    assert not fp.grade_file(root, 702).exists()
    obj = fp.load_json(report)
    obj["latest"] = {"round": 702, "date": target_date,
                     "main": [1, 2, 3, 4, 5, 6, 7], "bonus": [8, 9]}
    obj["verification_provenance"]["draw_csv_sha256"] = fp.sha_bytes(source.read_bytes())
    report.write_text(json.dumps(obj), encoding="utf-8")
    grade = fp.grade(source, report, out, root)
    assert grade["status"] == "new_verified_grade"
    assert grade["production_first_prizes"] == 1
    frozen_grade = fp.grade_file(root, 702).read_bytes()
    assert fp.grade(source, report, out, root)["status"] == "all_frozen_targets_graded"
    assert fp.grade_file(root, 702).read_bytes() == frozen_grade
    assert fp.summary(root, out)["production_first_prize_count"] == 1


def test_bias_audit_is_exploratory_and_does_not_touch_production(tmp_path):
    source, report, out, root = fixture(tmp_path)
    original = {p.name: p.read_bytes() for p in out.iterdir()}
    stats = fp.probability_audit(source, report, simulations=128)
    assert stats["draw_count"] == 701
    assert len(stats["all_number_counts"]) == 37
    assert sum(stats["all_number_counts"].values()) == 701 * 7
    assert 0 < stats["max_37_familywise_p_estimate"] <= 1
    assert stats["repeat_inspection_not_time_adjusted"] is True
    assert {p.name: p.read_bytes() for p in out.iterdir()} == original
    assert not root.exists()


def test_invalid_source_prefix_never_passes_bias_or_freeze(tmp_path):
    source, report, out, root = fixture(tmp_path)
    obj = fp.load_json(report)
    obj["verification"] = "degraded_single_result_source"
    report.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError, match="verified"):
        fp.probability_audit(source, report, simulations=128)
    with pytest.raises(ValueError, match="verified"):
        fp.freeze(source, report, out, root, now=ISSUANCE)
    assert not root.exists()


def test_late_ungraded_702_never_blocks_new_703_evidence(tmp_path, monkeypatch):
    source, report, out, root = fixture(tmp_path)
    fp.freeze(source, report, out, root, now=ISSUANCE)
    first = fp.load_json(fp.freeze_file(root, 702))
    second = {**first, "target_round": 703,
              "target_draw_date": "2026-11-13"}
    monkeypatch.setattr(fp, "validate_archive", lambda *_: {702: first, 703: second})
    fake_draw = {"回別": "第703回", "抽せん日": "2026-11-13",
                 "本数字": "01 03 05 07 09 11 13"}
    monkeypatch.setattr(fp, "checked_source",
                        lambda *_: ([fake_draw], {}, "f" * 64))
    result = fp.grade(source, report, out, root)
    assert result["status"] == "new_verified_grade"
    assert result["target_round"] == 703
    assert result["missed_past_targets"] == [702]
    assert fp.grade_file(root, 703).exists()
    assert not fp.grade_file(root, 702).exists()


def test_primary_and_fallback_commit_freeze_with_original_issued_production():
    for filename in ("weekly_production_publisher.yml", "weekly_production_fallback.yml"):
        text = Path(".github/workflows", filename).read_text(encoding="utf-8")
        freeze = text.index("python first_prize_research.py --mode freeze")
        publication_gate = text.index("python production_ticket_geometry35.py --verify-canonical")
        commit = text.index('git commit -m "chore:')
        assert publication_gate < freeze < commit
        assert "research/first_prize_oos" in text
        assert "Refusing non-additive first-prize archive change" in text
        assert 'date +%H%M)" -lt 1800' in text
        assert text.count("      - name: Commit Production checkpoint") == 1
        assert text.count("      - name: Validate Sakura sync payload") == 1
