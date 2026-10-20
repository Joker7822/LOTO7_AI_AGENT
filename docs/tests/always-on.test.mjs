import test from "node:test";
import assert from "node:assert/strict";
import {normalizeAlwaysOnActivity} from "../telemetry.mjs";

const NOW=new Date("2026-10-20T02:00:00Z");
const state=()=>({
  status:"active_bounded_research",sequence:5,
  last_activity_jst:"2026-10-20T10:17:00+09:00",
  current_activity:"オンライン文献調査",
  current_phase:"literature_search",
  online_search_status:"searched",research_mode:"VALIDATION_ONLY",
  promotion_authorized:false,review_notes:["過剰適合を避ける"],
  papers:[{title:"Sequential calibration methods",url:"https://doi.org/10.1234/prob.12",year:2026,review_status:"unreviewed"}]
});
test("fresh hourly online research is visible but explicitly unreviewed",()=>{
  const s=normalizeAlwaysOnActivity(state(),NOW);
  assert.equal(s.status,"active_bounded_research");
  assert.equal(s.stale,false);
  assert.equal(s.sequence,5);
  assert.equal(s.papers[0].reviewStatus,"unreviewed");
  assert.equal(s.researchMode,"VALIDATION_ONLY");
});
test("stale hourly activities flag failed automation without inventing research",()=>{
  const s=normalizeAlwaysOnActivity(state(),new Date("2026-10-21T02:00:00Z"));
  assert.equal(s.stale,true);
  assert.equal(normalizeAlwaysOnActivity(undefined).status,"not_yet_started");
});
test("model promotion or unknown schema is not accepted as research telemetry",()=>{
  const s=state();s.promotion_authorized=true;
  assert.equal(normalizeAlwaysOnActivity(s,NOW).status,"invalid_or_unsafe");
  s.promotion_authorized=false;s.sequence=-7;
  assert.equal(normalizeAlwaysOnActivity(s,NOW).status,"invalid_or_unsafe");
});
test("malicious external research links never appear in browser",()=>{
  const s=state();s.papers[0].url="javascript:alert(1)";
  assert.equal(normalizeAlwaysOnActivity(s,NOW).papers.length,0);
  s.papers[0].url="https://untrusted-host.com/10.1234/prob.12";
  assert.equal(normalizeAlwaysOnActivity(s,NOW).papers.length,0);
  s.papers[0].url="https://doi.org/10.1234/prob.12";
  assert.equal(normalizeAlwaysOnActivity(s,NOW).papers.length,1);
});
test("online outage is visibly differentiated from successful discovery",()=>{
  const s=state();s.status="online_unavailable";s.online_search_status="unavailable:TimeoutError";
  const x=normalizeAlwaysOnActivity(s,NOW);
  assert.equal(x.status,"online_unavailable");
  assert.match(x.searchStatus,/unavailable/);
});
