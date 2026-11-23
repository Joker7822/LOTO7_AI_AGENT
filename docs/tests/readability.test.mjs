import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const html=readFileSync(new URL("../index.html",import.meta.url),"utf8");
const css=readFileSync(new URL("../style.css",import.meta.url),"utf8");
const app=readFileSync(new URL("../app.js",import.meta.url),"utf8");

test("simple initial screen shows draw, adopted ROI v2, 5 issued tickets and future evidence in order",()=>{
  const ids=["overview","roi-v2","issued-predictions","validation","prospective-trend","research-details","operations"];
  const positions=ids.map(id=>html.indexOf('id="'+id+'"'));
  assert.ok(positions.every(p=>p>=0),"main visitor sections present");
  assert.ok(positions.every((p,i)=>i===0||p>positions[i-1]),"money and tickets before specialist research");
  assert.match(html,/ひと目でわかりやすく/);
  assert.match(html,/回収率とは？/);
  assert.match(html,/過去の仮想回収率/);
  assert.match(html,/旧モデルv1/);
  assert.match(html,/実際の購入/);
  assert.match(html,/最新の予測5口/);
  assert.match(html,/確認できた情報だけ/);
});

test("native research details makes the advanced material optional and preserves all internal targets",()=>{
  const start=html.indexOf('<details class="research-details"');
  const end=html.indexOf("</details>",start);
  assert.ok(start>0&&end>start);
  assert.match(html.slice(start,end),/<summary class="research-details-summary">/);
  assert.ok(!/<details class="research-details"[^>]*open/.test(html));
  for(const id of ["always-on-accuracy","research-application","advanced-validation","research","prediction-metrics"]){
    assert.ok(html.indexOf('id="'+id+'"')>start&&html.indexOf('id="'+id+'"')<end,id);
  }
  assert.match(app,/details\.open=true/);
  assert.match(html,/data-expand-research/);
});

test("sticky mobile navigation links resolve and meet keyboard/accessibility requirements",()=>{
  const nav=html.match(/<nav class="quick-nav"[\s\S]*?<\/nav>/)?.[0];
  assert.ok(nav,"a navigation landmark exists");
  assert.match(nav,/aria-label="主な情報へ移動"/);
  const anchors=[...nav.matchAll(/href="#([\w-]+)"/g)].map(m=>m[1]);
  assert.ok(anchors.length>=6);
  for(const target of anchors){
    assert.match(html,new RegExp('id="'+target+'"'));
  }
  assert.match(css,/:focus-visible/);
  assert.match(css,/\.quick-nav\{position:sticky/);
  assert.match(css,/@media\(max-width:700px\)/);
  assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
  assert.match(css,/\.metric-grid\{grid-template-columns:repeat\(2/);
});

test("all new at-a-glance DOM references exist exactly once, without fake public purchase claims",()=>{
  const ids=[
    "quick-prediction-state","quick-prediction-note",
    "roi-v2-state","roi-v2-target","roi-last-issued",
    "roi-v2-amount","roi-v1-amount","roi-v2-net",
    "roi-reference-period","roi-real-cash"
  ];
  for(const id of ids){
    assert.equal([...html.matchAll(new RegExp('id="'+id+'"','g'))].length,1,id);
    assert.ok(app.includes('"'+id+'"'),id+" is populated from validated source data");
  }
  assert.doesNotMatch(html,/>期待回収率\s*87/);
  assert.doesNotMatch(html,/>実購入の回収率/);
  assert.match(html,/公開済み/);
  assert.match(app,/renderRoiCashV2\(ops\)/);
  assert.match(app,/renderQuickPrediction\(ops\)/);
});
