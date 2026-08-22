import fetch_validate as fv


def rakuten_public_html():
    return """
    <html><body>
      <h1>ロト7の当せん番号案内</h1>
      <div>第0688回～第0691回</div>
      <table>
        <tr><th>開催回</th><td>第0691回</td></tr>
        <tr><th>抽せん日</th><td>2026/08/21</td></tr>
        <tr><th>本数字</th><td>08-10-20-22-23-27-37</td></tr>
        <tr><th>ボーナス<br>数字</th><td>(02) (09)</td></tr>
        <tr><th>1等</th><td>該当なし</td></tr>
      </table>
    </body></html>
    """


def test_rakuten_public_format_with_hyphens_and_split_bonus_label():
    got = fv.parse_rakuten_bank(rakuten_public_html(), 691)
    assert got == {
        "round": 691,
        "date": "2026-08-21",
        "main": [8, 10, 20, 22, 23, 27, 37],
        "bonus": [2, 9],
    }


def test_direct_public_result_endpoint_is_tried_before_root(monkeypatch):
    called = []

    def fake_get(url, timeout=30):
        called.append(url)
        if url == fv.RAKUTEN_BANK_RESULT_URL:
            return rakuten_public_html()
        raise AssertionError("root fallback should not be needed when direct result page parses")

    monkeypatch.setattr(fv, "http_get", fake_get)
    got = fv.fetch_rakuten_bank_result(691)
    assert got["round"] == 691
    assert got["transport"] == "direct_public_result_page"
    assert called == [fv.RAKUTEN_BANK_RESULT_URL]


def test_direct_result_can_verify_primary_when_mizuho_is_blocked():
    primary = {
        "round": 691,
        "date": "2026-08-21",
        "main": [8, 10, 20, 22, 23, 27, 37],
        "bonus": [2, 9],
    }
    secondary = fv.parse_rakuten_bank(rakuten_public_html(), 691)
    secondary["transport"] = "direct_public_result_page"
    verification, notes = fv.compare_sources(primary, {
        "mizuho": {"status": "unavailable", "error": "403"},
        "rakuten_bank": secondary,
        "official_schedule": {"round": 692, "date": "2026-08-28"},
    })
    assert verification == "verified_two_result_sources"
    assert any("direct_public_result_page" in note for note in notes)
