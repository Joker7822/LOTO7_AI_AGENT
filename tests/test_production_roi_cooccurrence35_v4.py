"""Operator v4 adoption: exact algorithm, provenance, no retroactive rewrite."""
import json
from dataclasses import asdict
import pytest
import audit_ledger as ledger
import loto7_v2_runner as v2
import production_disjoint35_policy as policy
import production_ticket_geometry35 as geometry
import weekly_production_prediction as weekly
from loto7_evolving_agent import fingerprint_file
from production_roi_cooccurrence35_v4 import candidate_from_canonical_rows,SELECTION_AUTHORITY
from test_production_roi_cash35_v2 import _history,_configure,_issued_tickets


def prepare(tmp_path,monkeypatch):
    data=tmp_path/"data.csv"
    h=_history(data,n=705)
    _configure(monkeypatch)
    out=tmp_path/"out"
    cfg=v2.DEFAULT_CHAMPION
    state=geometry.prepare_new_production_outputs(csv_path=data,out_dir=out,champion_version=cfg.version(),data_sha=fingerprint_file(data),latest_round=705,target_round=706,latest_draw_date="2026-11-27",git_sha="test",source_path=out/"source_validation.json",history=h,champion_config=cfg)
    return data,out,state


def test_policy_boundary_and_v2_history():
    assert policy.publication_policy_for_target(705)==policy.ROI_CASH_VERSION
    assert policy.publication_policy_for_target(706)==policy.ROI_COOCCURRENCE_VERSION
    for version,round_no in [(policy.ROI_CASH_VERSION,705),(policy.ROI_COOCCURRENCE_VERSION,706)]:
        rows=[{"ticket":i,"model_version":"baseline+"+version,"predicted_numbers":" ".join(map(str,range(7*i-6,7*i+1)))} for i in range(1,6)]
        policy.validate_issued_rows(rows,round_no)
    with pytest.raises(ValueError):
        policy.validate_issued_rows(rows,705)


def test_v4_matches_research_and_audit_rejects_forgery(tmp_path,monkeypatch):
    data,out,state=prepare(tmp_path,monkeypatch)
    canon=ledger.read_csv(data)
    tickets,meta=candidate_from_canonical_rows(canon,state["production_rank_order"])
    assert tickets==_issued_tickets(out)
    assert state["production_roi_cooccurrence_v4_selection_authority"]==SELECTION_AUTHORITY
    assert state["production_roi_prediction_skill_confirmed"] is False
    assert state["production_roi_cooccurrence_v4_diagnostics"]==meta
    rows=ledger.read_csv(out/"candidate_tickets.csv")
    for key,value in [("production_roi_cooccurrence_v4_layout_sha256","bad"),("production_roi_cooccurrence_v4_target_outcome_used",True),("production_purchase_automation",True),("production_roi_prediction_skill_confirmed",True)]:
        with pytest.raises(RuntimeError,match="refusing ROI v4"):
            ledger.append_current_predictions(canon,rows,out/"predictions.csv",{**state,key:value},current_data_sha=fingerprint_file(data))
        assert not (out/"predictions.csv").exists()
    assert ledger.append_current_predictions(canon,rows,out/"predictions.csv",state,current_data_sha=fingerprint_file(data))==5
    before=(out/"predictions.csv").read_bytes()
    assert ledger.append_current_predictions(canon,rows,out/"predictions.csv",state,current_data_sha=fingerprint_file(data))==0
    assert (out/"predictions.csv").read_bytes()==before


def test_weekly_v4_publish_and_republish(tmp_path,monkeypatch):
    data=tmp_path/"history.csv"
    _history(data,n=705)
    _configure(monkeypatch)
    out=tmp_path/"out"
    cfg=v2.DEFAULT_CHAMPION
    champion=tmp_path/"model.json"
    champion.write_text(json.dumps({"model_version":cfg.version(),"config":asdict(cfg)}))
    first=weekly.publish(csv_path=data,out_dir=out,champion_file=champion,research_state=tmp_path/"missing.json")
    assert first["target_round"]=="第706回"
    assert first["ticket_policy"]==policy.ROI_COOCCURRENCE_VERSION
    assert first["production_promotion_method"]=="explicit_operator_policy_switch_without_proven_future_roi"
    assert geometry.verify_canonical_publication(out)["status"]=="disjoint35_pass"
    before=(out/"predictions.csv").read_bytes()
    monkeypatch.setattr(geometry,"prepare_new_production_outputs",lambda **kw:(_ for _ in ()).throw(AssertionError("retrained frozen target")))
    second=weekly.publish(csv_path=data,out_dir=out,champion_file=champion,research_state=tmp_path/"missing.json")
    assert second["ticket_policy"]==first["ticket_policy"]
    assert second["production_promotion_method"]==first["production_promotion_method"]
    assert (out/"predictions.csv").read_bytes()==before
