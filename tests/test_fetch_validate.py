import datetime as dt

from fetch_validate import (
    compare_sources,
    expected_new_round,
    freshness_expected,
    iframe_urls,
    parse_mizuho,
    parse_rakuten_bank,
    validate_row,
)


def test_expected_round_friday_20_jst():
    before = {"回別": "第690回", "抽せん日": "2026-08-14"}
    now = dt.datetime(2026, 8, 21, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    assert expected_new_round(before, now) == (691, "2026-08-21")


def test_production_snapshot_does_not_require_same_day_result():
    before = {"回別": "第690回", "抽せん日": "2026-08-14"}
    now = dt.datetime(2026, 8, 21, 21, 30, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    assert expected_new_round(before, now) == (691, "2026-08-21")
    assert freshness_expected(before, production_snapshot=True, now=now) is None


def test_validate_latest_numbers():
    got = validate_row({
        "回別": "第691回",
        "抽せん日": "2026-08-21",
        "本数字": "01 02 03 04 05 06 07",
        "ボーナス数字": "08 09",
    })
    assert got["round"] == 691 and got["main"][-1] == 7


def synthetic_html():
    return """<html><body>ロト7 第691回 抽せん日 2026年8月21日
    本数字 01 02 03 04 05 06 07 ボーナス数字 08 09 1等</body></html>"""


def test_parse_mizuho_synthetic():
    got = parse_mizuho(synthetic_html(), 691)
    assert got["round"] == 691
    assert got["main"] == [1, 2, 3, 4, 5, 6, 7]
    assert got["bonus"] == [8, 9]


def test_parse_rakuten_bank_synthetic():
    got = parse_rakuten_bank(synthetic_html(), 691)
    assert got["round"] == 691
    assert got["date"] == "2026-08-21"


def test_iframe_urls_are_resolved_and_deduped():
    html = '<iframe src="/a"></iframe><iframe src="https://example.com/b"></iframe><iframe src="/a"></iframe>'
    assert iframe_urls(html, "https://bank.example/root/") == [
        "https://bank.example/a",
        "https://example.com/b",
    ]


def test_rakuten_bank_fallback_can_verify_two_sources():
    primary = {
        "round": 691,
        "date": "2026-08-21",
        "main": [1, 2, 3, 4, 5, 6, 7],
        "bonus": [8, 9],
    }
    sources = {
        "mizuho": {"status": "unavailable"},
        "rakuten_bank": dict(primary),
        "official_schedule": {"round": 692, "date": "2026-08-28"},
    }
    verification, notes = compare_sources(primary, sources)
    assert verification == "verified_two_result_sources"
    assert any("Rakuten Bank" in note for note in notes)


def test_any_secondary_mismatch_fails_closed():
    primary = {
        "round": 691,
        "date": "2026-08-21",
        "main": [1, 2, 3, 4, 5, 6, 7],
        "bonus": [8, 9],
    }
    sources = {
        "mizuho": dict(primary),
        "rakuten_bank": {**primary, "main": [1, 2, 3, 4, 5, 6, 10]},
    }
    verification, _ = compare_sources(primary, sources)
    assert verification == "mismatch"


# Real source-report and CSV bytes are copied into isolated tmpdirs:
# a transient outage can never synthesize draw outcomes or relax source trust.
import hashlib
import json
import shutil
import sys
import urllib.error
from pathlib import Path

import pytest
import fetch_validate as validation


@pytest.fixture()
def cached_wait(tmp_path, monkeypatch):
    csv_path = tmp_path / "loto7.csv"
    report = tmp_path / "source_validation.json"
    guard = tmp_path / "research_cycle_guard.json"
    shutil.copyfile("loto7.csv", csv_path)
    shutil.copyfile("loto7_agent_output/source_validation.json", report)
    before = validation.latest_row(validation.read_rows(csv_path))
    current = validation.validate_row(before)
    saved = json.loads(report.read_text(encoding="utf-8"))
    saved["latest"] = current
    saved["status"] = "degraded"
    saved["verification"] = "degraded_single_result_source"
    report.write_text(json.dumps(saved), encoding="utf-8")
    data_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    guard.write_text(json.dumps({
        "mode": "WAIT_FOR_NEW_DATA", "search_enabled": False,
        "data_sha256": data_sha
    }), encoding="utf-8")
    monkeypatch.setattr(validation, "now_jst", lambda: dt.datetime(
        2026, 10, 22, 9, 0, tzinfo=validation.JST
    ))
    monkeypatch.setattr(sys, "argv", [
        "fetch_validate.py", "--csv", str(csv_path), "--report", str(report),
        "--research-guard", str(guard),
        "--max-attempts", "1", "--interval-seconds", "0",
        "--allow-cached-wait-on-transient-error",
    ])
    return csv_path, report, guard


def fail_http(code):
    def rejected(*args, **kwargs):
        raise urllib.error.HTTPError(
            "https://www.rakuten-bank.co.jp/takarakuji/backnumber/",
            code, "Service Unavailable", {}, None
        )
    return rejected


def test_503_cached_wait_preserves_the_exact_unchanged_science_evidence(cached_wait, monkeypatch, capsys):
    csv, report, _guard = cached_wait
    original_csv, original_report = csv.read_bytes(), report.read_bytes()
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_http(503))
    assert validation.main() == 0
    assert csv.read_bytes() == original_csv
    assert report.read_bytes() == original_report
    assert "[WAIT-CACHE]" in capsys.readouterr().out


def test_503_cached_wait_never_permits_stale_results_after_next_draw_deadline(cached_wait, monkeypatch):
    _csv, report, _guard = cached_wait
    monkeypatch.setattr(validation, "now_jst", lambda: dt.datetime(
        2026, 10, 24, 9, 0, tzinfo=validation.JST
    ))
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_http(503))
    assert validation.main() == 1
    assert json.loads(report.read_text())["status"] == "failed"


def test_503_cached_wait_never_reopens_search_or_accepts_stale_guard_sha(cached_wait, monkeypatch):
    _csv, report, guard = cached_wait
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_http(503))
    original = json.loads(guard.read_text())
    original["mode"] = "SEARCH"
    original["search_enabled"] = True
    guard.write_text(json.dumps(original))
    assert validation.main() == 1
    assert json.loads(report.read_text())["status"] == "failed"


def test_503_cached_wait_blocks_wrong_guard_hash(cached_wait, monkeypatch):
    _csv, report, guard = cached_wait
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_http(503))
    original = json.loads(guard.read_text())
    original["data_sha256"] = "fake"
    guard.write_text(json.dumps(original))
    assert validation.main() == 1
    assert json.loads(report.read_text())["status"] == "failed"


@pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
def test_non_transient_http_errors_do_not_allow_cached_scientific_evidence(cached_wait, monkeypatch, code):
    _csv, report, _guard = cached_wait
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_http(code))
    assert validation.main() == 1
    assert json.loads(report.read_text())["status"] == "failed"


def test_transient_timeout_allows_only_unchanged_registered_wait(cached_wait, monkeypatch):
    csv, report, _guard = cached_wait
    before = csv.read_bytes()
    def timeout(*args, **kwargs):
        raise TimeoutError("source server timed out")
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", timeout)
    assert validation.main() == 0
    assert csv.read_bytes() == before
    assert json.loads(report.read_text())["verification"] == "degraded_single_result_source"


def test_partial_csv_mutation_cannot_be_reused_during_http_outage(cached_wait, monkeypatch):
    csv, report, _guard = cached_wait
    original_bytes = csv.read_bytes()
    def fail_after_change(*args, **kwargs):
        csv.write_bytes(original_bytes + b"tampered")
        raise urllib.error.HTTPError("https://example.com", 503, "unavailable", {}, None)
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_after_change)
    assert validation.main() == 1
    assert json.loads(report.read_text())["status"] == "failed"


def test_friday_result_window_is_never_skipped_on_outage(cached_wait, monkeypatch):
    _csv, report, _guard = cached_wait
    monkeypatch.setattr(validation, "now_jst", lambda: dt.datetime(
        2026, 10, 23, 20, 15, tzinfo=validation.JST
    ))
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_http(503))
    assert validation.main() == 1
    assert json.loads(report.read_text())["freshness_expected"]["round"] == 700


def test_wait_cache_requires_exact_existing_report_numbers(cached_wait, monkeypatch):
    _csv, report, _guard = cached_wait
    item = json.loads(report.read_text())
    item["latest"]["main"] = [1, 2, 3, 4, 5, 6, 7]
    report.write_text(json.dumps(item))
    monkeypatch.setattr(validation.scrapingloto7, "update_loto7_csv", fail_http(503))
    assert validation.main() == 1
    assert json.loads(report.read_text())["status"] == "failed"
