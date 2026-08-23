from __future__ import annotations

import model_history_reconcile as mhr
import loto7_v2_runner as v2


def cfg(name: str = "research") -> v2.ModelConfig:
    return v2.ModelConfig(
        name=name,
        eta=1.2,
        decay=0.994,
        expert_uniform_mix=0.12,
        final_uniform_mix=0.20,
        overlap_penalty=0.80,
    )


def test_report_key_changes_with_model_and_data():
    a = mhr.report_key("sha-a", cfg("a"), 100, 350)
    assert a != mhr.report_key("sha-b", cfg("a"), 100, 350)
    assert a != mhr.report_key("sha-a", cfg("b"), 100, 350)


def test_is_fresh_requires_exact_report_key():
    state = {"report_version": mhr.REPORT_VERSION, "report_key": "abc"}
    assert mhr.is_fresh(state, "abc")
    assert not mhr.is_fresh(state, "def")
    assert not mhr.is_fresh({"report_version": "old", "report_key": "abc"}, "abc")


def test_accepted_model_prefers_feedback_parent():
    fb = {"accepted_parent_config": cfg("feedback").__dict__}
    rs = {"research_parent_config": cfg("research-state").__dict__}
    got = mhr.accepted_model(fb, rs)
    assert got.name == "feedback"


def test_full_text_contains_round_ticket_actual_and_grade():
    summary = {
        "generated_at_jst": "2026-08-24T06:00:00+09:00",
        "model_version": "research-v1",
        "config": cfg().__dict__,
        "evaluated_rounds": 1,
        "evaluated_tickets": 5,
        "first_round": 691,
        "last_round": 691,
        "mean_top7_hits": 2.0,
        "mean_portfolio_max_hits": 3.0,
        "mean_portfolio_score": 3.2,
        "ge3_round_rate": 1.0,
        "ge4_round_rate": 0.0,
        "winning_tickets": 1,
        "winning_ticket_rate": 0.2,
        "grade_counts": {"6等": 1, "はずれ": 4},
        "purchase_cost_yen": 1500,
        "published_reference_payout_yen": 1000,
        "published_reference_net_yen": -500,
        "published_reference_roi": 2 / 3,
        "unknown_payout_rows": 0,
    }
    rounds = [{
        "base_round": 690,
        "target_round": 691,
        "draw_date": "2026-08-21",
        "training_rows": 690,
        "top7": "08 10 20 22 23 27 35",
        "top7_hits": 6,
        "actual_main": "08 10 20 22 23 27 37",
        "actual_bonus": "02 09",
        "portfolio_score": 3.2,
        "portfolio_max_hits": 3,
        "tickets": [{
            "ticket": 1,
            "predicted_numbers": "08 10 20 22 23 27 35",
            "main_hits": 6,
            "bonus_hits": 0,
            "grade": "2等",
            "published_prize_amount": "1,000,000円",
        }],
    }]
    text = mhr.render_full_text(summary, rounds, "data-sha")
    assert "第691回" in text
    assert "実本数字: 08 10 20 22 23 27 37" in text
    assert "本6 / B0" in text
    assert "2等" in text
    assert "Research評価" in text


def test_safe_filename_removes_path_characters():
    assert "/" not in mhr.safe_filename("model/a:b")
