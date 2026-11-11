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


# Next-round schedule recovery uses *only observed published date+round*.
# Synthetic HTML is intentionally isolated from real future evidence.
def test_parse_explicit_rakuten_loto7_703_sales_listing():
    html = """<html><body>ロト(LOTO)購入
      毎週金曜日が抽せん日
      第0703回 2026年11月13日(金) 18:20締切
      ロト7 最高12億円のチャンス
      毎週月・木曜日が抽せん日
      第2154回 2026年11月12日(木) 18:20締切
      毎週火曜日が抽せん日
      第1413回 2026年11月17日(火) 18:20締切</body></html>"""
    result = validation.parse_retailer_next_schedule(html, 703)
    assert result["round"] == 703
    assert result["date"] == "2026-11-13"
    assert result["source_tier"] == "authorized_retailer_sales_listing"
    assert validation.parse_retailer_next_schedule(html, 704) is None


@pytest.mark.parametrize("html", [
    "毎週金曜日が抽せん日 第0702回 2026年11月6日(金)",  # stale round
    "毎週金曜日が抽せん日 第0703回 2026年11月12日(木)",  # not Friday
    "毎週金曜日が抽せん日 第0703回 2026年11月31日(金)",  # nonexistent
    "毎週月・木曜日が抽せん日 第0703回 2026年11月13日(金)",  # wrong lottery
    "毎週金曜日が抽せん日 第0703回 2026年11月13日(金) "
    "毎週金曜日が抽せん日 第0703回 2026年11月20日(金)",  # conflict
    "ロト7の抽せんは毎週金曜日です",  # never compute a date
])
def test_sales_schedule_fail_closed_on_untrusted_or_ambiguous_content(html):
    assert validation.parse_retailer_next_schedule(html, 703) is None


def test_schedule_fallback_retains_explicit_retailer_provenance(monkeypatch):
    called = []
    expected_result = {
        "round": 702, "date": "2026-11-06",
        "main": [1, 5, 11, 14, 16, 30, 36],
        "bonus": [10, 28],
    }
    monkeypatch.setattr(validation, "fetch_rakuten_bank_result",
                        lambda round_number: dict(expected_result))
    def fetch(url):
        called.append(url)
        if url == validation.MIZUHO_URL:
            raise urllib.error.HTTPError(url, 403, "blocked", {}, None)
        if url == validation.OFFICIAL_URL:
            return "<div>javascript-only official calendar</div>"
        if url == validation.RAKUTEN_LOTO_SALES_URL:
            return ("毎週金曜日が抽せん日 "
                    "第0703回 2026年11月13日(金) 18:20締切")
        raise AssertionError("Unexpected schedule or result endpoint: " + url)
    monkeypatch.setattr(validation, "http_get", fetch)
    snapshot = validation.source_snapshot(702)
    assert snapshot["official_schedule"]["round"] == 703
    assert snapshot["official_schedule"]["date"] == "2026-11-13"
    assert snapshot["official_schedule"]["organizer_verified"] is False
    assert snapshot["official_schedule"]["url"] == validation.RAKUTEN_LOTO_SALES_URL
    assert len(snapshot["official_schedule"]["html_text_sha256"]) == 64
    assert snapshot["official_schedule"]["fetched_at_jst"]
    assert validation.OFFICIAL_URL in called
    assert validation.RAKUTEN_LOTO_SALES_URL in called
    verification, notes = validation.compare_sources(expected_result, snapshot)
    assert verification == "verified_two_result_sources"
    assert any("authorized_retailer_sales_listing" in n for n in notes)
    assert not any("official schedule visible" in n for n in notes)


def test_schedule_fallback_never_forges_calendar_from_weekday(monkeypatch):
    expected_result = {"round": 702, "date": "2026-11-06",
                       "main": [1, 5, 11, 14, 16, 30, 36],
                       "bonus": [10, 28]}
    monkeypatch.setattr(validation, "fetch_rakuten_bank_result",
                        lambda _: dict(expected_result))
    def fetch(url):
        if url == validation.MIZUHO_URL:
            raise OSError("bank temporarily unavailable")
        if url == validation.OFFICIAL_URL:
            raise OSError("organizer temporarily unavailable")
        if url == validation.RAKUTEN_LOTO_SALES_URL:
            return "<html>毎週金曜日に抽せんします</html>"
        raise AssertionError(url)
    monkeypatch.setattr(validation, "http_get", fetch)
    snapshot = validation.source_snapshot(702)
    assert snapshot["official_schedule"]["status"] == "unavailable"
    assert "round" not in snapshot["official_schedule"]


def test_authoritative_official_schedule_skips_retailer_fallback(monkeypatch):
    result = {"round": 702, "date": "2026-11-06",
              "main": [1, 5, 11, 14, 16, 30, 36],
              "bonus": [10, 28]}
    monkeypatch.setattr(validation, "fetch_rakuten_bank_result", lambda _: result)
    called = []
    def fetch(url):
        called.append(url)
        if url == validation.MIZUHO_URL:
            raise OSError("bank blocked")
        if url == validation.OFFICIAL_URL:
            return "<div>ロト7（第703回） 抽せん日 2026年11月13日</div>"
        raise AssertionError("Seller must not override valid organizer schedule")
    monkeypatch.setattr(validation, "http_get", fetch)
    snapshot = validation.source_snapshot(702)
    assert snapshot["official_schedule"] == {
        "round": 703, "date": "2026-11-13"}
    assert validation.RAKUTEN_LOTO_SALES_URL not in called
