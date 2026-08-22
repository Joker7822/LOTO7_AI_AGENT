from pathlib import Path

import research_feedback_bootstrap as rb


def test_bootstrap_prefers_research_parent_from_evaluation(tmp_path: Path):
    evaluation = {
        "research_parent": "parent-v1",
        "evaluations": [
            {
                "version": "parent-v1",
                "config": {
                    "name": "parent",
                    "eta": 1.5,
                    "decay": 0.995,
                    "expert_uniform_mix": 0.2,
                    "final_uniform_mix": 0.2,
                    "overlap_penalty": 0.7,
                },
            }
        ],
    }
    state = rb.bootstrap(evaluation, tmp_path / "missing-champion.json")
    assert state["accepted_parent_version"] == "parent-v1"
    assert state["accepted_parent_config"]["name"] == "parent"
    assert state["data_sha256"] == ""


def test_config_for_version_ignores_nonmatching_entries():
    evaluation = {
        "evaluations": [
            {"version": "a", "config": {"name": "a"}},
            {"version": "b", "config": {"name": "b"}},
        ]
    }
    assert rb.config_for_version(evaluation, "b") == {"name": "b"}
    assert rb.config_for_version(evaluation, "c") is None
