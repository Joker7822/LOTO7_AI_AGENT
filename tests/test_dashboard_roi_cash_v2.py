"""ROI v2 dashboard projection exposes only audited metadata and old-model truths."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from dashboard_roi_cash_v2 import (
    AUDITED_SOURCE_SHA256, AUDITED_DRAW_COUNT, AUDITED_LAST_ROUND,
    COST_PER_DRAW_YEN, ROI_CASH_VERSION, VERSION, project_roi_cash_v2
)

def project(tmp_path: Path) -> Path:
    root=tmp_path/"view"
    root.mkdir()
    (root/"loto7.csv").write_bytes(Path("loto7.csv").read_bytes())
    return root

def sources(round_number=704,verified=True):
    return {
        "source":{
            "status":"ok" if verified else "pending",
            "verification":"verified_two_result_sources" if verified else "unverified",
            "latest":{"round":round_number}
        },
        "champion":{"model_version":"baseline-5fdb8dc2ad"},
    }

def issued(version="production-disjoint35-layout-v1",target=704):
    return {"status":"published","target_round":target,
            "model":"baseline-5fdb8dc2ad+"+version}

def test_both_roi_arms_reproduce_fixed_audited_cashflow(tmp_path):
    root=project(tmp_path)
    view=project_roi_cash_v2(root,sources(),issued())
    ref=view["reference"]
    assert view["version"]==VERSION
    assert view["policy"]==ROI_CASH_VERSION
    assert view["next_target_round"]==705
    assert view["operator_selected"] is True
    assert view["issuance_status"]=="selected_not_yet_issued"
    assert view["latest_issued_v2"] is False
    assert view["latest_issued_policy"]=="production-disjoint35-layout-v1"
    assert ref["draw_count"]==AUDITED_DRAW_COUNT==703
    assert ref["last_round"]==AUDITED_LAST_ROUND==704
    assert ref["total_cost_yen_per_arm"]==AUDITED_DRAW_COUNT*COST_PER_DRAW_YEN==1054500
    assert ref["roi_v2_payout_yen"]==922400
    assert ref["previous_v1_payout_yen"]==228600
    assert ref["roi_v2_net_yen"]==-132100
    assert ref["largest_single_win_yen"]==705400
    assert ref["roi_v2_without_largest_single_win_yen"]==217000
    assert ref["public_data_sha256"]==AUDITED_SOURCE_SHA256
    assert ref["same_dataset_as_latest"] is True
    assert view["actual_personal_roi"] is None
    assert view["actual_purchase_receipts_verified"] is False
    assert view["future_cash_roi_improvement_confirmed"] is False
    assert view["candidate_specific_verified_future_roi"] is None
    assert view["automatic_purchase_authorized"] is False


def test_new_issued_v2_is_labelled_only_if_ledger_actually_issued_it(tmp_path):
    root=project(tmp_path)
    new=project_roi_cash_v2(root,sources(),issued(ROI_CASH_VERSION,705))
    assert new["issuance_status"]=="roi_v2_published"
    assert new["latest_issued_v2"] is True
    # Previously frozen pairwise model 705 must not be rewritten/rebranded.
    old=project_roi_cash_v2(root,sources(),issued("production-ai-ranked35-pairwise-combination-v1",705))
    assert old["issuance_status"]=="selected_not_yet_issued"
    assert old["latest_issued_v2"] is False
    assert old["latest_issued_policy"]=="production-ai-ranked35-pairwise-combination-v1"


def test_modified_or_new_lottery_data_flags_reference_as_older_not_live(tmp_path):
    root=project(tmp_path)
    source=root/"loto7.csv"
    source.write_bytes(source.read_bytes()+b"\n")
    view=project_roi_cash_v2(root,sources(),issued())
    assert view["reference"]["same_dataset_as_latest"] is False
    assert view["reference"]["last_round"]==704
    view=project_roi_cash_v2(root,sources(705),issued(ROI_CASH_VERSION,705))
    assert view["reference"]["same_dataset_as_latest"] is False
    assert view["next_target_round"]==706


def test_unverified_draw_never_claims_current_good_reference(tmp_path):
    root=project(tmp_path)
    view=project_roi_cash_v2(root,sources(verified=False),issued())
    assert view["source_verified"] is False
    assert view["issuance_status"]=="source_unverified"
    assert view["reference"]["same_dataset_as_latest"] is False


def test_source_and_champion_identity_fail_closed(tmp_path):
    root=project(tmp_path)
    bad=sources()
    bad["source"]["latest"]["round"]=None
    with pytest.raises(ValueError,match="current draw"):
        project_roi_cash_v2(root,bad,issued())
    bad=sources()
    bad["champion"]["model_version"]="unverified-champion"
    with pytest.raises(ValueError,match="Champion"):
        project_roi_cash_v2(root,bad,issued())
    with pytest.raises(ValueError,match="malformed issued"):
        project_roi_cash_v2(root,sources(),{"status":"published","model":"?"})


def test_projection_is_stable_and_read_only(tmp_path):
    root=project(tmp_path)
    before=hashlib.sha256((root/"loto7.csv").read_bytes()).hexdigest()
    first=project_roi_cash_v2(root,sources(),issued())
    assert first==project_roi_cash_v2(root,sources(),issued())
    assert hashlib.sha256((root/"loto7.csv").read_bytes()).hexdigest()==before
    assert "tickets" not in first
    assert "password" not in str(first)
    assert "prediction" not in str(first["reference"])
