"""Role-council integration and mutation-permission regression tests.

All mutation tests operate on isolated copies of repository evidence, never on
registered Future-OOS, Champion, production outputs or actual history.
"""
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

import agent_role_council as council


JST = timezone(timedelta(hours=9))
# Anchor the fixture clock to the actual checked-in source snapshot. A static
# time before the source checked_at timestamp incorrectly triggers a clock block.
NOW = datetime.fromisoformat(json.loads(
    Path("loto7_agent_output/source_validation.json").read_text(encoding="utf-8")
)["checked_at_jst"]) + timedelta(minutes=5)
OUT = [
    "source_validation.json", "model_champion.json", "shadow_registry.json",
    "future_holdout_state.json", "future_holdout_registry.json",
    "formal_challenger_state.json", "joint_set_v2_signal_oos_registration.json",
    "joint_set_v2_signal_oos_state.json", "joint_set_v2_conversion_audit_summary.json",
    "research_cycle_guard.json", "weekly_production_prediction_state.json",
]
CODE = ["joint_set_v2_signal_oos.py", "joint_set_v2_model.py", "joint_set_v2_research.py"]


@pytest.fixture()
def root(tmp_path):
    out = tmp_path / "loto7_agent_output"
    out.mkdir()
    repository = Path(".")
    for file in CODE + ["loto7.csv"]:
        shutil.copyfile(repository / file, tmp_path / file)
    for file in OUT:
        shutil.copyfile(repository / "loto7_agent_output" / file, out / file)
    return tmp_path


def rewrite(path, mutate):
    obj = json.loads(path.read_text(encoding="utf-8"))
    mutate(obj)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def set_verified_source_fixture(root):
    """Simulate a verified second-source record only in the isolated test tree.

    Never relabel the live degraded source report or registered Future-OOS.
    The real latest CSV and published-number fields remain unchanged.
    """
    path = root / "loto7_agent_output" / "source_validation.json"

    def verify(report):
        report["status"] = "ok"
        report["verification"] = "verified_two_result_sources"
        # A separate matching source *record* is mandatory under the existing
        # trusted-source guard; creating this is only a synthetic unit fixture.
        report.setdefault("sources", {})["rakuten_bank"] = dict(report["latest"])

    rewrite(path, verify)


def test_role_council_preserves_current_registered_evidence(root):
    report = council.evaluate(root, NOW)
    assert tuple(report["roles"]) == council.ROLES
    assert report["overall"] == "watch"  # Existing 7/26 holdout, current 699.
    assert report["latest_resolved_round"] == 699
    source = json.loads(
        (root / "loto7_agent_output" / "source_validation.json").read_text(encoding="utf-8")
    )
    expected_trust = (
        source["status"] == "ok"
        and source["verification"] == "verified_two_result_sources"
    )
    # A current one-source/degraded report is WATCH, not falsely trusted.
    assert report["roles"]["data_steward"]["status"] == (
        "ok" if expected_trust else "watch"
    )
    if not expected_trust:
        assert "RESULT_NOT_TWO_SOURCE_VERIFIED" in [
            f["code"] for f in report["roles"]["data_steward"]["findings"]
        ]
    assert report["roles"]["prospective_signal_custodian"]["status"] == "ok"
    assert report["roles"]["oos_risk_officer"]["status"] == "watch"
    assert report["roles"]["release_operations"]["status"] == "ok"
    assert report["governance"]["authority"] == "read_only_advisory"
    assert report["governance"]["auto_actions_taken"] == []
    assert not any(report["governance"]["permissions"][key] for key in (
        "freeze_or_backfill", "grade_prospective_outcomes", "update_model_or_signal",
        "publish_production_tickets", "promote_champion",
    ))
    assert report["input_snapshot_sha256"] == council.evaluate(root, NOW)["input_snapshot_sha256"]


def test_status_only_writes_two_advisory_files(root, tmp_path):
    dest = tmp_path / "report-only"
    before = {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*") if p.is_file()
    }
    result = council.run(root, dest, NOW)
    assert result["overall"] == "watch"
    assert sorted(x.name for x in dest.iterdir()) == [
        "agent_role_council_report.md", "agent_role_council_summary.json",
    ]
    for path, content in before.items():
        assert (root / path).read_bytes() == content
    assert "Read-only" in (dest / "agent_role_council_report.md").read_text()


def test_source_number_conflict_blocks_only_governed_role(root):
    # A *trusted* result must match the CSV and independently matching source.
    # Without this setup, the real degraded report must remain merely WATCH.
    set_verified_source_fixture(root)
    assert council.evaluate(root, NOW)["roles"]["data_steward"]["status"] == "ok"
    path = root / "loto7_agent_output" / "source_validation.json"
    rewrite(path, lambda s: s["latest"].update(main=[1, 2, 3, 4, 5, 6, 7]))
    result = council.evaluate(root, NOW)
    assert result["roles"]["data_steward"]["status"] == "block"
    assert result["overall"] == "block"
    assert result["roles"]["oos_risk_officer"]["status"] == "watch"
    assert result["handoff_tasks"][0]["owner"] == "data_steward"
    assert result["handoff_tasks"][0]["autonomous_production_write_allowed"] is False




def test_degraded_single_source_never_pretends_to_verify_conflicting_numbers(root):
    path = root / "loto7_agent_output" / "source_validation.json"

    def degrade_and_conflict(report):
        report["status"] = "degraded"
        report["verification"] = "degraded_single_result_source"
        report["latest"]["main"] = [1, 2, 3, 4, 5, 6, 7]

    rewrite(path, degrade_and_conflict)
    role = council.evaluate(root, NOW)["roles"]["data_steward"]
    assert role["status"] == "watch"
    assert role["findings"][0]["code"] == "RESULT_NOT_TWO_SOURCE_VERIFIED"


def test_trusted_result_with_mismatched_secondary_source_blocks(root):
    set_verified_source_fixture(root)
    path = root / "loto7_agent_output" / "source_validation.json"
    rewrite(path, lambda s: s["sources"]["rakuten_bank"].update(
        main=[1, 2, 3, 4, 5, 6, 7]
    ))
    role = council.evaluate(root, NOW)["roles"]["data_steward"]
    assert role["status"] == "block"
    assert role["findings"][0]["code"] == "DATA_INTEGRITY_BLOCK"


def test_registered_model_sha_drift_fails_closed(root):
    path = root / "joint_set_v2_model.py"
    path.write_text(path.read_text() + "\n# unauthorized drift\n")
    result = council.evaluate(root, NOW)
    assert result["roles"]["prospective_signal_custodian"]["status"] == "block"
    assert "PROSPECTIVE_LOCK_BLOCK" in [
        x["code"] for x in result["roles"]["prospective_signal_custodian"]["findings"]
    ]


def test_research_cannot_relabel_reused_history_as_promotable(root):
    path = root / "loto7_agent_output" / "joint_set_v2_conversion_audit_summary.json"
    rewrite(path, lambda obj: obj.update(independent_evidence=True, promotion_eligible=True))
    assert council.evaluate(root, NOW)["roles"]["research_skeptic"]["status"] == "block"


def test_missing_post_result_first_freeze_fails_closed(root):
    csv_path = root / "loto7.csv"
    with csv_path.open("a", encoding="utf-8") as f:
        f.write("\n2026-10-23,01 02 03 04 05 06 07,08 09,第700回,,,,,,,,,,,,\n")
        f.write("2026-10-30,01 02 03 04 05 06 07,08 09,第701回,,,,,,,,,,,,\n")
    role = council.prospective_signal_custodian(root, root / "loto7_agent_output", 701, False)
    assert role["status"] == "block"
    assert "missing mandatory prospective" in role["findings"][0]["evidence"]


def test_700_verified_prefix_without_701_freeze_creates_watch_handoff(root):
    role = council.prospective_signal_custodian(root, root / "loto7_agent_output", 700, True)
    assert role["status"] == "watch"
    assert role["findings"][-1]["code"] == "FREEZE_701_NOW"


def test_holdout_candidate_lock_mismatch_blocks(root):
    path = root / "loto7_agent_output" / "future_holdout_state.json"
    rewrite(path, lambda obj: obj.update(locked_candidate_version="switched-after-registered"))
    assert council.evaluate(root, NOW)["roles"]["oos_risk_officer"]["status"] == "block"


def test_no_retroactive_production_after_public_result_deadline(root):
    # Current Production already issued target 700 before the deadline. Recreate
    # the missing-publication failure ONLY inside this disposable fixture.
    path = root / "loto7_agent_output" / "weekly_production_prediction_state.json"
    rewrite(path, lambda obj: obj.update(published=False))
    deadline = datetime(2026, 10, 23, 20, 5, tzinfo=JST)
    role = council.release_operations(root / "loto7_agent_output", 699, deadline)
    assert role["status"] == "block"
    assert role["findings"][0]["code"] == "PRODUCTION_DEADLINE_PASSED"


def test_issued_production_still_passes_release_guard_after_draw(root):
    deadline = datetime(2026, 10, 23, 20, 5, tzinfo=JST)
    role = council.release_operations(root / "loto7_agent_output", 699, deadline)
    assert role["status"] == "ok"
    assert role["findings"][0]["code"] == "RELEASE_SCHEDULE_GUARD"


def test_missing_required_source_is_block_not_implicit_permission(root):
    (root / "loto7_agent_output" / "source_validation.json").unlink()
    role = council.data_steward(root, root / "loto7_agent_output", NOW)
    assert role["status"] == "block"
