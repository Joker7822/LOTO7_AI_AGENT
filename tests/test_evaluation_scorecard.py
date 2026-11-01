"""Read-only scorecard must separate scopes and reject untrusted aggregates."""
import json
import shutil
from pathlib import Path

import evaluation_scorecard as scorecard


def copy_reports(tmp_path):
    original = Path("loto7_agent_output")
    for name in scorecard.FILES.values():
        p = original / name
        if p.is_file():
            shutil.copyfile(p, tmp_path / name)
    return tmp_path


def test_published_metrics_are_separate_and_read_only(tmp_path):
    folder = copy_reports(tmp_path)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    s = scorecard.build_scorecard(folder)
    assert s["version"] == scorecard.VERSION
    assert s["prediction_skill_confirmed"] is False
    assert s["historical"]["status"] == "historical_only"
    assert s["random_baseline"]["status"] == "historical_only"
    assert s["reference_payout"]["status"] == "historical_hypothetical_only"
    assert s["reference_payout"]["actual_profit"] is None
    assert s["calibration"]["ece"] is None
    assert s["future_oos"]["confirmed"] is False
    assert s["historical"]["rounds"] == s["random_baseline"]["rounds"]
    assert s["reference_payout"]["tickets"] == s["historical"]["rounds"] * 5
    assert s["random_baseline"]["mean_score_delta"] < 0
    assert "実購入利益ではない" in scorecard.markdown(s)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


def test_reconciliation_sha_mismatch_fails_closed(tmp_path):
    folder = copy_reports(tmp_path)
    p = folder / scorecard.FILES["reconciliation"]
    data = json.loads(p.read_text(encoding="utf-8"))
    data["loto_csv_sha256"] = "0" * 64
    p.write_text(json.dumps(data), encoding="utf-8")
    s = scorecard.build_scorecard(folder)
    assert s["historical"]["status"] == "historical_only"
    assert s["reference_payout"]["status"] == "invalid_evidence"
    assert s["reference_payout"]["actual_profit"] is None


def test_invalid_calibration_state_does_not_turn_into_zero_advantage(tmp_path):
    folder = copy_reports(tmp_path)
    p = folder / scorecard.FILES["calibration"]
    p.write_text(json.dumps({
        "protocol_version": "champion-calibration-oos-v1",
        "promotion_role": "diagnostic_only", "trusted_draws": 28,
        "horizon_trusted_draws": 26,
        "sum_log_delta_vs_uniform": 9999,
        "sum_brier_improvement_vs_uniform": 9999,
    }), encoding="utf-8")
    s = scorecard.build_scorecard(folder)
    assert s["calibration"]["status"] == "invalid_evidence"
    assert s["calibration"]["ece"] is None


def test_missing_reports_have_unavailable_not_invented_values(tmp_path):
    s = scorecard.build_scorecard(tmp_path)
    assert s["historical"]["status"] == "unavailable"
    assert s["random_baseline"]["status"] == "unavailable"
    assert s["calibration"]["status"] == "unavailable"
    assert s["reference_payout"]["status"] == "unavailable"
    assert s["future_oos"]["status"] == "unavailable"
    assert s["prediction_skill_confirmed"] is False
