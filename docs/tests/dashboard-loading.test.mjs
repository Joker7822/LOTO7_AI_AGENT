import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {
  SNAPSHOT_URL, SNAPSHOT_MIRROR_URL,
  normalizeSnapshot, loadPublishedSnapshot
} from "../telemetry.mjs";

const published = () => JSON.parse(
  readFileSync(new URL("../data/dashboard_snapshot.json", import.meta.url), "utf8")
);
const response = (payload, code=200) => ({
  ok:code>=200 && code<300,status:code,
  json:async()=>payload
});

test("actual checked-in public snapshot is safe to normalize", () => {
  const s=published();
  const rendered=normalizeSnapshot(s,new Date(s.generated_at_jst));
  assert.equal(rendered.sourceCommit,s.source_commit);
  assert.equal(rendered.outdated,false);
  assert.equal(rendered.issuedPrediction.status,s.latest_prediction.status);
});

test("same-origin Pages snapshot loads without third-party requests", async () => {
  const s=published(),calls=[];
  const got=await loadPublishedSnapshot(async url=>{
    calls.push(url);
    return response(s);
  },new Date(s.generated_at_jst));
  assert.equal(calls.length,1);
  assert.ok(calls[0].startsWith(SNAPSHOT_URL));
  assert.ok(!calls[0].startsWith(SNAPSHOT_MIRROR_URL));
  assert.equal(got.source,SNAPSHOT_URL);
  assert.equal(got.snapshot.outdated,false);
});

test("raw GitHub mirror is used when Pages snapshot is unavailable", async () => {
  const s=published(),calls=[];
  const got=await loadPublishedSnapshot(async url=>{
    calls.push(url);
    if(url.startsWith(SNAPSHOT_URL))throw new Error("Pages not available");
    return response(s);
  },new Date(s.generated_at_jst));
  assert.equal(got.source,SNAPSHOT_MIRROR_URL);
  assert.equal(calls.length,2);
  assert.equal(got.errors.length,1);
});

test("newer mirror replaces stale Pages snapshot, without mixing underlying evidence", async () => {
  const s=published();
  const old=structuredClone(s);
  old.generated_at_jst=new Date(Date.parse(s.generated_at_jst)-3*3600*1000).toISOString();
  const got=await loadPublishedSnapshot(async url=>response(
    url.startsWith(SNAPSHOT_URL)?old:s
  ),new Date(s.generated_at_jst));
  assert.equal(got.source,SNAPSHOT_MIRROR_URL);
  assert.equal(got.snapshot.outdated,false);
  assert.equal(got.snapshot.sourceCommit,s.source_commit);
});

test("stale but validated data are shown as stale when the mirror is unavailable", async () => {
  const s=published();
  const now=new Date(Date.parse(s.generated_at_jst)+3*3600*1000);
  const got=await loadPublishedSnapshot(async url=>{
    if(url.startsWith(SNAPSHOT_MIRROR_URL))throw new Error("offline mirror");
    return response(s);
  },now);
  assert.equal(got.source,SNAPSHOT_URL);
  assert.equal(got.snapshot.outdated,true);
  assert.equal(got.errors.length,1);
});

test("a malformed Pages response never blocks an independently valid mirror", async () => {
  const s=published();
  const got=await loadPublishedSnapshot(async url=>
    response(url.startsWith(SNAPSHOT_URL)?{invalid:true}:s)
  ,new Date(s.generated_at_jst));
  assert.equal(got.source,SNAPSHOT_MIRROR_URL);
});

test("if both sources fail, the UI must show an error, never a fabricated green state", async () => {
  await assert.rejects(
    loadPublishedSnapshot(async()=>response({},503),new Date(),50),
    /公開状態JSONを取得・検証できません/
  );
});
