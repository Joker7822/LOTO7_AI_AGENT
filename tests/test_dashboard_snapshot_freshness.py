import json
from datetime import datetime, timedelta, timezone
from dashboard_snapshot_freshness import refresh_required


def test_heartbeat_threshold_and_bad_timestamp(tmp_path):
    path = tmp_path / "snapshot.json"
    now = datetime(2026, 11, 26, 6, tzinfo=timezone.utc)
    assert refresh_required(path, now)
    for age, expected in [(0, False), (59, False), (60, True), (180, True), (-6, True)]:
        path.write_text(json.dumps({"version":"loto7-ops-snapshot-v1",
                                    "generated_at_jst":(now-timedelta(minutes=age)).isoformat()}))
        assert refresh_required(path, now) is expected
    for content in ["{}", "not-json", "null",
                    '{"version":"loto7-ops-snapshot-v1","generated_at_jst":"2026-11-26T06:00:00"}']:
        path.write_text(content)
        assert refresh_required(path, now)
