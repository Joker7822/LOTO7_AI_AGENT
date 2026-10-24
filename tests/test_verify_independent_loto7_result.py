"""Independent LOTO7 results: direct response, exact round and source provenance."""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

import fetch_validate as fv
import verify_independent_loto7_result as verify
from joint_set_v2_signal_oos_guard import validate_trusted_source

HTML_700 = """<html><body>
<h1>ロト7 第700回 2026年10月23日(金) 当選結果</h1>
<p>第700回 2026年10月23日(金) の当選番号です。</p>
<div>第700回　2026年10月23日(金)</div>
<table>
<tr><th>当選数字</th><td>02 03 08 12 21 25 26</td></tr>
<tr><th>ボーナス数字</th><td>(13) (34)</td></tr>
<tr><th>2等</th><td>4,926,400円</td></tr>
</table>
<h2>第699回　2026年10月16日</h2>
<div>当選数字 05 06 08 14 15 22 29 ボーナス数字 (03) (16)</div>
</body></html>"""


@pytest.fixture()
def snapshot(tmp_path):
    csv = tmp_path / "loto7.csv"
    report = tmp_path / "source_validation.json"
    # Fixed synthetic round 700: historical regression CI intentionally runs
    # current code against the immutable round-699 reference repository.
    # Tests must NOT depend on whatever draw the checkout currently ends on.
    csv.write_text(
        "抽せん日,本数字,ボーナス数字,回別\n"
        "2026-10-23,02 03 08 12 21 25 26,13 34,第700回\n",
        encoding="utf-8",
    )
    report.write_text(json.dumps({
        "checked_at_jst": "2026-10-24T15:00:00+09:00",
        "status": "degraded", "verification": "degraded_single_result_source",
        "primary_source": "Rakuten backnumber via scrapingloto7.py",
        "latest": {
            "round": 700, "date": "2026-10-23",
            "main": [2, 3, 8, 12, 21, 25, 26], "bonus": [13, 34],
        },
        "sources": {
            "mizuho": {"status": "unavailable"},
            "rakuten_bank": {"status": "unavailable"},
        },
        "notes": [],
    }), encoding="utf-8")
    return csv, report


def test_parse_exact_target_only():
    x = verify.parse_tsushin(HTML_700, 700)
    assert x == {"round": 700, "date": "2026-10-23",
                 "main": [2, 3, 8, 12, 21, 25, 26], "bonus": [13, 34]}
    assert verify.parse_tsushin(HTML_700, 701) is None


def test_parse_no_numbers_from_unlabeled_prediction_block():
    fake = """第700回 2026年10月23日(金) 抽選結果
    予想数字 02 03 08 12 21 25 26 ボーナス数字 13 34"""
    assert verify.parse_tsushin(fake, 700) is None


def test_parse_disallows_wrong_draw_number_count():
    fake = HTML_700.replace("02 03 08 12 21 25 26", "02 03 08 12 21 25")
    assert verify.parse_tsushin(fake, 700) is None


def test_live_response_is_required_no_offline_fabrication(snapshot, monkeypatch):
    csv, report = snapshot
    before_csv, before_report = csv.read_bytes(), report.read_bytes()
    monkeypatch.setattr(fv, "http_get", lambda u: (_ for _ in ()).throw(RuntimeError("HTTP 403")))
    with pytest.raises(RuntimeError, match="403"):
        verify.verify(csv, report)
    assert csv.read_bytes() == before_csv
    assert report.read_bytes() == before_report


def test_full_independent_verification_updates_only_source_report(snapshot, monkeypatch):
    csv, report = snapshot
    first = csv.read_bytes()
    monkeypatch.setattr(fv, "http_get", lambda u: HTML_700)
    result = verify.verify(csv, report)
    assert result["round"] == 700 and result["verification"] == "verified_two_result_sources"
    assert csv.read_bytes() == first
    output = json.loads(report.read_text())
    assert output["status"] == "ok"
    assert output["verification_provenance"]["secondary_official"] is False
    source = output["sources"]["loto7_tsushin"]
    assert source["url"] == "https://loto7.money-plan.net/round/700/"
    assert len(source["response_sha256"]) == 64
    checked = validate_trusted_source(csv, report)
    assert checked["trusted"] is True and "loto7_tsushin" in checked["secondary"]


def test_mismatched_second_source_rejected_without_changes(snapshot, monkeypatch):
    csv, report = snapshot
    original = report.read_bytes()
    monkeypatch.setattr(fv, "http_get", lambda u: HTML_700.replace("21 25 26", "21 25 27"))
    with pytest.raises(ValueError, match="disagrees"):
        verify.verify(csv, report)
    assert report.read_bytes() == original


def test_source_does_not_trust_forged_status(snapshot, monkeypatch):
    csv, report = snapshot
    item = json.loads(report.read_text())
    item["latest"]["main"] = [1, 2, 3, 4, 5, 6, 7]
    report.write_text(json.dumps(item))
    original = report.read_bytes()
    monkeypatch.setattr(fv, "http_get", lambda u: HTML_700)
    with pytest.raises(ValueError, match="CSV differ"):
        verify.verify(csv, report)
    assert report.read_bytes() == original


def test_compare_sources_accepts_live_independent_alternative():
    first = {"round": 700, "date": "2026-10-23",
             "main": [2, 3, 8, 12, 21, 25, 26], "bonus": [13, 34]}
    src = {**first, "url": verify.url_for_round(700),
           "source_tier": "independent_non_official",
           "transport": "direct_independent_publisher_page",
           "response_sha256": "a" * 64,
           "fetched_at_jst": "2026-10-24T15:00:00+09:00"}
    status, notes = fv.compare_sources(first, {
        "mizuho": {"status": "unavailable"},
        "rakuten_bank": {"status": "unavailable"},
        "loto7_tsushin": src,
    })
    assert status == "verified_two_result_sources"
    assert any("non-official" in note for note in notes)
    for key, bad in (
        ("url", "https://untrusted.invalid/round/700/"),
        ("source_tier", "other"),
        ("response_sha256", ""),
    ):
        changed = {**src, key: bad}
        result, _ = fv.compare_sources(first, {"loto7_tsushin": changed})
        assert result == "degraded_single_result_source"
    changed = copy.deepcopy(src)
    changed["bonus"] = [13, 35]
    status, _ = fv.compare_sources(first, {"loto7_tsushin": changed})
    assert status == "mismatch"


def test_backup_publisher_only_fetched_when_bank_pages_not_available(monkeypatch):
    names = []
    monkeypatch.setattr(fv, "http_get", lambda url: """<html>no valid results</html>""")
    monkeypatch.setattr(fv, "fetch_rakuten_bank_result", lambda round_no: {"status": "unavailable"})
    monkeypatch.setattr(verify, "fetch_secondary", lambda round_no: names.append(round_no)
                        or {"status": "unavailable"})
    snapshot = fv.source_snapshot(700)
    assert names == [700]
    assert "loto7_tsushin" in snapshot


def test_bank_result_remains_preferred_over_third_party(monkeypatch):
    names = []
    monkeypatch.setattr(fv, "http_get", lambda url: """<html>no valid results</html>""")
    result = {"round": 700, "date": "2026-10-23",
              "main": [2, 3, 8, 12, 21, 25, 26], "bonus": [13, 34]}
    monkeypatch.setattr(fv, "fetch_rakuten_bank_result", lambda round_no: result)
    monkeypatch.setattr(verify, "fetch_secondary", lambda round_no: names.append(round_no))
    snapshot = fv.source_snapshot(700)
    assert names == []
    assert snapshot["rakuten_bank"]["round"] == 700
