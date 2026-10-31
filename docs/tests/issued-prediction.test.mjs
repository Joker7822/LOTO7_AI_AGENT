import test from "node:test";
import assert from "node:assert/strict";
import {normalizeIssuedPrediction} from "../telemetry.mjs";

const data=()=>({
  version:"issued-production-forecast-public-v1",
  status:"published",
  target_round:700,
  source_base_round:699,
  draw_date:"2026-10-23",
  published_at_jst:"2026-10-23T14:15:28+09:00",
  model:"baseline-5fdb8dc2ad",
  tickets:[
    [6,16,22,23,24,28,36],[10,18,22,23,24,34,35],
    [10,15,20,22,23,24,36],[6,10,15,16,22,24,34],
    [6,10,15,22,23,24,28]
  ].map((numbers,i)=>({ticket:i+1,numbers})),
  result_status:"awaiting_independently_verified_draw",
  current_result:null,
  latest_verified:{
    round:699,date:"2026-10-16",
    main:[5,6,8,14,15,22,29],bonus:[3,16],
    source_verification:"verified_two_result_sources",
    tickets:[1,2,3,4,5].map(ticket=>({
      ticket,main_hits:ticket===5?2:1,bonus_hits:ticket===1?0:1,grade:"はずれ"
    }))
  },
  exposure:"publicly_issued_production_only",
  no_future_oos_vectors:true,accuracy_claim:false,
});

test("five previously issued production tickets and verified 699 result can display",()=>{
  const p=normalizeIssuedPrediction(data());
  assert.equal(p.status,"published");
  assert.equal(p.targetRound,700);
  assert.equal(p.tickets.length,5);
  assert.deepEqual(p.tickets[0].numbers,[6,16,22,23,24,28,36]);
  assert.equal(p.currentResult,null);
  assert.equal(p.lastVerified.round,699);
  assert.equal(p.lastVerified.tickets[4].mainHits,2);
});
test("missing or unpublished predictions show no publicly exposed numbers",()=>{
  assert.deepEqual(normalizeIssuedPrediction(undefined).tickets,[]);
  assert.deepEqual(normalizeIssuedPrediction({status:"not_published",tickets:[1,2,3]}).tickets,[]);
});
test("reject unauthorized model, untrusted claimed win and extra ticket",()=>{
  const r=data();
  r.exposure="unregistered_future_oos";assert.throws(()=>normalizeIssuedPrediction(r),/整合性/);
  r.exposure="publicly_issued_production_only";r.tickets.push({ticket:6,numbers:[1,2,3,4,5,6,7]});
  assert.throws(()=>normalizeIssuedPrediction(r),/整合性/);
  r.tickets.pop();r.no_future_oos_vectors=false;
  assert.throws(()=>normalizeIssuedPrediction(r),/整合性/);
  r.no_future_oos_vectors=true;r.accuracy_claim=true;
  assert.throws(()=>normalizeIssuedPrediction(r),/整合性/);
});
test("no fake grading when official result not verified",()=>{
  const r=data();
  r.result_status="independently_verified";
  assert.throws(()=>normalizeIssuedPrediction(r),/検証状態/);
});
test("duplicate, unsorted or out-of-range numbers are blocked",()=>{
  const r=data();r.tickets[0].numbers=[1,1,2,3,4,5,6];
  assert.throws(()=>normalizeIssuedPrediction(r),/不正/);
  r.tickets[0].numbers=[0,2,3,4,5,6,7];
  assert.throws(()=>normalizeIssuedPrediction(r),/不正/);
});
test("trusted graded ticket must match issued numbers",()=>{
  const r=data();r.result_status="independently_verified";
  r.current_result={
    round:700,date:"2026-10-23",main:[1,2,3,4,5,6,7],bonus:[8,9],
    tickets:r.tickets.map(t=>({ticket:t.ticket,main_hits:0,bonus_hits:0,grade:"はずれ"}))
  };
  assert.throws(()=>normalizeIssuedPrediction(r),/不一致/);
  for(const t of r.current_result.tickets){
    const numbers=r.tickets[t.ticket-1].numbers;
    t.main_hits=numbers.filter(n=>r.current_result.main.includes(n)).length;
    t.bonus_hits=numbers.filter(n=>r.current_result.bonus.includes(n)).length;
  }
  const p=normalizeIssuedPrediction(r);
  assert.equal(p.currentResult.tickets[0].mainHits,1);
});

test("702+ disjoint35 issued Production label and 35 distinct numbers render",()=>{
  const r=data();
  r.target_round=702;
  r.source_base_round=701;
  r.draw_date="2026-11-06";
  r.published_at_jst="2026-11-06T13:30:00+09:00";
  r.model="baseline-5fdb8dc2ad+production-disjoint35-layout-v1";
  r.tickets=[0,1,2,3,4].map(i=>({
    ticket:i+1,numbers:Array.from({length:7},(_,j)=>i*7+j+1)
  }));
  r.latest_verified=null;
  assert.equal(normalizeIssuedPrediction(r).tickets.length,5);
  r.tickets[1].numbers=[1,9,10,11,12,13,14];
  assert.throws(()=>normalizeIssuedPrediction(r),/重複/);
  r.tickets[1].numbers=[8,9,10,11,12,13,14];
  r.model="baseline-5fdb8dc2ad";
  assert.throws(()=>normalizeIssuedPrediction(r),/配置方式/);
});
