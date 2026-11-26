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
    # Only the actual #704 prefix can exercise this fixed-clock example.
    current=json.loads((tmp_path/"loto7_agent_output/source_validation.json").read_text())
    if current.get("latest",{}).get("round")!=704:
        return
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


def test_prior_commitments_bind_registration_and_reject_changed_digest(tmp_path):
    pth=tmp_path/p.ARCHIVE
    pth.mkdir(parents=True)
    d={"cash_v2_sha256":"a"*64,"pairwise_v1_sha256":"b"*64,"ranking_sha256":"c"*64,
       "matched_random32_sha256":["d"*64]*32}
    record={"version":p.VERSION,"target_round":705,"base_round":704,"protocol_sha256":"e"*64,
            "production_changed":False,"prediction_skill_confirmed":False,
            "independent_snapshot_audit_passed":False,"digests":d,
            "created_at_jst":"2026-11-26T18:00:00+09:00","draw_date":"2026-11-27"}
    f=pth/"commitment_0705.json"
    f.write_text(json.dumps(record))
    reg={"first_target":705,"last_target":730}
    p.validate_commitments(tmp_path,reg,"e"*64)
    with pytest.raises(ValueError,match="protocol changed"):
        p.validate_commitments(tmp_path,reg,"f"*64)
    record["digests"]["cash_v2_sha256"]="invalid"
    f.write_text(json.dumps(record))
    with pytest.raises(ValueError,match="invalid commitment digest"):
        p.validate_commitments(tmp_path,reg,"e"*64)
