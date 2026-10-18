import {
  SOURCES, ROLE_NAMES, LEVEL_LABELS, buildView, percent, displayMetric
} from "./model.mjs";

const ROOT = "https://raw.githubusercontent.com/Joker7822/LOTO7_AI_AGENT/main/loto7_agent_output/";
const REFRESH_MS = 120_000;
let busy = false;
const el = id => document.getElementById(id);
const set = (id, value) => { const node = el(id); if (node) node.textContent = value == null ? "—" : String(value); };
const formatInt = n => n == null ? "—" : Number(n).toLocaleString("ja-JP");
function node(tag, className = "", text = "") {
  const created = document.createElement(tag);
  if (className) created.className = className;
  if (text !== "") created.textContent = String(text);
  return created;
}
function clear(id) { const target = el(id); if (target) target.replaceChildren(); return target; }
function pill(status, label = LEVEL_LABELS[status] || "未取得") {
  const p = node("span", "pill " + status, label);
  return p;
}
function translateState(status) {
  if (!status || status === "未取得") return "状態未取得";
  const table = {
    waiting_for_verified_round_700_prefix: "第700回の確認待ち",
    awaiting_two_source_round_700: "第700回の2ソース確認待ち",
    awaiting_two_source_verification: "結果の2ソース確認待ち",
    active_prefrozen_waiting_result: "予測凍結済み・結果待ち",
    graded_then_next_prefrozen: "採点後、次回を凍結済み",
    active_target_prefrozen_waiting_result: "予測凍結済み・結果待ち",
    complete_fixed_horizon: "固定検証が完了",
    active: "検証中"
  };
  return table[status] || (/^invalid_/.test(status) ? "証拠の不整合で停止" : "状態: " + status);
}
function balls(id, values, type) {
  const holder = clear(id);
  if (!holder) return;
  if (!Array.isArray(values) || !values.length) {
    holder.append(node("span", "empty-ball", "確認できる数字がありません"));
    return;
  }
  for (const n of values) {
    if (!Number.isInteger(n) || n < 1 || n > 37) continue;
    holder.append(node("span", "ball" + (type === "bonus" ? " bonus" : ""), String(n).padStart(2, "0")));
  }
}
function renderOverview(v) {
  const light = el("overall-light");
  if (light) light.className = "status-light " + v.state;
  set("overall-status", v.stateLabel);
  set("checked-at", v.sourceChecked);
  set("fetched-at", "画面再取得: " + v.fetchedAt);
  set("latest-round", v.latestRound == null ? "—" : "第" + v.latestRound + "回");
  set("latest-date", "抽せん日 " + v.drawDate);
  set("trust-status", v.sourceStatus);
  set("trust-note", v.sourceVerified ? "結果を独立した2ソースで照合" : "確認完了まで信頼済みとして扱いません");
  set("next-round", v.nextRound == null ? "—" : "第" + v.nextRound + "回");
  set("next-date", "抽せん予定 " + v.nextDate);
  const generation = v.stats[0].value;
  set("generation", formatInt(generation));
  set("evaluations", "累計 " + formatInt(v.stats[1].value) + " 件の研究評価");
  set("draw-description", v.sourceVerified ? "2ソース照合済み · " + v.drawDate : "未照合のため参考表示 · " + v.drawDate);
  balls("main-balls", v.latestMain, "main");
  balls("bonus-balls", v.latestBonus, "bonus");
}
function renderProgress(v) {
  const grid = clear("progress-grid");
  if (!grid) return;
  for (const item of v.completedCheckpoints) {
    const article = node("article", "progress-card " + item.id);
    const head = node("header");
    head.append(node("h3", "", item.name));
    const isMissing = item.done == null;
    const completed = !isMissing && item.done >= item.total && !item.ongoing;
    head.append(pill(isMissing ? "unknown" : completed ? "ok" : "watch",
      isMissing ? "未取得" : completed ? "完了" : item.done === 0 ? "開始待ち" : "検証中"));
    article.append(head);
    article.append(node("p", "", item.description));
    const main = node("div", "progress-main");
    const count = node("div", "progress-counter", isMissing ? "—" : String(item.done));
    count.append(node("small", "", " / " + item.total + (item.ongoing ? "（節目）" : "")));
    main.append(count);
    main.append(node("span", "label", percent(item.done, item.total) + "%"));
    article.append(main);
    const track = node("div", "progress-track");
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-label", item.name);
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", String(item.total));
    if (!isMissing) track.setAttribute("aria-valuenow", String(item.done));
    const fill = node("div", "progress-fill");
    fill.style.width = isMissing ? "0%" : percent(item.done, item.total) + "%";
    track.append(fill);
    article.append(track);
    const foot = node("div", "progress-foot");
    foot.append(node("span", "", translateState(item.status)));
    foot.append(node("b", "", item.target == null ? (item.ongoing ? "継続更新" : "事前登録済み") : "凍結対象 第" + item.target + "回"));
    article.append(foot);
    if (item.metric != null) {
      const extra = node("div", "role-findings", item.metricLabel + ": " + displayMetric(item.metric) + "個");
      article.append(extra);
    }
    grid.append(article);
  }
}
function renderResearch(v) {
  const chart = clear("rank-chart");
  for (const metric of v.historical) {
    const entry = node("div", "rank-row " + metric.id);
    entry.append(node("span", "rank-name", metric.label));
    const track = node("div", "rank-track");
    const bar = node("div", "rank-fill");
    bar.style.width = metric.value == null ? "0%" : Math.min(100, Math.max(0, metric.value / 2.3 * 100)) + "%";
    track.append(bar);
    entry.append(track);
    entry.append(node("span", "rank-value", metric.value == null ? "—" : displayMetric(metric.value, 3)));
    chart.append(entry);
  }
  set("research-generations", formatInt(v.stats[0].value));
  set("research-evaluations", formatInt(v.stats[1].value) + " 件");
  set("research-budget", v.stats[2].value == null ? "—" : formatInt(v.stats[2].value) + v.stats[2].suffix);
  const modes = {SEARCH:"探索中", VALIDATION_ONLY:"検証限定", WAIT_FOR_NEW_DATA:"新データ待ち"};
  set("research-mode", modes[v.researchMode] || v.researchMode);
  set("research-null", v.scoutP == null ? "未確定" : "p = " + displayMetric(v.scoutP, 4));
}
function renderOperations(v) {
  const grid = clear("role-grid");
  for (const role of v.roles) {
    const card = node("article", "role-card");
    const head = node("div", "role-top");
    head.append(node("span", "role-icon", "✦"));
    head.append(pill(role.status, role.statusLabel));
    card.append(head);
    card.append(node("h3", "", role.label));
    const details = role.findings.filter(x => x.level !== "ok");
    card.append(node("p", "", details.length ? details[0].description : role.status === "ok" ? "担当領域を継続監視中" : "監査結果の取得待ち"));
    card.append(node("div", "role-findings", "監査: " + (role.findings.length ? role.findings.length + "項目" : "未取得")));
    grid.append(card);
  }
  set("champion-name", v.champion);
  set("production-round", v.production.target + (v.production.isCurrent ? "（次回向け）" : "（最後の記録）"));
  set("production-time", v.production.issuedAt);
  set("audit-time", "監査時刻: " + v.councilChecked);
  set("alerts-count", v.handoffs.length + v.inconsistencies.length + " 件");
  const list = clear("alert-list");
  for (const message of v.inconsistencies) {
    const item = node("article", "alert-item block");
    item.append(node("span", "alert-owner", "データ表示の注意"));
    item.append(node("p", "", message));
    list.append(item);
  }
  for (const issue of v.handoffs) {
    const item = node("article", "alert-item " + issue.priority);
    item.append(node("span", "alert-owner", issue.owner));
    item.append(node("p", "", issue.description));
    list.append(item);
  }
  if (!v.handoffs.length && !v.inconsistencies.length) {
    list.append(node("p", "all-clear", "✓ 対応が必要な監査事項はありません。"));
  }
  if (v.problems.length) {
    const issues = node("p", "error-line", "一部の最新データを取得できません。ブラウザから再読み込みしてください。");
    list.append(issues);
  }
}
async function loadSource(name, file) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 13_000);
  const url = ROOT + encodeURIComponent(file) + "?_=" + Date.now();
  try {
    const response = await fetch(url, {
      cache: "no-store", headers: {Accept:"application/json"}, signal:controller.signal
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const value = await response.json();
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error("状態データの形式が不正");
    }
    return {name, value};
  } finally {
    clearTimeout(timeout);
  }
}
export async function refresh() {
  if (busy) return;
  busy = true;
  const button = el("refresh");
  if (button) button.disabled = true;
  set("refresh-label", "更新中");
  try {
    const entries = Object.entries(SOURCES);
    const settled = await Promise.allSettled(entries.map(([name, file]) => loadSource(name, file)));
    const values = {}, errors = {};
    settled.forEach((result, index) => {
      const key = entries[index][0];
      if (result.status === "fulfilled") values[key] = result.value.value;
      else errors[key] = result.reason?.message || "取得失敗";
    });
    const view = buildView(values, errors, new Date());
    renderOverview(view);
    renderProgress(view);
    renderResearch(view);
    renderOperations(view);
    document.title = (view.state === "ok" ? "● " : view.state === "watch" ? "◐ " : "！ ")
      + "LOTO7 AI AGENT | 現在の状態";
  } catch (e) {
    set("overall-status", "データの表示に失敗しました");
    const light = el("overall-light");
    if (light) light.className = "status-light block";
    const messages = clear("alert-list");
    messages.append(node("p", "error-line", String(e.message || "通信エラー")));
  } finally {
    busy = false;
    if (button) button.disabled = false;
    set("refresh-label", "更新");
  }
}
el("refresh")?.addEventListener("click", refresh);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
setInterval(() => { if (!document.hidden) refresh(); }, REFRESH_MS);
refresh();
