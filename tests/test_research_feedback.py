from dataclasses import asdict

import loto7_v2_runner as v2
import research_feedback as rf


def _summary(objective: float, full_max: float = 2.4, recent_score: float = 2.8):
    def win(score_delta, max_hits, score):
        return {
            "score_delta_vs_random": score_delta,
            "max_hits": max_hits,
            "score": score,
        }
    return {
        "feedback_objective": objective,
        "windows": {
            "full": win(objective, full_max, 2.7),
            "120": win(objective, full_max, recent_score),
            "60": win(objective, full_max, recent_score),
            "30": win(objective, full_max, recent_score),
        },
    }


def test_accepts_candidate_only_when_replay_objective_improves_without_regression():
    incumbent = _summary(0.10, full_max=2.40, recent_score=2.80)
    candidate = _summary(0.12, full_max=2.40, recent_score=2.81)
    accepted, detail = rf.decide_accept(candidate, incumbent)
    assert accepted
    assert detail["objective_gain"] > 0
    assert all(detail["checks"].values())


def test_rejects_short_term_candidate_when_full_history_max_hits_regress():
    incumbent = _summary(0.10, full_max=2.40, recent_score=2.80)
    candidate = _summary(0.15, full_max=2.30, recent_score=2.90)
    accepted, detail = rf.decide_accept(candidate, incumbent)
    assert not accepted
    assert not detail["checks"]["full_max_hits_not_regressed"]


def test_rejects_candidate_when_recent_120_score_regresses():
    incumbent = _summary(0.10, full_max=2.40, recent_score=2.80)
    candidate = _summary(0.15, full_max=2.40, recent_score=2.70)
    accepted, detail = rf.decide_accept(candidate, incumbent)
    assert not accepted
    assert not detail["checks"]["recent120_score_not_regressed"]


def test_apply_parent_overwrites_provisional_parent_for_next_generation():
    candidate = v2.ModelConfig("candidate", 2.0, 0.994, 0.20, 0.20, 0.7)
    accepted = v2.ModelConfig("accepted", 1.8, 0.996, 0.22, 0.25, 0.8)
    state = {"research_feedback_replays": 3, "research_feedback_accepts": 1}
    feedback = {
        "replayed": True,
        "candidate_accepted": False,
        "candidate_version": candidate.version(),
        "accepted_parent_version": accepted.version(),
    }
    rf.apply_parent_to_research_state(state, candidate, accepted, feedback)
    assert state["provisional_research_winner"] == candidate.version()
    assert state["research_winner"] == accepted.version()
    assert state["research_parent_config"] == asdict(accepted)
    assert state["research_feedback_replays"] == 4
    assert state["research_feedback_accepts"] == 1


def test_cache_key_changes_with_model_or_data():
    a = v2.DEFAULT_CHAMPION
    b = v2.ModelConfig("other", 2.0, 0.994, 0.20, 0.20, 0.7)
    k1 = rf.cache_key("data-a", a, 100, 350, 8)
    k2 = rf.cache_key("data-b", a, 100, 350, 8)
    k3 = rf.cache_key("data-a", b, 100, 350, 8)
    assert k1 != k2
    assert k1 != k3
