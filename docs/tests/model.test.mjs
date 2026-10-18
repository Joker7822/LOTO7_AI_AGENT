import test from "node:test";
import assert from "node:assert/strict";
import {
  SOURCES, ROLE_NAMES, buildView, displayMetric, japaneseDate, percent,
} from "../model.mjs";

const baseline = () => ({
  source: {
    status:"ok", verification:"verified_two_result_sources",
    checked_at_jst:"2026-10-18T10:01:00+09:00",
    latest:{round:699,date:"2026-10-16",main:[5,6,8,14,15,22,29],bonus:[3,16]},
    sources:{official_schedule:{round:700,date:"2026-10-23"}}
  },
  council:{
    overall:"watch", checked_at_jst:"2026-10-18T10:25:00+09:00",
    roles:Object.fromEntries(Object.keys(ROLE_NAMES).map(id => [id,{
      status:id==="oos_risk_officer"?"watch":"ok",
      findings:[{code:id==="oos_risk_officer"?"NO_EARLY_PORTFOLIO_CLAIM":"PASS",level:id==="oos_risk_officer"?"watch":"ok",evidence:"holdout=7/26"}]
    }])),
    handoff_tasks:[{owner:"oos_risk_officer",priority:"watch",issue_code:"NO_EARLY_PORTFOLIO_CLAIM",evidence:"holdout=7/26"}]
  },
  research:{generation:5089,total_research_evaluations:35622,champion_version:"baseline"},
  holdout:{status:"active",trusted_draws:7,horizon_trusted_draws:26},
  signal:{status:"waiting_for_verified_round_700_prefix",trusted_draws:0,horizon_trusted_draws:26,current_target_round:null},
  learning:{status:"waiting_for_verified_round_700_prefix",trusted_draws:0,current_prefrozen_target:null,latest_seen_round:699,descriptive_future_only:{mean_top7_hits:null}},
  champion:{model_version:"baseline-5fdb8dc2ad"},
  production:{published:true,target_round:"第699回",published_at_jst:"2026-10-16T13:54:02+09:00"},
  scout:{evaluated_rounds:60,synthetic_null_p_log_edge:.4462,scout:{mean_top7_hits:1.4333},v2_reference:{mean_top7_hits:1.5833}},
  budget:{mode:"VALIDATION_ONLY",signal_trials_this_data:768,max_signal_trials_per_data:800},
});

const when = new Date("2026-10-18T02:00:00Z");

test("current 699 state is WATCH with honest progressive research and future OOS counters", () => {
  const v=buildView(baseline(),{},when);
  assert.equal(v.state,"watch");
  assert.equal(v.latestRound,699);
  assert.equal(v.sourceVerified,true);
  assert.equal(v.nextRound,700);
  assert.equal(v.competed,undefined);
  assert.deepEqual(v.latestMain,[5,6,8,14,15,22,29]);
  assert.equal(v.completedCheckpoints[0].done,0);
  assert.equal(v.completedCheckpoints[0].target,null);
  assert.equal(v.completedCheckpoints[1].done,0);
  assert.equal(v.completedCheckpoints[2].done,7);
  assert.equal(v.handoffs.length,1);
  assert.equal(v.handoffs[0].priority,"watch");
  assert.equal(v.promotion,false);
  assert.equal(v.production.isCurrent,false);
  assert.equal(v.researchMode,"VALIDATION_ONLY");
  assert.equal(v.historical[2].value,1.5833);
});
test("unverified latest draw is not labeled trusted",()=>{
  const values=baseline();
  values.source.verification="unverified";
  const v=buildView(values,{},when);
  assert.equal(v.state,"block");
  assert.equal(v.sourceVerified,false);
  assert.equal(v.sourceStatus,"照合未完了");
});
test("fetch failure fails visually rather than inventing 0 or showing all-green",()=>{
  const values=baseline();
  delete values.source;
  const v=buildView(values,{source:"HTTP 500"},when);
  assert.equal(v.state,"unknown");
  assert.equal(v.latestRound,null);
  assert.equal(v.sourceStatus,"取得できません");
  assert.ok(v.inconsistencies.length);
  assert.equal(v.handoffs[0].priority,"watch");
});
test("cross-state disagreement raises alert even when component flags claim normal",()=>{
  const values=baseline();
  values.learning.latest_seen_round=700;
  const v=buildView(values,{},when);
  assert.equal(v.state,"block");
  assert.match(v.inconsistencies[0],/一致していません/);
});
test("block from role council cannot be suppressed",()=>{
  const values=baseline();
  values.council.overall="block";
  const v=buildView(values,{},when);
  assert.equal(v.state,"block");
});
test("null future metrics never become a fictitious zero score",()=>{
  const v=buildView(baseline(),{},when);
  assert.equal(v.completedCheckpoints[0].metric,null);
  assert.equal(displayMetric(null),"未確定");
  assert.equal(displayMetric(0),"0.000");
  assert.equal(percent(null,26),0);
  assert.equal(percent(7,26),27);
  assert.equal(percent(30,26),100);
  assert.equal(percent(-2,26),0);
});
test("no secret, ticket, or raw production predictions in public sources",()=>{
  const sourceNames=Object.values(SOURCES);
  assert.ok(!sourceNames.some(name=>/ticket|prediction_|secret|password|registry/i.test(name)));
  const json=JSON.stringify(buildView(baseline(),{},when));
  assert.ok(!json.includes("predicted_numbers"));
  assert.ok(!json.includes("HMAC"));
});
test("date parser avoids incorrect dates and source is public/valid",()=>{
  assert.equal(japaneseDate("2026-10-23"),"2026/10/23");
  assert.equal(japaneseDate("bad"),"未確認");
  assert.equal(japaneseDate(null),"未確認");
});
