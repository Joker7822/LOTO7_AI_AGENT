import { SNAPSHOT_URL, normalizeSnapshot, SERIES_TABS } from "./telemetry.mjs";
import {
  LEVEL_LABELS, buildView, percent, displayMetric
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
function renderIssuedPredictions(ops){
  const prediction=ops.issuedPrediction;
  const grid=clear("issued-ticket-grid");
  const history=clear("issued-previous-results");
  if(prediction.status!=="published"){
    set("issued-target","発行済みの予測がありません");
    set("issued-details","本番発行台帳で確認できた場合のみ公開します");
    set("issued-status","未発行");
    set("issued-result-status","予測番号なし");
    set("issued-next-check","未発行・未登録の候補は掲載しません");
    set("issued-previous-status","未取得");
    grid?.append(node("p","muted","新たに発行された予測はまだ確認できません。"));
    history?.append(node("p","muted","直近の照合済み予測成績は未取得です。"));
    return;
  }
  set("issued-target","第"+prediction.targetRound+"回向け · Production 5口");
  set("issued-details","予測発行: "+asJst(prediction.publishedAt)+"　/　モデル: "+prediction.model);
  set("issued-status",prediction.currentResult?"2ソース照合済み":"発行済み");
  for(const ticket of prediction.tickets){
    const article=node("article","issued-ticket");
    article.append(node("strong","issued-ticket-label","予測 "+ticket.ticket));
    const row=node("div","ball-row issued-ball-row");
    for(const n of ticket.numbers)row.append(node("span","ball",String(n).padStart(2,"0")));
    article.append(row);
    if(prediction.currentResult){
      const scored=prediction.currentResult.tickets[ticket.ticket-1];
      article.append(node("span","issued-ticket-grade",
        "本数字 "+scored.mainHits+"個・ボーナス "+scored.bonusHits+"個 / "+scored.grade));
    }
    grid?.append(article);
  }
  set("issued-result-status",prediction.currentResult?
      "第"+prediction.targetRound+"回：抽せん結果を照合済み":
      "第"+prediction.targetRound+"回：公式結果の検証待ち");
  set("issued-next-check",prediction.currentResult?
      "2ソース検証済みの実結果だけで一致数を採点しました":
      "結果が確認されるまで当否は表示しません。抽せん予定: "+prediction.drawDate);
  const prev=prediction.lastVerified;
  set("issued-previous-status",prev?"第"+prev.round+"回 検証済み":"照合済み結果なし");
  if(!prev){
    history?.append(node("p","muted","照合済みの過去予測成績がありません。"));
    return;
  }
  set("issued-previous-heading","直近の照合済み予測成績 · 第"+prev.round+"回");
  const official=node("p","issued-official",
    "公式本数字 "+prev.main.map(n=>String(n).padStart(2,"0")).join(" ") +
    "　 BONUS "+prev.bonus.map(n=>String(n).padStart(2,"0")).join(" "));
  history?.append(official);
  const table=node("div","issued-result-list");
  for(const t of prev.tickets){
    const line=node("div","issued-result-line");
    line.append(node("strong","","予測 "+t.ticket));
    line.append(node("span","","本 "+t.mainHits+"個 / B "+t.bonusHits+"個"));
    line.append(node("b","",t.grade));
    table.append(line);
  }
  history?.append(table);
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
const NS="http://www.w3.org/2000/svg";
const metricSelection={portfolio:"mean_delta_vs_random",v2:"mean_log_edge",adaptive:"mean_log_edge"};
const asJst=s=>s?new Intl.DateTimeFormat("ja-JP",{timeZone:"Asia/Tokyo",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false}).format(new Date(s))+" JST":"未取得";
function renderCommandCenter(ops){
  const plan=ops.operationsPlan;
  set("command-center-count",plan.counts.block+" 停止 / "+plan.counts.watch+" 要確認 / "+plan.counts.info+" 待機");
  set("command-center-overall",plan.overall==="block"?"重大な未対応事項があります":plan.overall==="watch"?"要確認事項を優先順位付きで表示":"監視中・重大な未対応なし");
  const grid=clear("command-center-grid");
  if(!plan.tasks.length){
    grid.append(node("p","command-empty","✓ 現在、追加対応が必要な事項はありません。"));return;
  }
  for(const task of plan.tasks){
    const card=node("article","command-card "+task.priority);
    const head=node("div","command-card-head");
    head.append(node("b","",task.owner));
    const tag=task.priority==="block"?"停止":task.priority==="watch"?"要確認":"待機";
    head.append(pill(task.priority==="info"?"ok":task.priority,tag));
    card.append(head);
    card.append(node("h4","",task.title));
    card.append(node("p","",task.detail));
    const next=node("div","command-next");
    next.append(node("strong","","次の安全な対応"));
    next.append(document.createTextNode(task.recommendedAction));
    card.append(next);
    if(task.url){
      const link=node("a","workflow-link","根拠・実行履歴を見る ↗");
      link.href=task.url;link.target="_blank";link.rel="noopener noreferrer";
      card.append(link);
    }
    grid.append(card);
  }
}
function renderWorkflowStatus(ops){
  set("monitor-timestamp",asJst(ops.generatedAt));
  set("monitor-commit",ops.sourceCommit.slice(0,12));
  set("workflow-summary",ops.healthyRuns+" / "+ops.workflows.length+" 正常終了（最新実行）");
  const grid=clear("workflow-grid");
  for(const w of ops.workflows){
    const box=node("article","workflow-card"),head=node("div","workflow-row");
    head.append(node("b","",w.label));
    head.append(pill(w.health==="running"||w.health==="warning"?"watch":w.health==="block"?"block":w.health==="ok"?"ok":"unknown",w.status));
    box.append(head);
    box.append(node("p","workflow-updated","最終実行 "+asJst(w.updatedAt)));
    if(w.failures!=null)box.append(node("span","workflow-note","直近5回の失敗: "+w.failures));
    if(w.url){const link=node("a","workflow-link","実行ログを見る ↗");link.href=w.url;link.rel="noopener noreferrer";link.target="_blank";box.append(link);}
    grid.append(box);
  }
  const freshness=el("snapshot-freshness");
  if(freshness){freshness.className="freshness"+(ops.outdated?" warn":"");freshness.textContent=ops.outdated?"監視データが古くなっています":"同一コミットに基づく監視データ";}
}
function svgEl(tag,attrs={},label=""){
  const e=document.createElementNS(NS,tag);
  for(const [key,value] of Object.entries(attrs))e.setAttribute(key,String(value));
  if(label)e.textContent=label;
  return e;
}
function renderSeriesGraph(series,field,baseline){
  const svg=svgEl("svg",{viewBox:"0 0 420 174",role:"img","aria-label":"将来検証"+series.length+"回の累積平均"});
  if(!series.length)return svg;
  const values=series.map(x=>x[field]);
  if(values.some(v=>typeof v!=="number"))return svg;
  const l=47,r=407,t=19,b=140;
  let low=Math.min(...values,baseline),high=Math.max(...values,baseline);
  const padding=Math.max((high-low)*.23,field==="mean_top7_hits"?.08:.00003);
  low-=padding;high+=padding;
  const xx=i=>l+(series.length===1?.5:i/(series.length-1))*(r-l);
  const yy=v=>b-(v-low)/(high-low)*(b-t);
  svg.append(svgEl("line",{x1:l,y1:b,x2:r,y2:b,stroke:"#4d6382","stroke-width":.7}));
  const zy=yy(baseline);
  svg.append(svgEl("line",{x1:l,y1:zy,x2:r,y2:zy,stroke:"#92a4bb","stroke-width":1,"stroke-dasharray":"4 5"}));
  svg.append(svgEl("text",{x:3,y:zy+4,fill:"#8ba5c2","font-size":10},field==="mean_top7_hits"?"1.324":"0"));
  svg.append(svgEl("polyline",{points:values.map((v,i)=>xx(i)+","+yy(v)).join(" "),fill:"none",stroke:"#6ae4d7","stroke-width":2.5,"stroke-linecap":"round","stroke-linejoin":"round"}));
  for(let i=0;i<series.length;i++){
    const dot=svgEl("circle",{cx:xx(i),cy:yy(values[i]),r:3,fill:"#8bf4eb",stroke:"#081829","stroke-width":1});
    dot.append(svgEl("title",{},"第"+series[i].round+"回: "+values[i].toFixed(7)));
    svg.append(dot);
  }
  svg.append(svgEl("text",{x:l,y:164,fill:"#8ba5c2","font-size":10},"第"+series[0].round+"回"));
  svg.append(svgEl("text",{x:r,y:164,fill:"#8ba5c2","font-size":10,"text-anchor":"end"},"第"+series.at(-1).round+"回"));
  return svg;
}
function renderResearchApplication(ops){
  const g=ops.researchApplication;
  const list=clear("application-review-list");
  if(g.status!=="research_review_ready_only"){
    set("application-health",g.status==="not_yet_published"?"初回研究結果待ち":"整合性を要確認");
    for(const id of ["application-papers","application-verified","application-null"])set(id,"—");
    if(list)list.append(node("p","muted","研究ゲートの結果が未公開、または検証できません。"));
    return;
  }
  set("application-health",g.trustedSource?"人の手法審査待ち":"抽せん結果の二重照合待ち");
  set("application-papers",String(g.papers)+" 件");
  set("application-verified",String(g.verifiedDois)+" 件");
  set("application-null","安全性検査済み");
  const topics={
    calibration:"予測確率の校正",
    online_evaluation:"オンライン学習の評価",
    anytime_evidence:"逐次検定・e値",
    distribution_shift:"時系列の変化",
    selection_bias:"多重比較・過剰適合",
    ensemble:"複数モデルの統合"
  };
  if(!list)return;
  if(!g.tasks.length){
    list.append(node("p","muted","現在、有効な研究計画はありません。"));
    return;
  }
  for(const item of g.tasks){
    const row=node("article","application-review");
    const heading=node("div","application-review-heading");
    heading.append(node("strong","",topics[item.topic]));
    heading.append(node("span","",item.twoProviderMatches+" 件の二重照合済み参考情報"));
    row.append(heading);
    row.append(node("p","",item.status==="bibliography_needs_verification"?
      "次の対応：論文の書誌情報を独立して照合。手法の実行は不可。":
      "次の対応：全文・仮定・再現性・ライセンスを人が審査。実験と本番採用は未承認。"));
    list.append(row);
  }
}
function renderAlwaysOn(ops){
  const a=ops.alwaysOnActivity, container=clear("always-on-paper-list");
  if (a.status==="not_yet_started" || a.status==="invalid_or_unsafe"){
    set("always-on-health",a.status==="not_yet_started"?"初回実行待ち":"要確認");
    for(const key of ["always-on-count","always-on-time","always-on-activity","always-on-mode"])set(key,"—");
    set("always-on-search","検索待ち");
    container.append(node("p","muted","監査活動の記録がまだないか、安全な表示を確認できません。"));
    return;
  }
  set("always-on-health",a.stale?"更新遅延":a.status==="online_unavailable"?"接続要確認":"記録更新中");
  set("always-on-count",String(a.sequence)+" 回");
  set("always-on-time",asJst(a.lastActivity));
  set("always-on-activity",a.activity);
  set("always-on-mode",a.researchMode==="SEARCH"?"探索許可":a.researchMode==="VALIDATION_ONLY"?"検証限定":"新データ待ち");
  const searchStatus = a.searchStatus.startsWith("unavailable:")?"通信失敗":a.searchStatus==="searched"?"文献検索済み":a.searchStatus==="no_relevant_metadata"?"関連論文なし":"次の巡回で検索";
  set("always-on-search",searchStatus);
  if (!a.papers.length){
    container.append(node("p","muted","まだ候補文献はありません。オンライン調査の成功後に表示します。"));
    return;
  }
  for(const p of a.papers){
    const item=node("article","always-on-paper");
    const anchor=node("a","always-on-doi",p.title+" ↗");
    anchor.href=p.url;anchor.target="_blank";anchor.rel="noopener noreferrer";
    item.append(anchor);
    item.append(node("p","",p.year+"年 · 未検証の研究候補"));
    container.append(item);
  }
}
function renderScientific(ops){
  const v=ops.scientificValidation;
  const plot=clear("science-e-plot");
  if(v.status!=="verified_diagnostic_only"){
    const label=v.status==="not_yet_published"?"最初の研究レポートを待っています。":"原データとの整合を確認できないため研究指標を非表示にしています。";
    set("science-future-pill",v.status==="not_yet_published"?"研究データ待ち":"要確認");
    for(const id of ["science-four-top7","science-five-top7","science-log-delta","science-ci",
                     "science-p","science-e","science-max-e","science-trusted"])set(id,"—");
    if(plot)plot.append(node("p","muted",label));
    return;
  }
  const sign=n=>(n>=0?"+":"")+n.toFixed(7);
  set("science-four-top7",v.originalTop7.toFixed(3)+" 個");
  set("science-five-top7",v.candidateTop7.toFixed(3)+" 個");
  set("science-log-delta",sign(v.candidateLog-v.originalLog));
  set("science-ci","["+sign(v.pairedCI.low95)+", "+sign(v.pairedCI.high95)+"]");
  set("science-p","p="+v.adjustedExploratoryP.toFixed(4)+"（"+v.nullWorlds+"世界）");
  set("science-e",v.eValue.toFixed(4));
  set("science-max-e",v.maxE.toFixed(4));
  set("science-threshold",v.threshold.toFixed(0));
  set("science-trusted",v.futureDraws+" 回");
  set("science-future-pill",v.futureDraws===0?"未来データ待ち":v.thresholdCrossed?"要監査・自動採用なし":"未来の観測中");
  if(!plot)return;
  if(!v.series.length)plot.append(node("p","science-empty","まだ独立した将来結果はありません。将来e値は中立値1で開始します。"));
  else plot.append(renderSeriesGraph(v.series,"e_value",1));
}
function renderProspective(ops){
  const host=clear("prospective-trends");
  for(const tab of SERIES_TABS){
    const data=ops.series[tab.id],card=node("article","panel prospective-panel"),top=node("div","panel-heading");
    top.append(node("h3","",tab.label));
    top.append(node("span","label-outline",data.length+"回 / 事前凍結実績"));
    card.append(top);
    const choices=node("div","metric-tabs");
    for(const metric of tab.choices){
      const btn=node("button","metric-tab"+(metric.id===metricSelection[tab.id]?" active":""),metric.label);
      btn.type="button";btn.setAttribute("aria-pressed",metric.id===metricSelection[tab.id]?"true":"false");
      btn.addEventListener("click",()=>{metricSelection[tab.id]=metric.id;renderProspective(ops);});
      choices.append(btn);
    }
    card.append(choices);
    const plot=node("div","prospective-plot");
    if(!data.length)plot.append(node("div","prospective-empty","まだ実際の未来結果はありません。事前凍結・照合後に表示します。"));
    else{
      const selected=tab.choices.find(x=>x.id===metricSelection[tab.id])||tab.choices[0];
      plot.append(renderSeriesGraph(data,selected.id,selected.zero));
      const last=data.at(-1)[selected.id];
      plot.append(node("p","prospective-latest","累積平均: "+(last==null?"未取得":last.toFixed(selected.id==="mean_top7_hits"?3:6))));
    }
    card.append(plot);card.append(node("p","prospective-caption",tab.description));host.append(card);
  }
}
function appendOperationalWarnings(ops){
  const list=el("alert-list");if(!list)return;
  for(const a of ops.alerts){
    const item=node("article","alert-item "+(a.severity==="block"?"block":"watch"));
    item.append(node("span","alert-owner",a.source));
    item.append(node("p","",a.description));
    if(a.url){const link=node("a","workflow-link","実行ログ ↗");link.href=a.url;link.target="_blank";link.rel="noopener noreferrer";item.append(link);}
    list.append(item);
  }
}
export async function refresh(){
  if(busy)return;
  busy=true;const button=el("refresh");
  if(button)button.disabled=true;set("refresh-label","更新中");
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),13000);
  try{
    const response=await fetch(SNAPSHOT_URL+"?v="+Date.now(),{cache:"no-store",headers:{Accept:"application/json"},signal:controller.signal});
    if(!response.ok)throw new Error("監視JSONを取得できません (HTTP "+response.status+")");
    const ops=normalizeSnapshot(await response.json(),new Date());
    const view=buildView(ops.sources,{},new Date());
    if(ops.outdated&&view.state==="ok"){view.state="watch";view.stateLabel="監視データが古くなっています";}
    if((ops.alerts.some(a=>a.severity==="block")||ops.operationsPlan.overall==="block")&&view.state!=="unknown"){view.state="block";view.stateLabel="一部の自動処理で異常を確認";}
    renderOverview(view);renderProgress(view);renderResearch(view);renderOperations(view);renderIssuedPredictions(ops);
    renderWorkflowStatus(ops);renderProspective(ops);renderScientific(ops);renderAlwaysOn(ops);renderResearchApplication(ops);renderCommandCenter(ops);appendOperationalWarnings(ops);
    set("alerts-count",view.handoffs.length+view.inconsistencies.length+ops.alerts.length+" 件");
    document.title=(view.state==="ok"?"● ":view.state==="watch"?"◐ ":"！ ")+"LOTO7 AI AGENT | 現在の状態";
  }catch(e){
    set("overall-status","監視データを取得できません");
    const light=el("overall-light");if(light)light.className="status-light unknown";
    set("snapshot-freshness","未取得・通信状況を確認してください");
    const list=clear("alert-list");list.append(node("p","error-line",String(e.message||"監視情報の取得失敗")));
    set("issued-status","検証データ未取得");
    clear("issued-ticket-grid")?.append(node("p","error-line","公開予測の整合性を確認できないため番号を表示しません。"));
    clear("issued-previous-results")?.append(node("p","muted","照合済み結果を取得できません。"));
    set("science-future-pill","情報を取得できません");
    set("command-center-overall","司令塔の判定を取得できません");
    const grid=clear("command-center-grid");grid.append(node("p","error-line","安全な判断のため状態の再取得が必要です。"));
  }finally{clearTimeout(timeout);busy=false;if(button)button.disabled=false;set("refresh-label","更新");}
}
el("refresh")?.addEventListener("click",refresh);
document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh();});
setInterval(()=>{if(!document.hidden)refresh();},REFRESH_MS);
refresh();
