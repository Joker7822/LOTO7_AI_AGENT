import test from "node:test";
import assert from "node:assert/strict";
import {normalizeScientificValidation} from "../telemetry.mjs";

const valid = () => ({
  status:"verified_diagnostic_only",
  model_family:"four_vs_five_experts",
  history_round_start:640,history_round_end:699,
  original_four_top7:1.4333333333,candidate_five_top7:1.3833333333,
  original_four_log_edge:.00001753,candidate_five_log_edge:-.000026,
  historical_matched_fair_worlds:32,
  historical_selection_adjusted_p_exploratory_only:.4242424,
  historical_paired_block_ci:{low95:-.002,high95:.001,mean_five_minus_four:-.0000435},
  future_draws:0,future_current_e:1,future_max_e:1,
  future_threshold:20,future_threshold_crossed:false,
  future_e_series:[],promotion_eligible:false
});

test("when the lab has not registered, the UI must not fabricate a score",()=>{
  const z=normalizeScientificValidation(undefined);
  assert.equal(z.status,"not_yet_published");
  assert.equal(z.futureDraws,null);
});
test("historical evidence and future neutral e=1 are displayed separately",()=>{
  const x=normalizeScientificValidation(valid());
  assert.equal(x.status,"verified_diagnostic_only");
  assert.equal(x.originalTop7,1.4333333333);
  assert.equal(x.candidateTop7,1.3833333333);
  assert.equal(x.eValue,1);
  assert.equal(x.futureDraws,0);
  assert.deepEqual(x.series,[]);
});
test("real future-only e values require contiguous targets starting at 701",()=>{
  const a=valid();a.futureDraws=2;a.future_current_e=1.08;a.future_max_e=1.2;
  a.future_e_series=[{round:701,e_value:1.2},{round:702,e_value:1.08}];
  const z=normalizeScientificValidation(a);
  assert.equal(z.series.length,2);
  assert.equal(z.series[0].round,701);
  a.future_e_series[1].round=704;
  assert.throws(()=>normalizeScientificValidation(a),/回別整合性/);
});
test("future threshold flag, stale data and auto-promotion cannot be faked",()=>{
  const x=valid();
  x.promotion_eligible=true;
  assert.throws(()=>normalizeScientificValidation(x),/整合性/);
  x.promotion_eligible=false;x.future_max_e=21;
  assert.throws(()=>normalizeScientificValidation(x),/整合性/);
  assert.equal(normalizeScientificValidation({status:"stale_or_mismatched_evidence"}).futureDraws,null);
});
test("unreasonable historical comparison and CI are rejected",()=>{
  const x=valid();x.historical_matched_fair_worlds=10;
  assert.throws(()=>normalizeScientificValidation(x),/整合性/);
  x.historical_matched_fair_worlds=32;
  x.historical_paired_block_ci.low95=.9;
  assert.throws(()=>normalizeScientificValidation(x),/bootstrap/);
});
