import json
from pathlib import Path

import formal_challenger as fc
import loto7_v4_runner as v4


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def candidate(version: str, score: float):
    return {
        "version": version,
        "config": {
            "name": version,
            "eta": 1.0,
            "decay": 0.99,
            "expert_uniform_mix": 0.2,
            "final_uniform_mix": 0.2,
            "overlap_penalty": 0.7,
        },
        "research_score": score,
        "tickets": [[1, 2, 3, 4, 5, 6, 7]] * 5,
    }


def registry(target=692, champion="champ", candidates=None):
    return {
        "agent_version": v4.AGENT_VERSION,
        "target_round": target,
        "base_data_sha": "sha",
        "frozen_at_jst": "2026-08-23T00:00:00+09:00",
        "champion_version": champion,
        "champion_tickets": [[1, 2, 3, 4, 5, 6, 8]] * 5,
        "candidates": candidates or [candidate("c1", 5.0), candidate("c2", 4.0)],
    }


def test_initial_enforcement_keeps_one_highest_frozen_candidate(tmp_path: Path):
    out = tmp_path / "out"
    write(out / "shadow_registry.json", registry())
    write(out / "oos_candidate_state.json", {
        "graded_rounds": [],
        "evidence": {
            v4.e_key("c1", "champ"): {"trusted_draws": 0},
            v4.e_key("c2", "champ"): {"trusted_draws": 0},
        },
    })

    result = fc.enforce(out)
    assert result["enforced"] is True
    assert result["formal_challenger_version"] == "c1"

    reg = json.loads((out / "shadow_registry.json").read_text())
    assert len(reg["candidates"]) == 1
    assert reg["candidates"][0]["version"] == "c1"
    assert reg["promotion_candidate_count"] == 1

    oos = json.loads((out / "oos_candidate_state.json").read_text())
    assert oos["evidence"] == {}
    archived = json.loads((out / "research_shadow_registry.json").read_text())
    assert len(archived["candidates"]) == 2
    assert archived["promotion_eligible"] is False


def test_active_candidate_is_locked_before_eight_trusted_draws(tmp_path: Path):
    out = tmp_path / "out"
    write(out / "shadow_registry.json", registry(target=693, candidates=[candidate("c2", 10.0), candidate("c1", 5.0)]))
    write(out / "formal_challenger_state.json", fc.make_state("champ", candidate("c1", 5.0), 692, "test"))
    write(out / "oos_candidate_state.json", {
        "graded_rounds": [692],
        "evidence": {
            v4.e_key("c1", "champ"): {
                "candidate_version": "c1",
                "champion_version": "champ",
                "trusted_draws": 1,
                "last_round": 692,
            },
            v4.e_key("c2", "champ"): {"trusted_draws": 1},
        },
    })

    result = fc.enforce(out)
    assert result["formal_challenger_version"] == "c1"
    assert result["trusted_draws"] == 1
    reg = json.loads((out / "shadow_registry.json").read_text())
    assert [x["version"] for x in reg["candidates"]] == ["c1"]
    oos = json.loads((out / "oos_candidate_state.json").read_text())
    assert list(oos["evidence"].keys()) == [v4.e_key("c1", "champ")]


def test_completed_eight_draw_block_rotates_and_resets_evidence(tmp_path: Path):
    out = tmp_path / "out"
    write(out / "shadow_registry.json", registry(target=700, candidates=[candidate("c1", 5.0), candidate("c2", 6.0)]))
    write(out / "formal_challenger_state.json", fc.make_state("champ", candidate("c1", 5.0), 692, "test"))
    write(out / "oos_candidate_state.json", {
        "graded_rounds": list(range(692, 700)),
        "evidence": {
            v4.e_key("c1", "champ"): {
                "candidate_version": "c1",
                "champion_version": "champ",
                "trusted_draws": 8,
                "sum_delta": 0.0,
                "wins": 4,
                "e_value": 1.0,
                "last_round": 699,
            }
        },
    })

    result = fc.enforce(out)
    assert result["formal_challenger_version"] == "c2"
    assert result["rotated"] is True
    oos = json.loads((out / "oos_candidate_state.json").read_text())
    assert oos["evidence"] == {}
    history = (out / "formal_challenger_history.jsonl").read_text().strip().splitlines()
    assert len(history) == 1
    rec = json.loads(history[0])
    assert rec["outcome"] == "block_completed_without_promotion"
    assert rec["final_evidence"]["trusted_draws"] == 8


def test_champion_change_starts_new_block(tmp_path: Path):
    out = tmp_path / "out"
    write(out / "shadow_registry.json", registry(target=700, champion="newchamp", candidates=[candidate("c3", 9.0)]))
    write(out / "formal_challenger_state.json", fc.make_state("oldchamp", candidate("c1", 5.0), 692, "test"))
    write(out / "oos_candidate_state.json", {
        "graded_rounds": [692],
        "evidence": {v4.e_key("c1", "oldchamp"): {"trusted_draws": 3}},
    })

    result = fc.enforce(out)
    assert result["champion_version"] == "newchamp"
    assert result["formal_challenger_version"] == "c3"
    state = json.loads((out / "formal_challenger_state.json").read_text())
    assert state["champion_version"] == "newchamp"
    assert state["trusted_draws_so_far"] == 0
