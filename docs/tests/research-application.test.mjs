import test from "node:test";
import assert from "node:assert/strict";
import {normalizeResearchApplication} from "../telemetry.mjs";

function state(){
  return {
    status:"research_review_ready_only",
    research_mode:"WAIT_FOR_NEW_DATA",
    trusted_result_source:false,
    papers:16,verified_dois:3,proposal_count:2,
    synthetic_control:"passed",
    actual_prediction_accuracy_improvement_verified:false,
    tasks:[
      {topic:"calibration",status:"awaiting_full_text_and_methodology_review",
       requires_human_approval:true,two_provider_matches:1},
      {topic:"anytime_evidence",status:"bibliography_needs_verification",
       requires_human_approval:true,two_provider_matches:0}
    ]
  };
}
test("safely render non-executable research work with a waiting guard",()=>{
  const x=normalizeResearchApplication(state());
  assert.equal(x.status,"research_review_ready_only");
  assert.equal(x.trustedSource,false);
  assert.equal(x.tasks.length,2);
  assert.equal(x.tasks[0].twoProviderMatches,1);
});
test("absence of newly published evidence is not mistaken for success",()=>{
  assert.equal(normalizeResearchApplication(undefined).status,"not_yet_published");
  assert.equal(normalizeResearchApplication({status:"stale_or_unsafe"}).status,"stale_or_unsafe");
});
test("unsupported experiment topic and forged confirmation fail closed",()=>{
  const x=state();x.tasks[0].topic="execute all forecasts";
  assert.equal(normalizeResearchApplication(x).status,"stale_or_unsafe");
  x.tasks[0].topic="calibration";
  x.actual_prediction_accuracy_improvement_verified=true;
  assert.equal(normalizeResearchApplication(x).status,"stale_or_unsafe");
});
test("missing or exaggerated application items cannot render",()=>{
  const x=state();x.proposal_count=5;
  assert.equal(normalizeResearchApplication(x).status,"stale_or_unsafe");
  x.proposal_count=2;x.tasks[1].two_provider_matches=700;
  assert.equal(normalizeResearchApplication(x).status,"stale_or_unsafe");
});
