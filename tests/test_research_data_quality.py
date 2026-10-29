"""Source-integrity checks and regeneration are derived-only and reproducible."""
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone

import research_data_quality as quality

JST = timezone(timedelta(hours=9))
FRIDAY_BEFORE = datetime(2026, 10, 30, 7, 0, tzinfo=JST)
FRIDAY_AFTER = datetime(2026, 10, 30, 21, 0, tzinfo=JST)
HEADER = "抽せん日,本数字,ボーナス数字,回別\n"
ROW = "2026-10-23,02 03 08 12 21 25 26,13 34,第700回\n"


def project(tmp_path):
    out = tmp_path / "loto7_agent_output"
    out.mkdir()
    data = (HEADER + ROW).encode("utf-8")
    (tmp_path / "loto7.csv").write_bytes(data)
    source = {
        "status": "ok",
        "verification": "verified_two_result_sources",
        "latest": {
            "round": 700, "date": "2026-10-23",
            "main": [2, 3, 8, 12, 21, 25, 26], "bonus": [13, 34],
        },
        "verification_provenance": {"draw_csv_sha256": hashlib.sha256(data).hexdigest()},
        "sources": {"official_schedule": {"round": 701, "date": "2026-10-30"}},
    }
    (out / "source_validation.json").write_text(json.dumps(source), encoding="utf-8")
    return tmp_path


def test_no_false_friday_morning_staleness(tmp_path):
    root = project(tmp_path)
    report = quality.audit(root, now=FRIDAY_BEFORE)
    assert report["status"] == "watch"  # fixture deliberately contains gaps 1..699
    assert "DRAW_UPDATE_OVERDUE" not in {i["code"] for i in report["issues"]}
    after = quality.audit(root, now=FRIDAY_AFTER)
    assert "DRAW_UPDATE_OVERDUE" in {i["code"] for i in after["issues"]}


def test_invalid_history_fails_closed_without_rewriting_source(tmp_path):
    root = project(tmp_path)
    csv_path = root / "loto7.csv"
    csv_path.write_text(HEADER + ROW + ROW, encoding="utf-8")
    before = csv_path.read_bytes()
    report = quality.run(root, now=FRIDAY_BEFORE)
    assert report["status"] == "block"
    codes = {item["code"] for item in report["issues"]}
    assert {"DRAW_DATA_INVALID", "DRAW_SHA_MISMATCH"} <= codes
    assert csv_path.read_bytes() == before


def test_unverified_receipt_does_not_masquerade_as_trusted(tmp_path):
    root = project(tmp_path)
    path = root / "loto7_agent_output" / "source_validation.json"
    source = json.loads(path.read_text())
    source["verification"] = "degraded_single_result_source"
    path.write_text(json.dumps(source), encoding="utf-8")
    report = quality.audit(root, now=FRIDAY_BEFORE)
    assert "INDEPENDENT_SOURCE_NOT_VERIFIED" in {x["code"] for x in report["issues"]}
    assert report["status"] == "block"


def test_derived_reports_recover_idempotently_and_source_stays_unchanged(tmp_path):
    root = project(tmp_path)
    source_path = root / "loto7_agent_output" / "source_validation.json"
    unchanged = (root / "loto7.csv").read_bytes(), source_path.read_bytes()
    first = quality.run(root, now=FRIDAY_BEFORE)
    assert set(first["derived_reports_regenerated"]) == {
        quality.JSON_REPORT, quality.MD_REPORT
    }
    second = quality.run(root, now=FRIDAY_BEFORE)
    assert second["derived_reports_regenerated"] == []
    path = root / "loto7_agent_output" / quality.MD_REPORT
    path.write_text("tampered", encoding="utf-8")
    recovered = quality.run(root, now=FRIDAY_BEFORE)
    assert recovered["derived_reports_regenerated"] == [quality.MD_REPORT]
    assert "tampered" not in path.read_text()
    assert ((root / "loto7.csv").read_bytes(), source_path.read_bytes()) == unchanged


def test_official_schedule_adjusts_deadline_without_creating_outcome(tmp_path):
    root = project(tmp_path)
    path = root / "loto7_agent_output" / "source_validation.json"
    source = json.loads(path.read_text())
    source["sources"]["official_schedule"]["date"] = "2026-11-06"
    path.write_text(json.dumps(source), encoding="utf-8")
    # The published schedule does not create a draw or authorize a grade.
    assert quality.next_result_deadline(
        datetime(2026, 10, 23).date(), source
    ) == datetime(2026, 11, 6, 20, 30, tzinfo=JST)
    assert "DRAW_UPDATE_OVERDUE" not in {
        item["code"] for item in quality.audit(root, now=FRIDAY_AFTER)["issues"]
    }
