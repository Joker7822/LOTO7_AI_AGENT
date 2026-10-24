"""Open-ended evolutionary researcher: indefinite generations, checkpoint recovery."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import open_ended_evolution_agent as agent
from loto7_evolving_agent import make_history, read_csv_flexible


@pytest.fixture()
def root(tmp_path):
    p = tmp_path / "open-ended"
    out = p / "loto7_agent_output"
    out.mkdir(parents=True)
    rng = np.random.default_rng(125)
    rows = []
    for n in range(155):
        win = sorted(int(v) for v in rng.choice(np.arange(1, 38), 7, replace=False))
        other = sorted(i for i in range(1, 38) if i not in win)
        rows.append({
            "回別": f"第{n+1}回",
            "抽せん日": (pd.Timestamp("2023-01-06") + pd.Timedelta(days=n*7)).strftime("%Y-%m-%d"),
            "本数字": " ".join(f"{k:02}" for k in win),
            "ボーナス数字": " ".join(f"{k:02}" for k in other[:2]),
        })
    pd.DataFrame(rows).to_csv(p / "loto7.csv", index=False)
    (out / "source_validation.json").write_text(json.dumps({
        "verification": "degraded_single_result_source",
        "status": "degraded",
        "latest": {"round": len(rows)}
    }))
    # Production and official research budget are intentionally present to
    # verify they are NEVER modified by this separate open-ended experiment.
    (out / "model_champion.json").write_text('{"version":"frozen"}')
    (out / "research_cycle_guard.json").write_text(
        '{"mode":"WAIT_FOR_NEW_DATA","signal_trials_this_data":800}'
    )
    return p


def protected(root):
    out = root / "loto7_agent_output"
    return {
        p.name: p.read_bytes()
        for p in out.iterdir()
        if p.name in {"model_champion.json", "research_cycle_guard.json",
                      "source_validation.json"}
    } | {"loto7.csv": (root / "loto7.csv").read_bytes()}


def test_indefinite_generations_continue_on_same_degraded_history(root):
    before = protected(root)
    a = agent.cycle(root, steps=6)
    assert a["generations_total"] == 6
    assert a["execution_limits"]["global_generation_cap"] is None
    assert a["execution_limits"]["global_trial_cap"] is None
    assert a["latest_verification"] == "degraded_single_result_source"
    assert a["last_unverified_row_excluded"]
    assert a["evaluation_rounds"] == 154
    assert len(a["hall_of_fame"]) <= 8
    b = agent.cycle(root, steps=9)
    assert b["generations_total"] == 15
    assert b["research_champion"]["assessment"]["historical_selection_only"]
    assert not b["research_champion"]["assessment"]["prospective_edge_confirmed"]
    assert len(agent.journal(root / "loto7_agent_output" / agent.LEDGER)) == 2
    assert protected(root) == before


def test_evolved_candidate_code_executes_equivalent_math_only(root):
    result = agent.cycle(root, steps=4)
    text = (root / "loto7_agent_output" / agent.PROGRAM).read_text()
    assert "AUTO-GENERATED RESEARCH MODEL" in text
    assert "def predict_inclusion_probability" in text
    scope = {}
    exec(compile(text, "<generated-research-only>", "exec"), scope)
    x, _ = make_history(read_csv_flexible(root / "loto7.csv"))
    same = agent.inclusion(x[:-1], result["research_champion"]["genome"])
    assert np.allclose(scope["predict_inclusion_probability"](x[:-1]), same)
    assert np.isclose(same.sum(), 7)
    assert np.all((same > 0) & (same < 1))


def test_all_features_are_numerically_valid_without_int8_wrap(root):
    x, _ = make_history(read_csv_flexible(root / "loto7.csv"))
    for op, parameters in (
        ("uniform", {}),
        ("frequency", {"window": 60, "prior": 30.0}),
        ("decay", {"half_life": 20.0}),
        ("gap", {"scale": 12.0}),
        ("pair", {"window": 100, "prior": 40.0}),
    ):
        q = agent.inclusion(x, {"op": op, **parameters})
        assert np.all(np.isfinite(q))
        assert q.sum() == pytest.approx(7, abs=1e-8)
    hist = np.zeros((150, 37), dtype=np.int8)
    hist[:, :7] = 1
    # Explicit wide pair-context arithmetic remains finite/valid.
    q = agent.inclusion(hist, {"op": "pair", "window": 140, "prior": 20.})
    assert np.isclose(q.sum(), 7)


def test_chronological_evaluation_cannot_use_target_draw(root):
    x, _ = make_history(read_csv_flexible(root / "loto7.csv"))
    gene = {"op": "blend", "alpha": .6,
            "left": {"op": "frequency", "window": 80, "prior": 100.},
            "right": {"op": "power", "exponent": 1.3,
                      "child": {"op": "decay", "half_life": 20.}}}
    before = agent.inclusion(x[:-48], gene)
    altered = x.copy()
    altered[-48:] = 0
    altered[-48:, 2:9] = 1
    assert np.allclose(before, agent.inclusion(altered[:-48], gene))
    assert agent.assess(x, gene)["mean_log_edge"] != agent.assess(altered, gene)["mean_log_edge"]


def test_audit_tamper_stops_evolution(root):
    agent.cycle(root, steps=2)
    path = root / "loto7_agent_output" / agent.LEDGER
    rec = json.loads(path.read_text().splitlines()[0])
    rec["snapshot"]["research_champion"]["assessment"]["fitness"] = 99999
    path.write_text(json.dumps(rec) + "\n")
    with pytest.raises(ValueError, match="hash chain corrupted"):
        agent.cycle(root, steps=1)


def test_recover_missing_state_from_verified_journal(root):
    a = agent.cycle(root, steps=2)
    path = root / "loto7_agent_output" / agent.STATE
    path.unlink()
    b = agent.cycle(root, steps=3)
    assert b["generations_total"] == a["generations_total"] + 3
    assert b["last_record_sha256"] == agent.journal(
        root / "loto7_agent_output" / agent.LEDGER)[-1]["record_sha256"]


def test_source_mismatch_fails_without_writing_any_research_file(root):
    p = root / "loto7_agent_output/source_validation.json"
    p.write_text('{"verification":"degraded","latest":{"round":1000}}')
    with pytest.raises(ValueError, match="disagree"):
        agent.cycle(root, steps=1)
    assert not (root / "loto7_agent_output" / agent.LEDGER).exists()


def test_operator_family_and_genome_mutations_do_not_have_four_trial_ceiling(root):
    a = agent.cycle(root, steps=17)
    assert a["generations_total"] == 17
    ops = set()
    def walk(g):
        ops.add(g["op"])
        for key in ("left", "right", "child"):
            if key in g:
                walk(g[key])
    walk(a["research_champion"]["genome"])
    assert ops <= set(agent.FEATURES) | set(agent.COMPOSITES)
    assert a["research_champion"]["generation"] <= 17


def test_reject_invalid_program_instruction(root):
    x, _ = make_history(read_csv_flexible(root / "loto7.csv"))
    with pytest.raises(ValueError, match="unknown evolved program"):
        agent.inclusion(x, {"op": "shell_command", "code": "echo no"})
