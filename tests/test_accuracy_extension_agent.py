"""Accuracy extension: research-only hypotheses and honest prospective lifecycle.

All invented round 700/701 outcomes live only in pytest temporary directories.
"""
import csv
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

import accuracy_extension_agent as ext
import continuous_learning_agent as ledger
import predictive_expert_agent as base


JST = timezone(timedelta(hours=9))
CLOCK = datetime(2026, 10, 19, 9, 30, tzinfo=JST)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "synthetic_accuracy_lab"
    path.mkdir()
    (path / "out").mkdir()
    for filename in (*ext.FILES_LOCKED, "loto7.csv"):
        shutil.copyfile(Path(filename), path / filename)
    shutil.copyfile(Path("loto7_agent_output/predictive_expert_agent_summary.json"),
                    path / "out" / "predictive_expert_agent_summary.json")
    return path


def set_source(root, *, verified):
    x, clean, latest = ledger.validated_draws(root / "loto7.csv")
    date = clean["抽せん日"].iloc[-1].date().isoformat()
    published = {
        "round": latest, "date": date,
        "main": [int(i + 1) for i in np.flatnonzero(x[-1])],
        "bonus": [int(v) for v in str(clean["ボーナス数字"].iloc[-1]).split()],
    }
    result = {
        "status": "ok" if verified else "degraded",
        "verification": ext.SOURCE_TRUST if verified else "degraded_single_result_source",
        "latest": published,
        "sources": {"rakuten_bank": dict(published)},
    }
    source = root / "source_test.json"
    source.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return source


def add_draw(root, number):
    file = root / "loto7.csv"
    with file.open(encoding="utf-8-sig", newline="") as f:
        original = list(csv.DictReader(f))
    assert len(original) == number - 1
    new = {name: "" for name in original[0]}
    new.update({
        "抽せん日": {700: "2026-10-23", 701: "2026-10-30"}[number],
        "本数字": "01 02 03 04 05 06 07" if number == 700 else "08 09 10 11 12 13 14",
        "ボーナス数字": "18 19", "回別": f"第{number}回",
    })
    with file.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=list(original[0])).writerow(new)


def run(root, verified=True, when=CLOCK, worlds=1):
    return ext.run(root, root / "out", set_source(root, verified=verified),
                   now=when, null_worlds=worlds)


def test_transition_probability_lag_exposure_and_sum7():
    x = base.synthetic_fair_history(145, 32)
    pair = ext.prefix_pairs(x, len(x))
    p = ext.transition_expert(pair, x[-1])
    assert p.shape == (37,)
    assert np.all((0 < p) & (p < 1))
    assert p.sum() == pytest.approx(7, abs=1e-9)
    # With no evidence (not zero prior), the forecast remains fair uniform.
    empty = ext.transition_expert(np.zeros((37, 37), dtype=int), x[-1])
    assert np.allclose(empty, 7 / 37)


def test_prior_only_last_target_cannot_peek_at_its_outcome():
    x = base.synthetic_fair_history(130, 57)
    _, before, frozen = ext.walk(x[:-1], last_n=2)
    result, scored, _ = ext.walk(x, last_n=2)
    assert result["evaluated_rounds"] == 2
    assert scored[-1]["round"] == 130
    assert scored[-1]["weights"] == pytest.approx(frozen["expert_weights"])
    y = x.copy()
    y[-1] = 0
    y[-1, [3, 8, 13, 18, 23, 28, 33]] = 1
    _, altered, _ = ext.walk(y, last_n=2)
    assert altered[-1]["weights"] == pytest.approx(scored[-1]["weights"])
    assert scored[-1]["log_edge"] != altered[-1]["log_edge"]


def test_fair_world_full_algorithm_reproducible():
    a = ext.matched_fair_null(120, worlds=2, last_n=3)
    b = ext.matched_fair_null(120, worlds=2, last_n=3)
    assert a == b
    assert a["full_learner_rerun_each_fair_world"]
    assert a["no_prospective_claim"]
    assert len(a["log_edges"]) == 2
    with pytest.raises(ValueError, match="budget"):
        ext.matched_fair_null(120, worlds=0)


def test_start_699_register_only_degraded_no_fake_freeze(root):
    old = run(root, verified=False)
    assert old["status"] == "waiting_for_verified_round_700_prefix"
    assert old["trusted_future_draws"] == 0
    assert old["current_prefrozen_target"] is None
    assert old["promotion_eligible"] is False
    assert not old["p_values_valid_for_continual_monitoring"]
    assert (root / "out" / ext.REG).exists()
    assert not (root / "out" / ext.REGISTRY).exists()
    reg_before = (root / "out" / ext.REG).read_bytes()
    assert run(root, verified=False) == old
    assert (root / "out" / ext.REG).read_bytes() == reg_before


def test_verified_700_precedes_701_and_verified_701_grades_then_freezes_702(root):
    run(root, verified=False)
    add_draw(root, 700)
    untrusted = run(root, verified=False)
    assert untrusted["status"] == "awaiting_two_source_round_700"
    assert not (root / "out" / ext.FREEZES).exists()

    first = run(root, verified=True)
    assert first["current_prefrozen_target"] == 701
    freeze = ledger.read_chain(root / "out" / ext.FREEZES, kind="freeze")
    assert len(freeze) == 1
    sha = freeze[0]["record_sha256"]
    assert freeze[0]["base_round"] == 700
    assert sum(map(float, freeze[0]["inclusion_p_canonical"])) == pytest.approx(7)
    assert run(root, verified=True) == first

    add_draw(root, 701)
    waiting = run(root, verified=False)
    assert waiting["trusted_future_draws"] == 0
    assert waiting["status"] == "awaiting_verified_result"
    assert not (root / "out" / ext.GRADES).exists()
    graded = run(root, verified=True, when=CLOCK + timedelta(days=12))
    assert graded["trusted_future_draws"] == 1
    assert graded["current_prefrozen_target"] == 702
    rows = ledger.read_chain(root / "out" / ext.GRADES, kind="grade")
    assert rows[0]["frozen_record_sha256"] == sha
    assert rows[0]["actual_numbers"] == list(range(8, 15))
    assert graded["future_descriptive_only"]["mean_log_edge"] is not None
    assert run(root, verified=True, when=CLOCK + timedelta(days=12)) == graded


def test_fail_closed_on_changed_algorithm_after_registration(root):
    run(root, verified=False)
    path = root / "accuracy_extension_agent.py"
    path.write_text(path.read_text() + "\n# unregistered change\n")
    with pytest.raises(ValueError, match="algorithm drift"):
        run(root)


def test_frozen_vector_edit_is_not_accepted(root):
    run(root, verified=False)
    add_draw(root, 700)
    run(root, verified=True)
    path = root / "out" / ext.REGISTRY
    rec = json.loads(path.read_text(encoding="utf-8"))
    rec["top7_numbers"] = list(range(1, 8))
    path.write_text(json.dumps(rec))
    with pytest.raises(ValueError, match="registry changed"):
        run(root)


def test_grade_never_backfills_first_target(root):
    run(root, verified=False)
    add_draw(root, 700)
    add_draw(root, 701)
    with pytest.raises(ValueError, match="after it was drawn"):
        run(root, verified=True)


def test_invalid_history_or_wrong_freeze_prefix_is_blocked(root):
    x = base.synthetic_fair_history(120, 3)
    x[80, :] = 0
    with pytest.raises(ValueError, match="seven"):
        ext.walk(x)
    run(root, verified=False)
    add_draw(root, 700)
    run(root, verified=True)
    path = root / "loto7.csv"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("01 02 03 04 05 06 07", "01 02 03 04 05 06 08"))
    with pytest.raises(ValueError, match="historical outcomes changed"):
        run(root, verified=True)


def test_never_write_any_production_or_prior_registered_evidence(root):
    run(root, verified=False)
    created = {p.name for p in (root / "out").iterdir()}
    assert created == {
        "predictive_expert_agent_summary.json", ext.REG, ext.STATE, ext.SUMMARY, ext.REPORT
    }
    assert not created.intersection({
        "model_champion.json", "weekly_production_prediction_state.json",
        "joint_set_v2_signal_oos_registry.json",
        "continuous_learning_agent_registry.json",
    })
