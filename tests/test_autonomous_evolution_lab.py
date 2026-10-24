"""Autonomous research must evolve ONLY inside a bounded, separately labeled sandbox."""
import copy
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import autonomous_evolution_lab as ai
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible


@pytest.fixture()
def project(tmp_path: Path):
    root = tmp_path / "safe-autonomous-lab"
    out = root / "loto7_agent_output"
    out.mkdir(parents=True)
    rng = np.random.default_rng(7710)
    rows = []
    for i in range(150):
        selected = sorted(int(z) for z in rng.choice(np.arange(1, 38), 7, replace=False))
        extras = sorted(n for n in range(1, 38) if n not in selected)
        rows.append({
            "抽せん日": (date(2023, 1, 6) + timedelta(days=i * 7)).isoformat(),
            "本数字": " ".join(f"{n:02d}" for n in selected),
            "ボーナス数字": " ".join(f"{n:02d}" for n in extras[:2]),
            "回別": f"第{i+1}回",
        })
    pd.DataFrame(rows).to_csv(root / "loto7.csv", index=False, encoding="utf-8")
    latest = rows[-1]
    numbers = [int(x) for x in latest["本数字"].split()]
    bonus = [int(x) for x in latest["ボーナス数字"].split()]
    source = {
        "status": "degraded", "verification": "degraded_single_result_source",
        "latest": {"round": len(rows), "date": latest["抽せん日"],
                   "main": numbers, "bonus": bonus},
        "sources": {"provider_b": {"status": "unavailable"}},
    }
    guard = {
        "data_sha256": fingerprint_file(root / "loto7.csv"),
        "mode": "SEARCH", "search_enabled": True,
        "signal_trials_this_data": 5, "max_signal_trials_per_data": 800,
    }
    (out / "source_validation.json").write_text(json.dumps(source), encoding="utf-8")
    (out / "research_cycle_guard.json").write_text(json.dumps(guard), encoding="utf-8")
    return root


def rewrite(path, mutation):
    item = json.loads(path.read_text(encoding="utf-8"))
    mutation(item)
    path.write_text(json.dumps(item), encoding="utf-8")


def verified(project):
    source = project / "loto7_agent_output/source_validation.json"

    def approve(src):
        # An independent matching record is created ONLY in disposable tests.
        src["status"] = "ok"
        src["verification"] = "verified_two_result_sources"
        src["sources"]["provider_b"] = dict(src["latest"])
    rewrite(source, approve)


def test_unverified_result_never_trains_and_is_idempotent(project):
    out = project / "loto7_agent_output"
    original = {p.name: p.read_bytes() for p in out.iterdir()}
    first = ai.run(project)
    assert first["last_action"] == "WAIT_FOR_INDEPENDENT_RESULT_SOURCE"
    assert first["trials"] == []
    assert not first["authority"]["production_or_champion_update"]
    assert not first["authority"]["self_modifying_code"]
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    second = ai.run(project)
    assert second == first
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before
    assert {k: (out / k).read_bytes() for k in original} == original
    assert len(ai.read_chain(out / ai.LEDGER)) == 1


def test_verified_data_autonomously_proposes_scores_and_stops_at_four(project):
    verified(project)
    out = project / "loto7_agent_output"
    protected = {p.name: p.read_bytes() for p in out.iterdir()}
    for trial_no in range(1, 5):
        result = ai.run(project)
        assert result["last_action"] == "EVALUATE_SANDBOX_MUTATION"
        assert len(result["trials"]) == trial_no
        assert all(t["diagnostic"]["evaluated_historical_draws"] == 48
                   for t in result["trials"])
        assert all(t["diagnostic"]["historical_only"]
                   and not t["diagnostic"]["production_eligible"]
                   and not t["diagnostic"]["independent_future_evidence"]
                   for t in result["trials"])
    assert result["next_action"] == "WAIT_FOR_NEW_VERIFIED_HISTORY"
    assert result["diagnostic_leader"] in {t["candidate_id"] for t in result["trials"]}
    assert len({t["candidate_id"] for t in result["trials"]}) == 4
    # One harmless transition to WAIT is recorded, then repeated runs do nothing.
    ai.run(project)
    n = len(ai.read_chain(out / ai.LEDGER))
    ai.run(project)
    assert len(ai.read_chain(out / ai.LEDGER)) == n
    assert {k: (out / k).read_bytes() for k in protected} == protected


def test_wait_mode_refuses_trials_even_if_trusted(project):
    verified(project)
    guard = project / "loto7_agent_output/research_cycle_guard.json"
    rewrite(guard, lambda obj: obj.update(mode="WAIT_FOR_NEW_DATA", search_enabled=False))
    result = ai.run(project)
    assert result["trials"] == []
    assert result["last_action"] == "WAIT_FOR_NEW_DATA_OR_VALIDATION"


def test_cannot_spend_last_official_trial_envelope(project):
    verified(project)
    guard = project / "loto7_agent_output/research_cycle_guard.json"
    rewrite(guard, lambda obj: obj.update(signal_trials_this_data=800))
    result = ai.run(project)
    assert result["last_action"] == "WAIT_FOR_RESEARCH_BUDGET"
    assert result["trials"] == []


def test_history_source_or_budget_conflict_fail_closed_without_files(project):
    out = project / "loto7_agent_output"
    initial = {p.name: p.read_bytes() for p in out.iterdir()}
    guard = out / "research_cycle_guard.json"
    rewrite(guard, lambda g: g.update(data_sha256="not-current"))
    with pytest.raises(ValueError, match="different draw-history"):
        ai.run(project)
    assert not (out / ai.STATE).exists()
    guard.write_bytes(initial[guard.name])
    verified(project)
    source = out / "source_validation.json"
    rewrite(source, lambda s: s["sources"].update(provider_b={"round": 150, "main": [1]}))
    with pytest.raises(ValueError, match="matching secondary"):
        ai.run(project)
    assert not (out / ai.LEDGER).exists()


def test_detects_ledger_tampering_and_preserves_registered_inputs(project):
    result = ai.run(project)
    out = project / "loto7_agent_output"
    ledger = out / ai.LEDGER
    lines = ledger.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["action"] = "FORGED_TRAINING"
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ledger integrity"):
        ai.run(project)
    assert json.loads((out / ai.STATE).read_text()) == result


def test_prior_only_no_future_leakage(project):
    x, _ = make_history(read_csv_flexible(project / "loto7.csv"))
    config = {"window": 30, "prior": 100, "blend": 0.25}
    prefix = x[:-48].copy()
    q = ai.prior_probabilities(prefix, config)
    altered = x.copy()
    altered[-48:] = 0
    altered[-48:, :7] = 1
    assert np.allclose(q, ai.prior_probabilities(altered[:-48], config))
    assert np.isclose(float(q.sum()), 7.0)
    assert ai.propose([]) == config


def test_source_report_cannot_falsely_claim_verified_provider(project):
    out = project / "loto7_agent_output"
    source = out / "source_validation.json"
    rewrite(source, lambda s: s.update(status="ok", verification="verified_two_result_sources"))
    with pytest.raises(ValueError, match="matching secondary"):
        ai.run(project)
    assert not (out / ai.STATE).exists()
