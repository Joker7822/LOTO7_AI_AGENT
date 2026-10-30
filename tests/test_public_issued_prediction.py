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


def test_latest_canonical_published_five_tickets_and_verified_result_gate(project):
    src, published = evidence(project)
    p, hashes = preview(project, src, published)
    target = int(published["target_round"].strip("第回"))
    assert p["version"] == VERSION
    assert p["status"] == "published"
    assert p["target_round"] == target
    assert p["source_base_round"] == target - 1
    assert target <= src["latest"]["round"] + 1
    assert p["result_status"] == ("independently_verified" if p["current_result"]
                                  else "awaiting_independently_verified_draw")
    assert [t["ticket"] for t in p["tickets"]] == [1, 2, 3, 4, 5]
    assert all(len(t["numbers"]) == len(set(t["numbers"])) == 7 for t in p["tickets"])
    if target == 701:
        # Actual, immutable first ticket of the original 701 Production freeze.
        assert p["tickets"][0]["numbers"] == [6, 16, 22, 23, 24, 25, 28]
    if p["current_result"] is not None:
        assert p["current_result"]["round"] == target
        assert len(p["current_result"]["tickets"]) == 5
    if p["latest_verified"] is not None:
        assert p["latest_verified"]["round"] == target - 1
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
        raw = [r for r in csv.DictReader(f)
               if r["target_round"] == pub["target_round"] and r["ticket"] == "1"]
    assert len(raw) == 1
    with (out / "prediction_corrections.csv").open("a", encoding="utf-8") as f:
        f.write("\n" + raw[0]["prediction_id"] + ",2099-01-01T00:00:00+09:00,invalidate,stale,abc,def\n")
    with pytest.raises(ValueError, match="count is not five"):
        preview(project, src, pub)


@pytest.mark.parametrize("column,wrong,err", [
    ("predicted_numbers", "01 01 02 03 04 05 06", "duplicate or unsorted"),
    ("model_version", "unregistered-shadow", "model version mismatch"),
    ("target_round", "第9999回", "count is not five"),
    ("prediction_created_at_jst", "2099-01-01T00:00:00+09:00", "not recorded before draw"),
])
def test_canonical_ledger_mismatch_blocks_public_projection(project, column, wrong, err):
    src, pub = evidence(project)
    path = project / "loto7_agent_output" / "predictions.csv"
    def tamper(rows):
        for r in rows:
            if r["target_round"] == pub["target_round"] and r["ticket"] == "1":
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


def test_current_published_forecast_requires_independent_result_evidence(project):
    src, pub = evidence(project)
    target = int(pub["target_round"].strip("第回"))
    if src["latest"]["round"] != target:
        pytest.skip("latest issued target has not yet been graded")
    p, _ = preview(project, src, pub)
    assert p["result_status"] == "independently_verified"
    assert p["current_result"]["round"] == target
    assert len(p["current_result"]["tickets"]) == 5

    src["verification"] = "degraded_single_result_source"
    degraded, _ = preview(project, src, pub)
    assert degraded["current_result"] is None
    assert degraded["result_status"] == "awaiting_independently_verified_draw"


def test_source_disagreement_never_creates_graded_draw(project):
    src, pub = evidence(project)
    target = int(pub["target_round"].strip("第回"))
    if src["latest"]["round"] != target:
        pytest.skip("latest issued target has not yet been graded")
    src["status"] = "ok"
    src["verification"] = "verified_two_result_sources"
    # Preserve the recorded verified actual; forge only the current claimed
    # source result. This must not create a false lottery grade.
    src["latest"]["main"] = [4, 5, 6, 7, 8, 9, 10]
    src["latest"]["bonus"] = [11, 12]
    with pytest.raises(ValueError, match="disagrees"):
        preview(project, src, pub)


def test_future_702_dashboard_never_displays_overlapping_issued_tickets():
    import production_ticket_geometry35 as geometry
    from public_issued_prediction import forecast_group
    tickets = geometry.portfolio_for_target(702)
    rows = [
        {"prediction_id": f"future-{i}", "target_round": "第702回",
         "base_round": "第701回", "ticket": str(i),
         "prediction_created_at_jst": "2026-11-06T15:00:00+09:00",
         "target_draw_date_estimate": "2026-11-06",
         "predicted_numbers": " ".join(f"{n:02d}" for n in numbers),
         "model_version": "baseline-test+" + geometry.VERSION}
        for i, numbers in enumerate(tickets, 1)
    ]
    assert len(forecast_group(rows, 702, required=True)) == 5
    bad = [dict(r) for r in rows]
    bad[1]["predicted_numbers"] = bad[0]["predicted_numbers"]
    with pytest.raises(ValueError, match="overlap"):
        forecast_group(bad, 702, required=True)
    bad = [dict(r) for r in rows]
    bad[2]["model_version"] = "champion_original"
    with pytest.raises(ValueError, match="policy"):
        forecast_group(bad, 702, required=True)


def test_frozen_701_remains_displayable_even_with_overlapping_numbers(project):
    src, state = evidence(project)
    if state["target_round"] != "第701回":
        pytest.skip("canonical file now tracks a later issued target")
    result, _ = preview(project, src, state)
    assert result["target_round"] == 701
    assert len(result["tickets"]) == 5
    assert len({n for r in result["tickets"] for n in r["numbers"]}) < 35
