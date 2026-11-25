import test from "node:test";
import assert from "node:assert/strict";
import {normalizePrizeTotals} from "../telemetry.mjs";
test("prize totals stay separated; inconsistent counts or payout rejected",()=>{
  const h={scope:"historical_replay",status:"verified",actual_purchase_verified:false,rounds:1,tickets:5,winning_tickets:1,grade_counts:{"1等":0,"2等":0,"3等":0,"4等":0,"5等":0,"6等":1,"はずれ":4},reference_cost_yen:1500,reference_payout_yen:1100,reference_roi:1100/1500,excluded_rounds:0,pending_rounds:0};
  const raw={version:"dashboard-prize-totals-v1",historical:h,live:{...h,scope:"issued_production"}};
  assert.equal(normalizePrizeTotals(raw).historical.reference_payout_yen,1100);
  raw.live.reference_roi=1;
  assert.equal(normalizePrizeTotals(raw).live.status,"unavailable");
  assert.equal(normalizePrizeTotals(undefined).historical.status,"unavailable");
});
