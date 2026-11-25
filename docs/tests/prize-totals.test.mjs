import test from "node:test";
import assert from "node:assert/strict";
import {normalizePrizeTotals} from "../telemetry.mjs";
test("v2 history cannot be confused with legacy replay; live dates are validated",()=>{
  const h={scope:"historical_roi_cash_v2",model:"production-ai-ranked35-roi-cash-v2",status:"verified",actual_purchase_verified:false,rounds:703,tickets:3515,winning_tickets:147,grade_counts:{"1等":0,"2等":0,"3等":1,"4等":4,"5等":52,"6等":90,"はずれ":3368},reference_cost_yen:1054500,reference_payout_yen:922400,reference_roi:922400/1054500,excluded_rounds:0,pending_rounds:0,first_round:2,last_round:704,first_draw_date:"2013-04-12",last_draw_date:"2026-11-20",artifact_id:14742025156,ticket_csv_sha256:"da3ae04a601aec74d1ad7b27d08e6ca3ff9408feee3bed877ddc546fc896c030",audit_url:"https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/44990515557"};
  const date={round:692,draw_date:"2026-08-28",created_at_jst:"2026-08-21T20:19:21+09:00"};
  const live={scope:"issued_production",status:"verified",actual_purchase_verified:false,rounds:1,tickets:5,winning_tickets:1,grade_counts:{"1等":0,"2等":0,"3等":0,"4等":0,"5等":0,"6等":1,"はずれ":4},reference_cost_yen:1500,reference_payout_yen:1100,reference_roi:1100/1500,excluded_rounds:0,pending_rounds:0,first_settled:date,last_settled:date};
  const raw={version:"dashboard-prize-totals-v2",historical:h,live};
  assert.equal(normalizePrizeTotals(raw).historical.winning_tickets,147);
  assert.equal(normalizePrizeTotals(raw).live.first_settled.round,692);
  assert.equal(normalizePrizeTotals({...raw,historical:{...h,scope:"historical_replay"}}).historical.status,"unavailable");
  assert.equal(normalizePrizeTotals({...raw,live:{...live,first_settled:null}}).live.status,"unavailable");
  assert.equal(normalizePrizeTotals({...raw,live:{...live,reference_roi:1}}).live.status,"unavailable");
  assert.equal(normalizePrizeTotals(undefined).historical.status,"unavailable");
});
