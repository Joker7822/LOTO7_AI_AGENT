from datetime import datetime
import pytest
from production_publication_deadline import check, JST

SOURCE={"status":"ok","verification":"verified_two_result_sources","latest":{"round":704},
        "sources":{"official_schedule":{"round":705,"date":"2026-11-27"}}}

@pytest.mark.parametrize("hour,minute,allowed",[(12,59,False),(13,0,True),(16,58,True),(16,59,True),(17,0,False),(18,0,False)])
def test_deadline(hour,minute,allowed):
    at=datetime(2026,11,27,hour,minute,tzinfo=JST)
    if allowed:
        assert check(SOURCE,at)==705
    else:
        with pytest.raises(RuntimeError):
            check(SOURCE,at)

def test_before_push_buffer_and_wrong_draw_date():
    with pytest.raises(RuntimeError,match="safe push"):
        check(SOURCE,datetime(2026,11,27,16,59,tzinfo=JST),before_push=True)
    with pytest.raises(RuntimeError,match="schedule"):
        check(SOURCE,datetime(2026,12,4,14,tzinfo=JST))
    with pytest.raises(RuntimeError,match="verification"):
        check({**SOURCE,"verification":"degraded"},datetime(2026,11,27,14,tzinfo=JST))

def test_both_publishers_recheck_before_generation_and_push():
    from pathlib import Path
    for name in ("weekly_production_publisher.yml","weekly_production_fallback.yml"):
        w=Path(".github/workflows",name).read_text()
        assert w.index("python production_publication_deadline.py\n") < w.index("python weekly_production_prediction.py")
        assert w.index("git pull --rebase") < w.index("python production_publication_deadline.py --before-push") < w.index("timeout 30s git push")
