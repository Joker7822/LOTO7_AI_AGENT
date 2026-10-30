"""Production-only geometry boundary, immutability and append-ledger checks."""
import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

import audit_ledger as ledger
import balanced_uniform_portfolio as disjoint
import production_ticket_geometry35 as geometry
import weekly_production_prediction as weekly

JST = timezone(timedelta(hours=9))


@pytest.mark.parametrize("target", [702, 703, 704, 1000])
def test_new_production_geometry_is_exactly_35_numbers(target):
    tickets = geometry.portfolio_for_target(target)
    assert tickets == geometry.portfolio_for_target(target)
    disjoint.validate_portfolio(tickets)
    assert len({n for ticket in tickets for n in ticket}) == 35
    assert len(tickets) == 5


@pytest.mark.parametrize("target", [1, 700, 701, -1, 702.5])
def test_never_retroactively_change_first_frozen_target(target):
    with pytest.raises(ValueError):
        geometry.portfolio_for_target(target)


def test_render_is_parseable_as_canonical_candidate_tickets():
    tickets = geometry.portfolio_for_target(702)
    text = geometry.render_ticket_csv(tickets)
    rows = list(csv.DictReader(text.lstrip("\ufeff").splitlines()))
    assert len(rows) == 5
    assert [int(row["ticket"]) for row in rows] == [1, 2, 3, 4, 5]
    for row, ticket in zip(rows, tickets):
        assert [int(n) for n in row["numbers"].split()] == list(ticket)
        assert int(row["sum"]) == sum(ticket)
        assert int(row["odd_count"]) == sum(n % 2 for n in ticket)


@pytest.mark.parametrize("d,h,m,allowed", [
    ("2026-10-25", 23, 35, False),  # Sunday
    ("2026-10-30", 12, 59, False),
    ("2026-10-30", 13, 0, True),
    ("2026-10-30", 19, 59, True),
    ("2026-10-30", 20, 0, False),
    ("2026-10-31", 14, 0, False),
])
def test_cannot_publish_outside_original_friday_gate(d, h, m, allowed):
    at = datetime.fromisoformat(d).replace(
        hour=h, minute=m, tzinfo=JST
    )
    if allowed:
        geometry.production_window_guard(at)
    else:
        with pytest.raises(RuntimeError, match="outside Friday"):
            geometry.production_window_guard(at)


def test_trust_guard_requires_report_matching_csv(tmp_path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text("sample", encoding="utf-8")
    src = tmp_path / "source.json"
    src.write_text(json.dumps({"verification_provenance":
                               {"draw_csv_sha256": "0" * 64}}))
    monkeypatch.setattr(geometry, "validate_trusted_source",
                        lambda *args: {"trusted": True, "round": 701})
    with pytest.raises(RuntimeError, match="stale CSV fingerprint"):
        geometry.verify_source(csv_path, src, 701)
    monkeypatch.setattr(geometry, "validate_trusted_source",
                        lambda *args: {"trusted": False, "round": 701})
    with pytest.raises(RuntimeError, match="two-source"):
        geometry.verify_source(csv_path, src, 701)
    monkeypatch.setattr(geometry, "validate_trusted_source",
                        lambda *args: {"trusted": True, "round": 700})
    with pytest.raises(RuntimeError, match="two-source"):
        geometry.verify_source(csv_path, src, 701)


def make_synthetic_csv(path: Path, rounds: int):
    # No historical results beyond each synthetic target influence its
    # frozen tickets; this tests integration/metadata only, not forecast skill.
    start = datetime(2013, 4, 5, tzinfo=JST)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["抽せん日", "本数字", "ボーナス数字", "回別"])
        for idx in range(rounds):
            day = start + timedelta(days=7 * idx)
            numbers = sorted((idx * 13 + k * 5) % 37 + 1 for k in range(7))
            bonus = [n for n in range(1, 38) if n not in numbers][:2]
            w.writerow([day.date().isoformat(),
                        " ".join(f"{n:02d}" for n in numbers),
                        " ".join(f"{n:02d}" for n in bonus),
                        f"第{idx+1}回"])


def test_production_702_appends_once_and_republishes_without_replacing(tmp_path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    make_synthetic_csv(csv_path, 701)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    source = out_dir / "source_validation.json"
    source.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(geometry, "verify_source",
                        lambda *args: {"trusted": True, "round": 701})
    monkeypatch.setattr(geometry, "production_window_guard", lambda *_: None)
    result = weekly.publish(
        csv_path=csv_path, out_dir=out_dir,
        champion_file=tmp_path / "missing_champion.json",
        research_state=tmp_path / "missing_research.json",
    )
    assert result["published"]
    assert result["reason"] == "frozen_to_canonical_prediction_ledger"
    assert result["ticket_policy"] == geometry.VERSION
    assert geometry.verify_canonical_publication(out_dir) == {
        "target_round": 702, "status": "disjoint35_pass",
        "covered_distinct_numbers": 35, "checked_active_tickets": 5,
        "production_changed": False,
    }
    rows = ledger.read_csv(out_dir / "predictions.csv")
    assert len(rows) == 5
    assert all(geometry.VERSION in r["model_version"] for r in rows)
    tickets = [tuple(int(x) for x in row["predicted_numbers"].split())
               for row in rows]
    disjoint.validate_portfolio(tickets)
    first_state = json.loads((out_dir / "agent_state.json").read_text())
    assert first_state["production_ticket_policy_version"] == geometry.VERSION
    assert first_state["first_prize_odds_unchanged"] is True
    assert first_state["signal_champion_version"].startswith("baseline-")
    first_issued = (out_dir / "predictions.csv").read_bytes()

    # Even if somebody changes the editable candidate view, republish must
    # only render the already-frozen canonical prediction ledger.
    (out_dir / "candidate_tickets.csv").write_text("tampered", encoding="utf-8")
    followup = weekly.publish(
        csv_path=csv_path, out_dir=out_dir,
        champion_file=tmp_path / "missing_champion.json",
        research_state=tmp_path / "missing_research.json",
    )
    assert followup["reason"] == "republished_frozen_ledger_prediction"
    assert (out_dir / "predictions.csv").read_bytes() == first_issued
    assert len(ledger.read_csv(out_dir / "predictions.csv")) == 5
    assert geometry.VERSION in (out_dir / "latest_prediction.txt").read_text()


def test_production_change_never_prepares_701(tmp_path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text("sample")
    out_dir = tmp_path / "out"
    with pytest.raises(RuntimeError, match="round 701 and earlier"):
        geometry.prepare_new_production_outputs(
            csv_path=csv_path, out_dir=out_dir,
            champion_version="baseline", data_sha="x",
            latest_round=700, target_round=701,
            latest_draw_date="2026-10-23", git_sha="test",
            source_path=tmp_path / "source.json",
            now=datetime(2026, 10, 30, 13, 0, tzinfo=JST),
        )
    assert not out_dir.exists()


def test_weekly_existing_frozen_target_returns_before_new_geometry(tmp_path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    make_synthetic_csv(csv_path, 701)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    monkeypatch.setattr(geometry, "prepare_new_production_outputs",
                        lambda **kwargs: (_ for _ in ()).throw(
                            RuntimeError("should not run for already frozen target")))
    # A successful first issuance under an injected prefreeze is not
    # required for this logic: _frozen_target_rows controls the early exit.
    monkeypatch.setattr(weekly, "_frozen_target_rows", lambda *_: [
        {"ticket": str(i), "model_version": "original"}
        for i in range(1, 6)
    ])
    monkeypatch.setattr(ledger, "append_prediction_invalidations",
                        lambda *args: 0)
    monkeypatch.setattr(ledger, "render_latest", lambda *args: "frozen ledger\n")
    result = weekly.publish(
        csv_path=csv_path, out_dir=out_dir,
        champion_file=tmp_path / "none.json",
        research_state=tmp_path / "none2.json",
    )
    assert result["reason"] == "republished_frozen_ledger_prediction"
    assert not (out_dir / "candidate_tickets.csv").exists()


def issued_rows(target=702):
    tickets = geometry.portfolio_for_target(target)
    return [
        {"ticket": str(i), "predicted_numbers": " ".join(f"{n:02d}" for n in numbers),
         "model_version": "baseline-test+" + geometry.VERSION}
        for i, numbers in enumerate(tickets, 1)
    ]


def test_shared_post_migration_ledger_validator_rejects_all_overlaps():
    rows = issued_rows()
    geometry.validate_issued_rows(rows, 702)
    assert len({n for r in rows for n in r["predicted_numbers"].split()}) == 35

    altered = [dict(x) for x in rows]
    nums = altered[1]["predicted_numbers"].split()
    nums[0] = altered[0]["predicted_numbers"].split()[0]
    altered[1]["predicted_numbers"] = " ".join(sorted(nums, key=int))
    with pytest.raises(ValueError, match="overlap|disjoint|tickets"):
        geometry.validate_issued_rows(altered, 702)


@pytest.mark.parametrize("change", ["drop", "position", "policy", "duplicate", "out_of_range"])
def test_shared_validator_refuses_invalid_702_production(change):
    rows = issued_rows()
    if change == "drop":
        rows.pop()
    elif change == "position":
        rows[1]["ticket"] = "1"
    elif change == "policy":
        rows[0]["model_version"] = "baseline-original"
    elif change == "duplicate":
        rows[0]["predicted_numbers"] = "01 01 02 03 04 05 06"
    else:
        rows[0]["predicted_numbers"] = "01 02 03 04 05 06 38"
    with pytest.raises(ValueError):
        geometry.validate_issued_rows(rows, 702)


def test_canonical_append_never_writes_non_disjoint_702(tmp_path):
    csv_path = tmp_path / "loto7.csv"
    make_synthetic_csv(csv_path, 701)
    loto_rows = ledger.read_csv(csv_path)
    pred_path = tmp_path / "predictions.csv"
    valid = geometry.portfolio_for_target(702)
    bad = [tuple(numbers) for numbers in valid]
    bad[1] = bad[0]
    ticket_rows = [
        {"ticket": str(i), "numbers": " ".join(map(str, numbers))}
        for i, numbers in enumerate(bad, 1)
    ]
    state = {
        "target_round": "第702回",
        "latest_round": "第701回",
        "data_sha256": ledger.sha_file(csv_path),
        "production_ticket_policy_version": geometry.VERSION,
        "model_version": "baseline-test+" + geometry.VERSION,
    }
    with pytest.raises(ValueError, match="overlap"):
        ledger.append_current_predictions(loto_rows, ticket_rows, pred_path, state,
                                          current_data_sha=ledger.sha_file(csv_path))
    assert not pred_path.exists()

    good_rows = [
        {"ticket": str(i), "numbers": " ".join(map(str, numbers))}
        for i, numbers in enumerate(valid, 1)
    ]
    state["production_ticket_policy_version"] = "champion_original"
    with pytest.raises(RuntimeError, match="without disjoint35"):
        ledger.append_current_predictions(loto_rows, good_rows, pred_path, state,
                                          current_data_sha=ledger.sha_file(csv_path))
    assert not pred_path.exists()


def test_702_republish_rejects_edited_frozen_ledger(tmp_path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    make_synthetic_csv(csv_path, 701)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "source_validation.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(geometry, "verify_source",
                        lambda *_: {"trusted": True, "round": 701})
    monkeypatch.setattr(geometry, "production_window_guard", lambda *_: None)
    issued = weekly.publish(csv_path=csv_path, out_dir=out_dir,
                            champion_file=tmp_path / "missing_champion.json",
                            research_state=tmp_path / "missing_research.json")
    assert issued["ticket_policy"] == geometry.VERSION
    ledger_path = out_dir / "predictions.csv"
    rows = ledger.read_csv(ledger_path)
    rows[1]["predicted_numbers"] = rows[0]["predicted_numbers"]
    ledger.write_csv(ledger_path, rows, ledger.PRED_FIELDS)
    frozen_bytes = ledger_path.read_bytes()
    with pytest.raises(ValueError, match="overlap"):
        weekly.publish(csv_path=csv_path, out_dir=out_dir,
                       champion_file=tmp_path / "missing_champion.json",
                       research_state=tmp_path / "missing_research.json")
    assert ledger_path.read_bytes() == frozen_bytes
