import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {predictionTabFromHash,predictionTabView} from "../prediction-tabs.mjs";
import {normalizeSnapshot} from "../telemetry.mjs";
import {buildView} from "../model.mjs";
const html=readFileSync(new URL("../index.html",import.meta.url),"utf8");
const app=readFileSync(new URL("../app.js",import.meta.url),"utf8");
const snapshot=JSON.parse(readFileSync(new URL("../data/dashboard_snapshot.json",import.meta.url),"utf8"));
test("two accessible panels use distinct history and live content",()=>{
  for(const name of ["history","live"]){
    assert.match(html,new RegExp('role="tab" id="prediction-tab-'+name+'" aria-controls="prediction-panel-'+name+'"'));
    assert.match(html,new RegExp('id="prediction-panel-'+name+'" role="tabpanel" aria-labelledby="prediction-tab-'+name+'"'));
  }
  const historical=html.slice(html.indexOf('id="prediction-panel-history"'),html.indexOf('id="prediction-panel-live"'));
  assert.match(historical,/id="history-tab-rounds"/);
  assert.match(historical,/44990515557\/artifacts\/14742025156/);
  assert.doesNotMatch(historical,/id="issued-ticket-grid"/);
  assert.match(app,/panel.hidden=!selected/);
  assert.match(app,/ArrowLeft/);
  assert.match(app,/renderPredictionTabs\(null,null\)/);
});
test("deep links select the correct tab",()=>{
  assert.equal(predictionTabFromHash("#roi-v2"),"history");
  assert.equal(predictionTabFromHash("#issued-predictions"),"live");
  assert.equal(predictionTabFromHash("#operations"),null);
});
test("actual snapshot metrics are rendered only as historical aggregate diagnostics",()=>{
  const now=new Date(snapshot.generated_at_jst),ops=normalizeSnapshot(snapshot,now);
  const view=buildView(ops.sources,{},now),result=predictionTabView(ops,view);
  assert.equal(result["history-tab-rounds"],ops.roiCashV2.rounds.toLocaleString("ja-JP")+"回");
  assert.match(result["history-tab-period"],/ROI Cash v2/);
  assert.equal(result["history-tab-roi"],"87.47%");
});
test("previous issue cannot masquerade as next live forecast; stale and missing fail closed",()=>{
  const ops={outdated:false,issuedPrediction:{status:"published",targetRound:704}};
  const view={nextRound:705,nextDate:"2026-11-27"};
  assert.equal(predictionTabView(ops,view)["live-tab-state"],"発行待ち");
  assert.match(predictionTabView(ops,view)["live-tab-note"],/第704回.*次回予測ではありません/);
  ops.issuedPrediction.targetRound=705;
  assert.equal(predictionTabView(ops,view)["live-tab-state"],"発行済み");
  ops.outdated=true;
  assert.equal(predictionTabView(ops,view)["live-tab-state"],"最新状態は未確認");
  assert.equal(predictionTabView(null,null)["history-tab-roi"],"—");
  assert.equal(predictionTabView(null,null)["live-tab-state"],"最新状態は未確認");
});
