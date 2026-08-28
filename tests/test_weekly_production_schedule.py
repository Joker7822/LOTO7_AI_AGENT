from pathlib import Path

import weekly_production_prediction as weekly


def test_weekly_prediction_cron_is_friday_15_jst():
    text = Path(".github/workflows/continuous_loto7_v4.yml").read_text(encoding="utf-8")
    assert '- cron: "0 6 * * 5"' in text
    assert "weekly_production_prediction.py" in text
    assert "research_v4_no_production.py" in text


def test_render_latest_prediction_has_expected_fields():
    state = {
        "target_round": "第693回",
        "latest_round": "第692回",
        "latest_draw_date": "2026-08-28",
        "model_version": "baseline-test",
    }
    text = weekly.render_latest_prediction(
        state,
        [
            "01 02 03 04 05 06 07",
            "08 09 10 11 12 13 14",
            "15 16 17 18 19 20 21",
            "22 23 24 25 26 27 28",
            "29 30 31 32 33 34 35",
        ],
        "2026-09-04T15:00:00+09:00",
    )
    assert "対象回: 第693回" in text
    assert "予測基準: 第692回 / 2026-08-28" in text
    assert "予測作成(JST): 2026-09-04T15:00:00+09:00" in text
    assert "モデル: baseline-test" in text
    assert "5. 29 30 31 32 33 34 35" in text


def test_current_frozen_production_is_preserved(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "agent_state.json").write_text(
        '{"model_version":"baseline-test","data_sha256":"sha-a"}',
        encoding="utf-8",
    )
    (out / "candidate_tickets.csv").write_text("ticket,numbers\n", encoding="utf-8")
    (out / "latest_prediction.txt").write_text("frozen", encoding="utf-8")
    assert weekly.current_production_is_frozen_and_current(out, "sha-a", "baseline-test") is True
    assert weekly.current_production_is_frozen_and_current(out, "sha-b", "baseline-test") is False
