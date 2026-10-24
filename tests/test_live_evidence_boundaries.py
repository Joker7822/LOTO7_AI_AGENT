"""Validate real checked-in draw/OOS evidence on the newest main data.

These are NOT 699-only historical fixtures. They must work with later draws,
including outcomes recorded for diagnostics before secondary verification.
"""
import csv
import json
from pathlib import Path

import pytest

import autonomous_evolution_lab as autonomy
import dashboard_status_snapshot as dashboard
from loto7_evolving_agent import make_history, read_csv_flexible
from loto7_v4_runner import parse_round

ROOT = Path(".")
OUT = ROOT / "loto7_agent_output"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_current_draw_source_identity_and_trust_boundary():
    x, history = make_history(read_csv_flexible(ROOT / "loto7.csv"))
    latest = parse_round(history["回別"].iloc[-1])
    source = load("source_validation.json")
    assert latest == len(x)
    assert source["latest"]["round"] == latest
    assert source["latest"]["date"] == history["抽せん日"].iloc[-1].date().isoformat()
    actual = [int(j) + 1 for j in __import__("numpy").flatnonzero(x[-1])]
    assert actual == sorted(source["latest"]["main"])
    if source["verification"] != "verified_two_result_sources":
        assert source["status"] != "ok"


def test_current_holdout_tracks_all_outcomes_but_only_trusted_scores():
    state = load("future_holdout_state.json")
    with (OUT / "future_holdout_results.csv").open(encoding="utf-8-sig", newline="") as stream:
        items = list(csv.DictReader(stream))
    rounds = [int(row["round"]) for row in items]
    assert rounds == state["graded_rounds"]
    assert len(rounds) == state["all_draws"]
    assert rounds == list(range(state["start_target_round"], state["start_target_round"] + len(rounds)))
    trusted = [
        row for row in items if row["trusted"].lower() == "true"
        and row["source_verification"] == "verified_two_result_sources"
    ]
    assert len(trusted) == state["trusted_draws"]
    for row in items:
        assert dashboard.before_draw(row), "retroactively frozen portfolio"
        assert (row["trusted"].lower() == "true") == (
            row["source_verification"] == "verified_two_result_sources"
        )
    public_series = dashboard.read_portfolio(OUT, state)
    assert [row["round"] for row in public_series] == [int(row["round"]) for row in trusted]
    assert len(public_series) == state["trusted_draws"]
    assert all(row["round"] <= int(trusted[-1]["round"]) for row in public_series) if trusted else not public_series


def test_latest_oos_officer_distinguishes_untrusted_from_ledger_corruption():
    import agent_role_council as council

    state = load("future_holdout_state.json")
    latest = load("source_validation.json")["latest"]["round"]
    role = council.oos_risk_officer(OUT, latest)
    assert role["status"] in ("ok", "watch")
    assert "OOS_REFERENCE_CONSISTENCY" in [v["code"] for v in role["findings"]]
    assert state["trusted_draws"] <= state["all_draws"]


def test_independent_source_gap_does_not_authorize_sandbox_trials():
    info, _ = autonomy.inspect(ROOT)
    source = load("source_validation.json")
    if source["verification"] != "verified_two_result_sources":
        assert info["trusted"] is False
        assert autonomy.next_action(info, []) == "WAIT_FOR_INDEPENDENT_RESULT_SOURCE"


def test_reject_disguised_untrusted_portfolio_as_verified(tmp_path):
    state = load("future_holdout_state.json")
    with (OUT / "future_holdout_results.csv").open(encoding="utf-8-sig", newline="") as stream:
        items = list(csv.DictReader(stream))
    if not any(row["trusted"].lower() == "false" for row in items):
        pytest.skip("no not-yet-verified outcome in current snapshot")
    target = tmp_path / "future_holdout_results.csv"
    one = next(row for row in items if row["trusted"].lower() == "false")
    one["source_verification"] = "verified_two_result_sources"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=items[0])
        writer.writeheader()
        writer.writerows(items)
    with pytest.raises(ValueError, match="unverified|contradictory"):
        dashboard.read_portfolio(tmp_path, state)
