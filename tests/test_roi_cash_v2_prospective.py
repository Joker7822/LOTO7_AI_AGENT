from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import pytest
import research.roi_cash_v2_prospective as p


def test_registration_pins_current_algorithms():
    reg=p.protocol(Path("."))
    assert reg["first_target"]==705 and reg["last_target"]==730
    assert reg["independent_receipt_required"] is True


def test_hashes_preserve_same_35_and_do_not_expose_vectors():
    ranking=list(range(1,38))
    tickets=[ranking[i:i+7] for i in range(0,35,7)]
    assert len(p.hash_portfolios(tickets,ranking))==64
    bad=[list(x) for x in tickets]
    bad[-1][-1]=37
    with pytest.raises(ValueError):
        p.hash_portfolios(bad,ranking)


def test_actual_prefix_freeze_is_additive_and_before_cutoff(tmp_path):
    root=Path(".")
    reg=p.protocol(root)
    for path in [*reg["algorithm_git_blob_sha1"], str(p.REGISTRATION),
                 "loto7.csv","loto7_agent_output/source_validation.json",
                 "loto7_agent_output/model_champion.json"]:
        dest=tmp_path/path
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/path,dest)
    import os
    from unittest.mock import patch
    with patch.dict(os.environ,{"GITHUB_ACTIONS":"false"}):
        result=p.freeze(tmp_path,now=datetime(2026,11,26,9,tzinfo=timezone.utc),
                        run_id="123",source_commit="a"*40)
        # The frozen historical CI fixture, or an advanced live source, must
        # not manufacture a target 705 freeze from an unrelated history.
        if result["status"]!="hash_commitment_created":
            assert result["status"] in {"outside_fixed_horizon","awaiting_verified_source",
                                       "awaiting_explicit_schedule","cutoff_passed_no_backfill"}
            return
        assert result["target_round"]==705
        path=Path(result["file"])
        before=path.read_bytes()
        record=json.loads(before)
        assert record["independent_snapshot_audit_passed"] is False
        assert record["production_changed"] is False
        assert len(record["digests"]["matched_random32_sha256"])==32
        assert set(record["digests"])=={"cash_v2_sha256","pairwise_v1_sha256","matched_random32_sha256","ranking_sha256"}
        assert p.freeze(tmp_path,now=datetime(2026,11,27,9,tzinfo=timezone.utc),
                        run_id="124",source_commit="b"*40)["status"]=="already_committed"
        assert path.read_bytes()==before
        path.unlink()
        assert p.freeze(tmp_path,now=datetime(2026,11,27,9,tzinfo=timezone.utc),
                        run_id="124",source_commit="b"*40)["status"]=="cutoff_passed_no_backfill"
        assert not path.exists()
