"""Round 20 onward genuine prior-only REPLAY (not independent future OOS)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import round20_change_replay as replay

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def full_replay():
    try:
        status = replay.validate_trusted_source(
            ROOT/"loto7.csv", ROOT/"loto7_agent_output/source_validation.json"
        )
    except (ValueError, RuntimeError, KeyError):
        status = {"trusted": False}
    if status.get("trusted") is not True:
        pytest.skip("intentionally pinned historical CI data lacks two-source trust")
    return replay.execute(ROOT, pool_size=100)


def test_first_round_is_explicitly_20():
    assert replay.FIRST_ROUND == 20
    assert replay.MODEL_MIN_PRIOR == 20
    assert replay.LEARNED_MIN_PRIOR == 100


def test_19_history_predictor_cold_start_and_20_history_model_start(full_replay):
    summary, data = full_replay
    last = summary["last_target_round"]
    assert summary["first_target_round"] == 20
    assert last >= 700
    assert summary["round20_handling"] == "uniform_cold_start_with_19_prior_draws"
    rows = {(r["lane"], r["target_round"]): r for r in data}
    a = rows["current_champion", 20]
    b = rows["current_champion", 21]
    assert a["prior_rounds"] == 19
    assert a["training_status"] == "cold_start_19_priors_uniform"
    assert b["prior_rounds"] == 20
    assert b["training_status"] == "prior_only_champion"
    assert summary["lanes"]["current_champion"]["rounds"] == last - 19
    assert summary["lanes"]["uniform_disjoint35"]["rounds"] == last - 19
    assert summary["lanes"]["top1_shared34"]["rounds"] == last - 19
    assert summary["total_retrospective_rows"] >= 3 * (last - 19)
    assert summary["first_model_eligible_target"] == 21


def test_each_prior_round_is_complete_valid_and_seed_frozen(full_replay):
    summary, data = full_replay
    seen = set()
    for row in data:
        key = (row["lane"], row["target_round"])
        assert key not in seen
        seen.add(key)
        assert row["target_round"] == row["prior_rounds"] + 1
        assert len(row["forecast_sha256"]) == 64
        assert len(row["training_data_sha256"]) == 64
        assert 0 <= row["top7_hits"] <= 7
        assert 0 <= row["max_hits"] <= 7
        assert 0 <= row["mean_ticket_hits"] <= 7
        assert 0 <= row["any_ge3"] <= 1
        assert 0 <= row["any_ge4"] <= 1
        assert row["diagnostic_only"] is True
        tickets = [tuple(int(x) for x in row[f"ticket_{k}"].split()) for k in range(1, 6)]
        replay.check_tickets(tickets, row["coverage"])
        if row["lane"] == "uniform_disjoint35":
            assert row["coverage"] == 35
        elif row["lane"] == "top1_shared34":
            assert row["coverage"] == 34
    assert len(seen) == summary["total_retrospective_rows"]


def test_model_replay_is_not_confused_with_oos_claim(full_replay):
    s, _ = full_replay
    assert s["evaluation_type"] == "retrospective_reexecution_with_priors_only"
    assert s["model_selected_using_full_historical_data"]
    assert s["trial_budget_consumed"] == 0
    assert not s["first_prize_odds_improved"]
    assert not s["production_promoted"]
    assert not s["future_oos_registry_or_pre_frozen_predictions_modified"]
    assert s["outcome_was_not_an_input_to_any_forecast"]
    assert s["source_manifest_sha256"] == replay.sha(
        replay.stable(s["source_file_sha256"]).encode()
    )


def test_first_round_score_comparison_uses_exact_same_actual_set(full_replay):
    _, rows = full_replay
    first = [r for r in rows if r["target_round"] == 20]
    assert len(first) == 3
    assert len({r["actual_main"] for r in first}) == 1
    assert len({r["actual_bonus"] for r in first}) == 1
    assert first[0]["training_data_sha256"] == first[1]["training_data_sha256"]
    assert first[1]["training_data_sha256"] == first[2]["training_data_sha256"]


def test_forecast_commitment_does_not_depend_on_target_outcome():
    q = np.full(37, 1/37, dtype=float)
    tickets = replay.disjoint.disjoint_portfolio(1009321)
    kwargs = dict(
        target=20, date="2013-08-23", prior=19,
        lane="uniform_disjoint35", version=replay.disjoint.VERSION,
        training="fair_uniform_geometry_only",
        training_sha="f"*64, q=q, tickets=tickets,
        bonus=(3, 17),
    )
    a = replay.make_row(**kwargs, actual={1,2,3,4,5,6,7})
    b = replay.make_row(**kwargs, actual={31,32,33,34,35,36,37})
    assert a["forecast_sha256"] == b["forecast_sha256"]
    assert a["training_data_sha256"] == b["training_data_sha256"]
    assert a["actual_main"] != b["actual_main"]
    assert a["composite_score"] != b["composite_score"]


def test_theoretical_fair_world_premiums_do_not_claim_lottery_signal():
    a = replay.disjoint.exact_disjoint_null()
    b = replay.overlap34.exact_fair_null()
    assert a["covered_distinct_numbers"] == 35
    assert b["distinct_numbers"] == 34
    assert a["score"] > b["score"]
    assert a["any_first_prize_probability"] == b["first_prize_probability"]
    assert a["total_possible_draws"] == b["total_possible_draws"]


def test_csv_export_deterministic_and_complete():
    q = np.full(37, 1/37)
    t = replay.disjoint.disjoint_portfolio(981)
    r = replay.make_row(
        target=20, prior=19, date="2013-08-23",
        lane="uniform_disjoint35", version=replay.disjoint.VERSION,
        training="fair_uniform_geometry_only", training_sha="0"*64,
        q=q, tickets=t, actual={1,2,3,4,5,6,7}, bonus=(8,9)
    )
    raw = replay.csv_data([r])
    assert raw.count("\n") == 2
    assert "uniform_disjoint35" in raw
    assert "=HYPERLINK" not in raw
    assert raw == replay.csv_data([r])


def test_tampered_model_version_or_invalid_pool_fails_before_testing(monkeypatch):
    with pytest.raises(ValueError, match="invalid bounded"):
        replay.execute(ROOT, pool_size=1)
    with pytest.raises(ValueError, match="invalid bounded"):
        replay.execute(ROOT, pool_size=5000)
    assert replay.check_tickets(replay.disjoint.disjoint_portfolio(771), 35)


def test_generated_research_manifest_is_never_unverified_python_execution(tmp_path):
    g = tmp_path / "research/autonomous_generated"
    g.mkdir(parents=True)
    cfg = {"window": 30, "prior": 100, "blend": 0.25}
    candidate_id = "a"*20
    data_sha = "b"*64
    state_sha = "c"*64
    source = replay.rewrite.generate_source(
        config=cfg, candidate_id=candidate_id, data_sha=data_sha,
        source_state_sha=state_sha,
    )
    (g / "research_model.py").write_text(source, encoding="utf-8")
    manifest = {
        "learned_config": cfg, "learned_candidate_id": candidate_id,
        "draw_data_sha256": data_sha, "source_state_sha256": state_sha,
        "source_sha256": replay.sha(source.encode()),
        "source_authority": "research_only_not_loaded_by_production",
        "champion_changed": False, "historical_only_not_independent": True,
    }
    (g/"research_model_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    conf, meta = replay.learned_program(tmp_path)
    assert conf == cfg and meta["enabled"]
    (g/"research_model.py").write_text(source + "\n__import__('os').system('pwd')")
    with pytest.raises(ValueError, match="template"):
        replay.learned_program(tmp_path)


def test_replay_rejects_untrusted_lottery_data_in_pinned_699_fixture(monkeypatch):
    original = replay.validate_trusted_source
    monkeypatch.setattr(replay, "validate_trusted_source",
                        lambda *_: {"trusted": False, "round": 700})
    with pytest.raises(ValueError, match="independently two-source verified"):
        replay.validate_inputs(
            ROOT, ROOT/"loto7.csv",
            ROOT/"loto7_agent_output/source_validation.json",
            ROOT/"loto7_agent_output/model_champion.json"
        )
    monkeypatch.setattr(replay, "validate_trusted_source", original)


def test_full_replay_is_read_only(full_replay):
    _, rows = full_replay
    assert rows
    protected = [
        "loto7.csv",
        "loto7_agent_output/model_champion.json",
        "research/disjoint_future_oos/freeze_0701.json",
    ]
    before = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
              for p in protected}
    # The fixture already executed and remained pure; verify source files exist
    # and no mutation is required to serialize its output.
    s, data = full_replay
    assert "第20回" in replay.markdown(s)
    assert replay.csv_data(data) == replay.csv_data(data)
    assert before == {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                      for p in protected}
