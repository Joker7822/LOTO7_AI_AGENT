import loto7_v2_runner as v2
from nested_replay import bootstrap_mean_ci, composite_past_score, select_research_model, summarize


def test_composite_past_score_excludes_target_row():
    records = {
        100: {"score": 1.0},
        101: {"score": 1.0},
        102: {"score": 99.0},
    }
    score_at_102 = composite_past_score(records, 102, 100)
    assert score_at_102 == 1.0


def test_selector_uses_only_prior_records():
    a, b = v2.DEFAULT_CHAMPION, v2.CHALLENGERS[0]
    sims = {
        a.version(): {100: {"score": 2.0}, 101: {"score": 2.0}, 102: {"score": 0.0}},
        b.version(): {100: {"score": 1.0}, 101: {"score": 1.0}, 102: {"score": 100.0}},
    }
    selected, _ = select_research_model(sims, [a, b], 102, 100)
    assert selected.version() == a.version()


def test_bootstrap_ci_contains_observed_mean_for_constant_values():
    got = bootstrap_mean_ci([0.25] * 20, reps=100)
    assert got["mean"] == 0.25
    assert got["low95"] == 0.25
    assert got["high95"] == 0.25


def test_summary_three_way_comparison():
    rows = [{
        "round": 690,
        "selected_research_model": v2.CHALLENGERS[0].version(),
        "champion_max_hits": 2,
        "research_max_hits": 3,
        "random_mean_max_hits": 2.4,
        "champion_mean_hits": 1.2,
        "research_mean_hits": 1.4,
        "random_mean_ticket_hits": 1.3,
        "champion_ge3": 0,
        "research_ge3": 1,
        "random_ge3_rate": 0.4,
        "champion_ge4": 0,
        "research_ge4": 0,
        "random_ge4_rate": 0.1,
        "champion_score": 2.12,
        "research_score": 3.49,
        "random_mean_score": 2.65,
        "research_delta_vs_champion": 1.37,
        "research_delta_vs_random": 0.84,
    }]
    got = summarize(rows, "abc", 691, 100, 120, 350, 32)
    assert got["evaluated_rounds"] == 1
    assert got["nested_research"]["mean_score"] == 3.49
    assert got["nested_research"]["score_delta_vs_champion"]["mean"] == 1.37
    assert got["random_reference"]["mean_score"] == 2.65
