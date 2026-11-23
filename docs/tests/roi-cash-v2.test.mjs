import test from "node:test";
import assert from "node:assert/strict";
import {normalizeIssuedPrediction,normalizeRoiCashV2} from "../telemetry.mjs";

const V2="production-ai-ranked35-roi-cash-v2";
const LEGACY="production-disjoint35-layout-v1";
const sourceSha="9114a6f11003e7cc590e317f50b08da7cfc32cd5dfb1b9779432b032eca87b80";
const cash=()=>({
  version:"dashboard-roi-cash-v2-v1",
  policy:V2,champion:"baseline-5fdb8dc2ad",
  operator_selected:true,
  adoption:"explicit_operator_instruction_not_statistical_promotion",
  new_issuance_from_round:705,next_target_round:705,
  latest_issued_target_round:704,latest_issued_policy:LEGACY,
  latest_issued_v2:false,issuance_status:"selected_not_yet_issued",
  source_verified:true,
  reference:{
    scope:"exploratory_walk_forward_hypothetical_purchases",
    first_round:2,last_round:704,last_draw_date:"2026-11-20",
    draw_count:703,public_data_sha256:sourceSha,same_dataset_as_latest:true,
    ticket_count_per_draw:5,ticket_cost_yen:300,
    total_cost_yen_per_arm:1054500,
    roi_v2_payout_yen:922400,previous_v1_payout_yen:228600,
    rank_order_payout_yen:205500,
    roi_v2_net_yen:-132100,
    roi_v2_without_largest_single_win_yen:217000,
    largest_single_win_yen:705400,largest_single_win_round:118,
    audit_url:"https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/44990515557",
  },
  actual_purchase_receipts_verified:false,actual_purchase_cost_yen:null,
  actual_personal_roi:null,future_cash_roi_improvement_confirmed:false,
  candidate_specific_verified_future_roi:null,
  automatic_purchase_authorized:false,approved_future_roi_promotion_gate_passed:false,
  adoption_pr_url:"https://github.com/Joker7822/LOTO7_AI_AGENT/pull/161",
});
const notIssued={status:"not_published",tickets:[],latestVerified:null,currentResult:null};
const ticketNumbers=[0,1,2,3,4].map(i=>[1,2,3,4,5,6,7].map(n=>n+7*i));
const published=(policy,target)=>({
  version:"issued-production-forecast-public-v1",status:"published",
  target_round:target,source_base_round:target-1,
  draw_date:target===704?"2026-11-20":"2026-11-27",
  published_at_jst:"2026-11-27T13:45:00+09:00",
  model:"baseline-5fdb8dc2ad+"+policy,
  tickets:ticketNumbers.map((numbers,i)=>({ticket:i+1,numbers})),
  result_status:"awaiting_independently_verified_draw",
  current_result:null,latest_verified:null,
  no_future_oos_vectors:true,accuracy_claim:false,
  exposure:"publicly_issued_production_only"
});

test("v2 is the selected next-issuance policy, not a paid or proven future ROI",()=>{
  const x=normalizeRoiCashV2(cash(),704,notIssued);
  assert.equal(x.status,"selected_not_yet_issued");
  assert.equal(x.latestIssuedV2,false);
  assert.equal(x.v2Roi,922400/1054500);
  assert.equal(x.previousRoi,228600/1054500);
  assert.equal(x.v2Net,-132100);
  assert.equal(x.singleWin,705400);
  assert.equal(x.withoutSingleWinRoi,217000/1054500);
  assert.equal(x.futureRoiVerified,false);
  assert.equal(x.personalPurchaseVerified,false);
});

test("valid frozen v2 #705 is displayable without relabeling legacy issue",()=>{
  const issue=normalizeIssuedPrediction(published(V2,705));
  assert.equal(issue.targetRound,705);
  assert.equal(issue.tickets.length,5);
  const record=cash();
  record.latest_issued_policy=V2;
  record.latest_issued_target_round=705;
  record.latest_issued_v2=true;
  record.issuance_status="roi_v2_published";
  const view=normalizeRoiCashV2(record,704,issue);
  assert.equal(view.latestIssuedV2,true);
  assert.equal(view.status,"roi_v2_published");
  const old=normalizeIssuedPrediction(published(LEGACY,704));
  assert.equal(old.model,"baseline-5fdb8dc2ad+"+LEGACY);
  assert.throws(()=>normalizeRoiCashV2(record,704,old),/台帳のモデル識別子/);
});

test("an old v1/pairwise or ranked frozen #705 remains a valid issued forecast",()=>{
  const policies=[
    LEGACY,"production-ai-ranked-disjoint35-layout-v1",
    "production-ai-ranked35-pairwise-combination-v1",V2
  ];
  for(const p of policies)assert.equal(normalizeIssuedPrediction(published(p,705)).targetRound,705);
  assert.throws(()=>normalizeIssuedPrediction(published("forged-portfolio",705)),/配置方式/);
  assert.throws(()=>normalizeIssuedPrediction(published(V2,704)),/配置方式/);
  const tampered=published(V2,705);
  tampered.tickets[1].numbers=tampered.tickets[0].numbers;
  assert.throws(()=>normalizeIssuedPrediction(tampered),/重複/);
});

test("cash data and provenance cannot be forged into a user ROI claim",()=>{
  const cases=[
    o=>{o.reference.public_data_sha256="f".repeat(64);},
    o=>{o.reference.roi_v2_payout_yen=1022400;o.reference.roi_v2_net_yen=-32100;},
    o=>{o.reference.total_cost_yen_per_arm=300;},
    o=>{o.reference.largest_single_win_yen=0;o.reference.roi_v2_without_largest_single_win_yen=922400;},
    o=>{o.actual_personal_roi=2;},
    o=>{o.actual_purchase_receipts_verified=true;},
    o=>{o.automatic_purchase_authorized=true;},
    o=>{o.future_cash_roi_improvement_confirmed=true;},
    o=>{o.approved_future_roi_promotion_gate_passed=true;},
    o=>{o.reference.audit_url="javascript:alert(1)";},
  ];
  for(const change of cases){
    const x=cash();change(x);
    assert.throws(()=>normalizeRoiCashV2(x,704,notIssued),/検証できません/);
  }
});

test("historical cash reference explicitly becomes stale after later draw",()=>{
  const x=cash();
  x.next_target_round=706;
  x.reference.same_dataset_as_latest=false;
  assert.equal(normalizeRoiCashV2(x,705,notIssued).referenceCurrent,false);
  x.reference.same_dataset_as_latest=true;
  assert.throws(()=>normalizeRoiCashV2(x,705,notIssued),/検証できません/);
  assert.equal(normalizeRoiCashV2(null,704,notIssued).status,"unavailable");
});
