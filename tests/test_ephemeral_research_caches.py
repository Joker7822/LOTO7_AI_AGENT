"""Regression checks for removing derived optimizer caches from Git.

The active research scripts must start with empty caches and rebuild them safely,
while prospective freeze registries and append-only evidence remain tracked.
"""
from pathlib import Path

import feedback_optimizer
import research_feedback
import separated_optimizer


CACHE_PATHS = (
    "loto7_agent_output/feedback_optimizer_cache.json",
    "loto7_agent_output/research_feedback_cache.json",
    "loto7_agent_output/separated_signal_cache.json",
)

EVIDENCE_PATHS = (
    "loto7_agent_output/feedback_optimizer_history.jsonl",
    "loto7_agent_output/research_feedback_history.jsonl",
    "loto7_agent_output/joint_set_v2_signal_oos_registration.json",
    "loto7_agent_output/joint_set_v2_signal_oos_state.json",
    "loto7_agent_output/source_validation.json",
    "loto7_agent_output/model_champion.json",
    "loto7_agent_output/future_holdout_registry.json",
)


def test_missing_runtime_optimizer_caches_are_supported(tmp_path):
    template = {"optimizer_version": "test", "entries": {}}
    for module, name in (
        (feedback_optimizer, "feedback_optimizer_cache.json"),
        (research_feedback, "research_feedback_cache.json"),
        (separated_optimizer, "separated_signal_cache.json"),
    ):
        missing_path = tmp_path / name
        assert not missing_path.exists()
        assert module.load_json(missing_path, template) == template
        assert not missing_path.exists()


def test_gitignore_applies_only_to_derived_cache_files():
    patterns = set(Path(".gitignore").read_text(encoding="utf-8").splitlines())
    for path in CACHE_PATHS:
        assert "/" + path in patterns
        assert not Path(path).exists(), "derived caches must not remain tracked"
    for path in EVIDENCE_PATHS:
        assert Path(path).exists(), "scientific/OOS evidence must remain in the repository"
        assert "/" + path not in patterns
