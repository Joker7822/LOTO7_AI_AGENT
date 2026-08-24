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


def base_summary() -> dict:
    return {
        "generated_at_jst": "2026-08-24T06:00:00+09:00",
        "model_version": "research-v1",
        "config": cfg().__dict__,
        "evaluated_rounds": 2,
        "evaluated_tickets": 10,
        "first_round": 690,
        "last_round": 691,
        "mean_top7_hits": 2.0,
        "mean_portfolio_max_hits": 3.0,
        "mean_portfolio_score": 3.2,
        "ge3_round_rate": 0.5,
        "ge4_round_rate": 0.0,
        "winning_tickets": 1,
        "winning_ticket_rate": 0.1,
        "grade_counts": {"6等": 1, "はずれ": 9},
        "purchase_cost_yen": 3000,
        "published_reference_payout_yen": 1000,
        "published_reference_net_yen": -2000,
        "published_reference_roi": 1 / 3,
        "unknown_payout_rows": 0,
    }


def winning_round() -> dict:
    return {
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
    }


def all_loss_round() -> dict:
    return {
        "base_round": 689,
        "target_round": 690,
        "draw_date": "2026-08-14",
        "training_rows": 689,
        "top7": "01 02 03 04 05 06 07",
        "top7_hits": 0,
        "actual_main": "08 10 20 22 23 27 37",
        "actual_bonus": "02 09",
        "portfolio_score": 1.0,
        "portfolio_max_hits": 2,
        "tickets": [
            {
                "ticket": i,
                "predicted_numbers": "01 02 03 04 05 06 07",
                "main_hits": 0,
                "bonus_hits": 0,
                "grade": "はずれ",
                "published_prize_amount": "0円",
            }
            for i in range(1, 6)
        ],
    }


def test_full_text_contains_round_ticket_actual_and_grade():
    text = mhr.render_full_text(base_summary(), [winning_round()], "data-sha")
    assert "第691回  抽せん日:" in text
    assert "実本数字: 08 10 20 22 23 27 37" in text
    assert "本6 / B0" in text
    assert "2等" in text
    assert "Research評価" in text


def test_full_text_omits_round_when_all_five_tickets_lose():
    loss = all_loss_round()
    win = winning_round()
    assert not mhr.round_has_prize(loss)
    assert mhr.round_has_prize(win)

    text = mhr.render_full_text(base_summary(), [loss, win], "data-sha")
    assert "第690回  抽せん日:" not in text
    assert "第691回  抽せん日:" in text
    assert "5口全外れ回は非掲載" in text
    assert "回別掲載: 1回" in text


def test_full_text_reports_when_no_round_is_publishable():
    text = mhr.render_full_text(base_summary(), [all_loss_round()], "data-sha")
    assert "第690回  抽せん日:" not in text
    assert "当選回なし（5口全外れ回は非掲載）" in text


def test_safe_filename_removes_path_characters():
    assert "/" not in mhr.safe_filename("model/a:b")
