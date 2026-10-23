"""Only already-published canonical Production tickets may be displayed."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from public_issued_prediction import VERSION, preview


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "readonly"
    out = root / "loto7_agent_output"
    out.mkdir(parents=True)
    shutil.copyfile("loto7.csv", root / "loto7.csv")
    for name in ("source_validation.json", "weekly_production_prediction_state.json",
                 "predictions.csv", "prediction_corrections.csv", "actual_results.csv"):
        shutil.copyfile(Path("loto7_agent_output") / name, out / name)
    return root



def append_actual(path, main, bonus):
    with path.open(encoding="utf-8-sig", newline="") as f:
        fieldnames=list(csv.DictReader(f).fieldnames)
    row={k:"" for k in fieldnames}
    row.update({"result_id":"synthetic", "recorded_at_jst":"2026-10-23T21:00:00+09:00",
                "round":"第700回", "draw_date":"2026-10-23",
                "main_numbers":main, "bonus_numbers":bonus,
                "source_verification":"verified_two_result_sources",
                "source_status":"ok", "source_report_sha256":"abc"})
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writerow(row)


def evidence(root):
    p = root / "loto7_agent_output"
    return (json.loads((p / "source_validation.json").read_text()),
            json.loads((p / "weekly_production_prediction_state.json").read_text()))


def overwrite_csv(path, fn):
    with path.open(encoding="utf-8-sig", newline="") as f:
        original = list(csv.DictReader(f))
    fn(original)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(original[0]))
        writer.writeheader()
        writer.writerows(original)


def test_actual_published_700_five_tickets_and_verified_699_backreference(project):
    src, published = evidence(project)
    p, hashes = preview(project, src, published)
    assert p["version"] == VERSION
    assert p["status"] == "published"
    assert p["target_round"] == 700
    assert p["source_base_round"] == 699
    assert p["result_status"] == "awaiting_independently_verified_draw"
    assert p["current_result"] is None
    assert [t["ticket"] for t in p["tickets"]] == [1, 2, 3, 4, 5]
    assert p["tickets"][0]["numbers"] == [6, 16, 22, 23, 24, 28, 36]
    assert all(len(t["numbers"]) == len(set(t["numbers"])) == 7 for t in p["tickets"])
    assert p["latest_verified"]["round"] == 699
    assert p["latest_verified"]["source_verification"] == "verified_two_result_sources"
    assert len(p["latest_verified"]["tickets"]) == 5
    assert p["accuracy_claim"] is False
    assert p["no_future_oos_vectors"] is True
    assert set(hashes) == {"prediction_ledger", "prediction_corrections", "production_actuals"}


def test_unpublished_state_never_exposes_even_existing_ledger_tickets(project):
    src, pub = evidence(project)
    pub["published"] = False
    p, hashes = preview(project, src, pub)
    assert p["status"] == "not_published"
    assert p["tickets"] == []
    assert p["latest_verified"] is None
    assert hashes == {}


def test_forbid_all_invalidated_current_tickets(project):
    src, pub = evidence(project)
    out = project / "loto7_agent_output"
    active = preview(project, src, pub)[0]["tickets"]
    assert len(active) == 5
    with (out / "predictions.csv").open(encoding="utf-8-sig", newline="") as f:
        raw = [r for r in csv.DictReader(f) if r["target_round"] == "第700回" and r["ticket"] == "1"]
    with (out / "prediction_corrections.csv").open("a", encoding="utf-8") as f:
        f.write("\n" + raw[0]["prediction_id"] + ",2026-10-23T17:00:00+09:00,invalidate,stale,abc,def\n")
    with pytest.raises(ValueError, match="count is not five"):
        preview(project, src, pub)


@pytest.mark.parametrize("column,wrong,err", [
    ("predicted_numbers", "01 01 02 03 04 05 06", "duplicate or unsorted"),
    ("model_version", "unregistered-shadow", "model version mismatch"),
    ("target_round", "第701回", "count is not five"),
    ("prediction_created_at_jst", "2026-10-23T21:01:00+09:00", "not recorded before draw"),
])
def test_canonical_ledger_mismatch_blocks_public_projection(project, column, wrong, err):
    src, pub = evidence(project)
    path = project / "loto7_agent_output" / "predictions.csv"
    def tamper(rows):
        for r in rows:
            if r["target_round"] == "第700回" and r["ticket"] == "1":
                r[column] = wrong
                break
    overwrite_csv(path, tamper)
    with pytest.raises(ValueError, match=err):
        preview(project, src, pub)


def test_stale_source_for_current_new_forecast_is_blocked(project):
    src, pub = evidence(project)
    pub["data_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="another source snapshot"):
        preview(project, src, pub)


def test_older_published_forecast_can_be_graded_only_with_two_source_evidence(project):
    src, pub = evidence(project)
    src["latest"] = dict(src["latest"], round=700, date="2026-10-23",
                         main=[1, 2, 3, 4, 5, 6, 7], bonus=[8, 9])
    src["status"] = "ok"
    src["verification"] = "verified_two_result_sources"
    path = project / "loto7_agent_output" / "actual_results.csv"
    append_actual(path, "01 02 03 04 05 06 07", "08 09")
    p, _ = preview(project, src, pub)
    assert p["result_status"] == "independently_verified"
    assert p["current_result"]["round"] == 700
    assert p["current_result"]["tickets"][0]["main_hits"] == 1
    assert p["current_result"]["tickets"][0]["bonus_hits"] == 0

    src["verification"] = "degraded_single_result_source"
    degraded, _ = preview(project, src, pub)
    assert degraded["current_result"] is None
    assert degraded["result_status"] == "awaiting_independently_verified_draw"


def test_source_disagreement_never_creates_graded_draw(project):
    src, pub = evidence(project)
    src["latest"]["round"] = 700
    src["status"] = "ok"
    src["verification"] = "verified_two_result_sources"
    src["latest"]["main"] = [1, 2, 3, 4, 5, 6, 7]
    src["latest"]["bonus"] = [8, 9]
    path = project / "loto7_agent_output" / "actual_results.csv"
    append_actual(path, "01 02 03 04 05 06 08", "07 09")
    with pytest.raises(ValueError, match="disagrees"):
        preview(project, src, pub)
