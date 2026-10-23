import test from "node:test";
import assert from "node:assert/strict";
import {normalizeResearchPriorities} from "../telemetry.mjs";

function fixture(){
  return {
    status:"audited_research_plan",research_mode:"WAIT_FOR_NEW_DATA",
    source_two_verified:false,total_tasks:2,
    counts:{block:1,watch:1,info:0},promotion_authorized:false,
    tasks:[
      {priority:"block",lane:"source_integrity",owner:"source_verifier",
       title:"2ソース照合待ち",reason:"未検証の実結果",next_step:"公式発表元を確認",
       safe_autonomous_action:"report_only"},
      {priority:"watch",lane:"bibliography",owner:"literature_verifier",
       title:"論文を点検",reason:"未レビュー",next_step:"DOIの書誌情報を検証",
       safe_autonomous_action:"report_only"}
    ],
  };
}

test("missing research queue remains explicitly unavailable",()=>{
  const p=normalizeResearchPriorities(undefined);
  assert.equal(p.status,"not_yet_published");
  assert.deepEqual(p.tasks,[]);
});

test("priority queue stays advisory under WAIT_FOR_NEW_DATA",()=>{
  const p=normalizeResearchPriorities(fixture());
  assert.equal(p.status,"audited_research_plan");
  assert.equal(p.researchMode,"WAIT_FOR_NEW_DATA");
  assert.equal(p.totalTasks,2);
  assert.deepEqual(p.tasks.map(t=>t.priority),["block","watch"]);
  assert.equal(p.sourceTwoVerified,false);
});

test("unsafe or out-of-order tasks are never shown",()=>{
  const p=fixture();p.tasks[0].safe_autonomous_action="execute_pipeline";
  assert.equal(normalizeResearchPriorities(p).status,"stale_or_unsafe");
  p.tasks[0].safe_autonomous_action="report_only";
  p.tasks.reverse();
  assert.equal(normalizeResearchPriorities(p).status,"stale_or_unsafe");
});

test("fabricated counts or model promotion flag are rejected",()=>{
  const p=fixture();p.counts.block=2;
  assert.equal(normalizeResearchPriorities(p).status,"stale_or_unsafe");
  p.counts.block=1;p.promotion_authorized=true;
  assert.equal(normalizeResearchPriorities(p).status,"stale_or_unsafe");
});

test("research texts cannot exceed bounded safe display",()=>{
  const p=fixture();
  p.tasks[0].reason="x".repeat(400);
  assert.equal(normalizeResearchPriorities(p).status,"stale_or_unsafe");
});
