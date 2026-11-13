"""Static publication recovery contracts; never emit or rewrite predictions."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def test_publisher_has_off_zero_crons_and_guarded_wakeup():
    text = (ROOT / "weekly_production_publisher.yml").read_text(encoding="utf-8")
    assert 'cron: "7 2 * * 5"' in text
    assert 'cron: "13 3 * * 5"' in text
    assert 'cron: "17 4 * * 5"' in text
    assert re.search(r"(?m)^  push:\n    branches: \[main\]", text)
    assert "Pair Context v2 Numeric Diagnostics" in text
    assert "    branches: [main]" in text
    assert 'if [ "${HM}" -ge 2000 ]; then' in text
    assert 'if [ "${HM}" -lt 1300 ]; then' in text
    assert "production_ticket_geometry35.py --verify-canonical" in text
    assert text.count('[ "${GITHUB_EVENT_NAME}" = "push" ]') == 2


def test_fallback_has_independent_off_zero_cron_and_same_cutoff():
    text = (ROOT / "weekly_production_fallback.yml").read_text(encoding="utf-8")
    assert 'cron: "23 5 * * 5"' in text
    assert 'if [ "${HM}" -ge 2000 ]; then' in text
    assert "production_ticket_geometry35.py --verify-canonical" in text


def test_watchdog_cannot_publish_outside_friday_gate_and_uses_canonical_dispatch():
    text = (ROOT / "friday_production_publication_watchdog.yml").read_text(encoding="utf-8")
    for cron in ('37 4 * * 5', '41 5 * * 5', '19 7 * * 5', '11 9 * * 5'):
        assert f'cron: "{cron}"' in text
    assert 'if [ "${DOW}" != "5" ] || [ "${HM}" -lt 1300 ] || [ "${HM}" -ge 2000 ]; then' in text
    assert "git reset --hard FETCH_HEAD" in text
    assert "ALREADY_PUBLISHED" in text
    assert "weekly_production_publisher.yml" in text
    assert "weekly_production_fallback.yml" in text
    assert 'gh workflow run weekly_production_publisher.yml --repo "${GITHUB_REPOSITORY}" --ref main' in text
    assert "python weekly_production_prediction.py" not in text
    assert "git push" not in text
