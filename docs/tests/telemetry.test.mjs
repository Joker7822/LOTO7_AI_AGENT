import test from "node:test";
import assert from "node:assert/strict";
import {SNAPSHOT_VERSION, normalizeSnapshot, SERIES_TABS} from "../telemetry.mjs";

const FIXED = new Date("2026-10-18T12:16:00Z");
const snapshot = () => ({
  version:SNAPSHOT_VERSION, source_commit:"a".repeat(40),
  generated_at_jst:"2026-10-18T21:00:00+09:00",
  sources:{source:{latest:{round:699}},holdout:{trusted_draws:7}},
  workflows:[
    {label:"継続研究",health:"ok",status:"completed",conclusion:"success",updated_at:"2026-10-18T12:00:00Z",
     url:"https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/123",recent_failure_count:1},
    {label:"v2 Future OOS",health:"running",status:"in_progress",updated_at:"2026-10-18T12:00:00Z"},
  ],
  series:{
    portfolio:[{round:693,date:"2026-09-04",mean_delta_vs_random:.02,mean_delta_vs_champion:-.02},
      {round:694,date:"2026-09-11",mean_delta_vs_random:-.52,mean_delta_vs_champion:.01}],
    v2:[],adaptive:[]
  }
});

test("same-timestamp snapshot with real prospective portfolio and ungraded v2",()=>{
  const x=normalizeSnapshot(snapshot(),FIXED);
  assert.equal(x.outdated,false);
  assert.equal(x.healthyRuns,1);
  assert.equal(x.series.portfolio.length,2);
  assert.equal(x.series.v2.length,0);
  assert.equal(x.series.adaptive.length,0);
  assert.equal(x.alerts.length,0);
  assert.ok(x.workflows[0].url.endsWith("123"));
  assert.equal(SERIES_TABS[1].choices.length,3);
  assert.equal(SERIES_TABS[2].choices.length,3);
});
test("a failed workflow creates a concrete alert and points to Actions",()=>{
  const x=snapshot();x.workflows[0].health="block";
  const y=normalizeSnapshot(x,FIXED);
  assert.equal(y.alerts.length,1);
  assert.equal(y.alerts[0].severity,"block");
  assert.match(y.alerts[0].url,/actions\/runs\/123/);
});
test("stale monitoring is not silently reported healthy",()=>{
  const y=normalizeSnapshot(snapshot(),new Date("2026-10-19T02:00:00Z"));
  assert.equal(y.outdated,true);
  assert.equal(y.alerts[0].severity,"watch");
});
test("unavailable Actions monitoring is a warning, not a success",()=>{
  const x=snapshot();x.workflows[0].health="unknown";
  const y=normalizeSnapshot(x,FIXED);
  assert.equal(y.workflows[0].status,"未取得");
  assert.equal(y.alerts[0].severity,"watch");
});
test("malformed mixed or invented prospective series is refused",()=>{
  const s=snapshot();s.series.v2=[{round:703},{round:701}];
  assert.throws(()=>normalizeSnapshot(s,FIXED),/回別連続性/);
  const t=snapshot();delete t.series.adaptive;
  assert.throws(()=>normalizeSnapshot(t,FIXED),/時系列データ/);
  const u=snapshot();u.version="unknown";
  assert.throws(()=>normalizeSnapshot(u,FIXED),/形式が不正/);
});
test("untrusted external links cannot be inserted in dashboard DOM",()=>{
  const s=snapshot();s.workflows[0].url="javascript:alert(1)";
  assert.equal(normalizeSnapshot(s,FIXED).workflows[0].url,null);
});
