import datetime as dt

from fetch_validate import (
    compare_sources,
    expected_new_round,
    iframe_urls,
    parse_mizuho,
    parse_rakuten_bank,
    validate_row,
)


def test_expected_round_friday_20_jst():
    before = {"回別": "第690回", "抽せん日": "2026-08-14"}
    now = dt.datetime(2026, 8, 21, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    assert expected_new_round(before, now) == (691, "2026-08-21")


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
