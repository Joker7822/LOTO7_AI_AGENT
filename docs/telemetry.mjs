// A single, committed main-branch snapshot eliminates mixed-time JSON reads.
// GitHub Actions state itself is sampled, so the UI never claims real-time liveness.
export const SNAPSHOT_VERSION = "loto7-ops-snapshot-v1";
export const SNAPSHOT_URL = "https://raw.githubusercontent.com/Joker7822/LOTO7_AI_AGENT/main/docs/data/dashboard_snapshot.json";
export const WORKFLOW_HEALTH = Object.freeze({
  ok: "成功", running: "実行中", warning: "要確認",
  block: "失敗", unknown: "未取得"
});

function parseDate(value) {
  if (typeof value !== "string") return null;
  const d = new Date(value);
  return Number.isFinite(d.getTime()) ? d : null;
}
function finite(value) {
  return typeof value === "number" && Number.isFinite(value);
}
export function normalizeScientificValidation(value) {
  if (!value || value.status === "not_yet_published") {
    return {status:"not_yet_published",futureDraws:null};
  }
  if (value.status !== "verified_diagnostic_only") {
    return {status:"stale_or_mismatched_evidence",futureDraws:null};
  }
  const valid = n => typeof n === "number" && Number.isFinite(n);
  const tail = value.future_e_series;
  const n = value.future_draws;
  if (value.promotion_eligible !== false ||
      !Number.isInteger(n) || n < 0 || !Array.isArray(tail) ||
      tail.length !== n || !valid(value.future_current_e) ||
      !valid(value.future_max_e) || !valid(value.future_threshold) ||
      value.future_current_e <= 0 || value.future_max_e < 1 ||
      value.future_threshold <= 1 ||
      value.future_max_e < value.future_current_e - 1e-8 ||
      value.future_threshold_crossed !== (value.future_max_e >= value.future_threshold) ||
      value.historical_matched_fair_worlds !== 32 ||
      !valid(value.historical_selection_adjusted_p_exploratory_only) ||
      value.historical_selection_adjusted_p_exploratory_only < 0 ||
      value.historical_selection_adjusted_p_exploratory_only > 1 ||
      !valid(value.original_four_top7) || !valid(value.candidate_five_top7) ||
      !valid(value.original_four_log_edge) || !valid(value.candidate_five_log_edge)) {
    throw new Error("高度な研究指標の整合性を確認できません");
  }
  const ci = value.historical_paired_block_ci || {};
  if (!valid(ci.low95) || !valid(ci.high95) || ci.low95 > ci.high95) {
    throw new Error("時系列bootstrapの研究区間が不正です");
  }
  const series = tail.map((d,i) => {
    if (!Number.isInteger(d.round) || d.round !== 701 + i ||
        !valid(d.e_value) || d.e_value <= 0) {
      throw new Error("将来e値の回別整合性が不正です");
    }
    return {round:d.round,e_value:d.e_value};
  });
  return {
    status:"verified_diagnostic_only",
    futureDraws:n,
    eValue:value.future_current_e,
    maxE:value.future_max_e,
    threshold:value.future_threshold,
    thresholdCrossed:value.future_threshold_crossed,
    originalTop7:value.original_four_top7,
    candidateTop7:value.candidate_five_top7,
    originalLog:value.original_four_log_edge,
    candidateLog:value.candidate_five_log_edge,
    nullWorlds:value.historical_matched_fair_worlds,
    adjustedExploratoryP:value.historical_selection_adjusted_p_exploratory_only,
    pairedCI:{low95:ci.low95,high95:ci.high95},
    series,
  };
}

export function normalizeAlwaysOnActivity(value, now = new Date()) {
  if (!value || value.status === "not_yet_started") {
    return {status:"not_yet_started",papers:[],sequence:0};
  }
  if (!["active_bounded_research","online_unavailable"].includes(value.status) ||
      value.promotion_authorized !== false ||
      !Number.isInteger(value.sequence) || value.sequence < 1 ||
      !Array.isArray(value.papers) || !Array.isArray(value.review_notes) ||
      typeof value.last_activity_jst !== "string") {
    return {status:"invalid_or_unsafe",papers:[],sequence:0};
  }
  const ageHours=(now.getTime()-new Date(value.last_activity_jst).getTime())/3600000;
  if (!Number.isFinite(ageHours)) return {status:"invalid_or_unsafe",papers:[],sequence:0};
  const papers=value.papers.slice(0,8).map(p=>{
    const link=typeof p.url === "string" && /^https:\/\/doi\.org\/10\.\d{4,9}\/[a-z0-9._;():%/-]+$/i.test(p.url) ? p.url : null;
    if (!link || p.review_status!=="unreviewed" ||
        typeof p.title!=="string" || p.title.length>200 || !Number.isInteger(p.year)) {
      return null;
    }
    return {title:p.title,year:p.year,url:link,reviewStatus:"unreviewed"};
  }).filter(Boolean);
  return {
    status:value.status,
    stale:ageHours>2.5 || ageHours < -1,
    sequence:value.sequence,
    lastActivity:value.last_activity_jst,
    activity:String(value.current_activity||"").slice(0,150),
    phase:String(value.current_phase||"").slice(0,60),
    researchMode:String(value.research_mode||"").slice(0,40),
    searchStatus:String(value.online_search_status||"").slice(0,80),
    papers,
    reviewNotes:value.review_notes.slice(0,6).map(n=>String(n).slice(0,160))
  };
}

export function normalizeSnapshot(snapshot, now = new Date()) {
  if (!snapshot || typeof snapshot !== "object" ||
      snapshot.version !== SNAPSHOT_VERSION ||
      !snapshot.sources || typeof snapshot.sources !== "object" ||
      !Array.isArray(snapshot.workflows) ||
      !snapshot.series || typeof snapshot.series !== "object") {
    throw new Error("監視スナップショットの形式が不正です");
  }
  const timestamp = parseDate(snapshot.generated_at_jst);
  if (!timestamp) throw new Error("監視データの取得時刻が不正です");
  const ageMinutes = (now.getTime() - timestamp.getTime()) / 60_000;
  const outdated = ageMinutes > 90 || ageMinutes < -5;
  const sha = typeof snapshot.source_commit === "string" && /^[0-9a-f]{40}$/.test(snapshot.source_commit)
    ? snapshot.source_commit : null;
  if (!sha) throw new Error("監視データの参照コミットが不正です");
  const workflows = snapshot.workflows.map(item => {
    const health = Object.hasOwn(WORKFLOW_HEALTH, item.health) ? item.health : "unknown";
    const link = typeof item.url === "string" &&
      /^https:\/\/github\.com\/Joker7822\/LOTO7_AI_AGENT\/actions\/runs\/\d+$/.test(item.url)
        ? item.url : null;
    return {
      label: String(item.label || "Unknown").slice(0, 100),
      health, status: WORKFLOW_HEALTH[health],
      conclusion: item.conclusion || null,
      url: link,
      updatedAt: item.updated_at || null,
      failures: Number.isInteger(item.recent_failure_count) ? item.recent_failure_count : null
    };
  });
  const needed = ["portfolio", "v2", "adaptive"];
  for (const key of needed) {
    if (!Array.isArray(snapshot.series[key])) {
      throw new Error("将来検証の時系列データがありません: " + key);
    }
  }
  const series = {};
  for (const key of needed) {
    series[key] = snapshot.series[key].map(p => ({
      round: p.round,
      date: p.date,
      mean_log_edge: finite(p.mean_log_edge) ? p.mean_log_edge : null,
      mean_brier_edge: finite(p.mean_brier_edge) ? p.mean_brier_edge : null,
      mean_top7_hits: finite(p.mean_top7_hits) ? p.mean_top7_hits : null,
      mean_delta_vs_random: finite(p.mean_delta_vs_random) ? p.mean_delta_vs_random : null,
      mean_delta_vs_champion: finite(p.mean_delta_vs_champion) ? p.mean_delta_vs_champion : null,
    }));
    for (let i = 0; i < series[key].length; i++) {
      const p = series[key][i];
      if (!Number.isInteger(p.round) || (i > 0 && p.round !== series[key][i - 1].round + 1)) {
        throw new Error("将来検証の回別連続性を確認できません");
      }
    }
  }

  // Incident plan is computed from this exact snapshot, not a separate fetch.
  const plan = snapshot.operations_plan;
  if (!plan || plan.version !== "agent-operations-command-center-v1" ||
      plan.source_commit !== sha || !Array.isArray(plan.tasks) ||
      !plan.counts || !plan.authority ||
      plan.authority.model_promotions !== false ||
      plan.authority.forecast_overwrites !== false ||
      plan.authority.retroactive_freezes !== false ||
      plan.authority.workflow_retries !== false ||
      plan.authority.production_publication !== false) {
    throw new Error("AI司令塔の安全性とデータ整合性を確認できません");
  }
  const allowActionUrl = url => {
    if (typeof url !== "string") return null;
    if (/^https:\/\/github\.com\/Joker7822\/LOTO7_AI_AGENT\/actions\/runs\/\d+$/.test(url)) return url;
    if (url === "https://github.com/Joker7822/LOTO7_AI_AGENT/blob/main/loto7_agent_output/agent_role_council_report.md") return url;
    return null;
  };
  const priority = {block:0,watch:1,info:2};
  const incidentTasks = plan.tasks.map(t => {
    if (!Object.hasOwn(priority,t.priority) || t.autonomous_mutation_allowed !== false ||
        t.requires_existing_workflow_or_human_review !== true ||
        !/^[a-f0-9]{16}$/.test(t.id)) {
      throw new Error("安全でないAIエージェントの対応指示が含まれています");
    }
    return {
      id:t.id,priority:t.priority,
      title:String(t.title||"要確認").slice(0,140),
      owner:String(t.owner||"担当未確認").slice(0,100),
      detail:String(t.detail||"").slice(0,300),
      recommendedAction:String(t.recommended_action||"").slice(0,320),
      url:allowActionUrl(t.url)
    };
  });
  if (incidentTasks.some((t,i) => i>0 && priority[t.priority]<priority[incidentTasks[i-1].priority]) ||
      new Set(incidentTasks.map(x=>x.id)).size!==incidentTasks.length ||
      ["block","watch","info"].some(p=>incidentTasks.filter(x=>x.priority===p).length!==plan.counts[p])) {
    throw new Error("AI司令塔の優先順位と件数が一致しません");
  }
  const scientificValidation = normalizeScientificValidation(snapshot.scientific_validation);
  const alwaysOnActivity = normalizeAlwaysOnActivity(snapshot.always_on_accuracy, now);
  const alerts = [];
  if (alwaysOnActivity.stale || alwaysOnActivity.status === "invalid_or_unsafe") alerts.push({
    severity:"watch",source:"自律研究活動",
    description:"定期監査が古いか、活動証跡を検証できません。研究workflowの最新実行を確認してください。"
  });
  if (scientificValidation.status === "stale_or_mismatched_evidence") alerts.push({
    severity:"watch",source:"高度な研究データ",
    description:"統計研究の状態が古いか、原データと一致していません。結果を採用せず専用CIを確認してください。"
  });
  if (outdated) alerts.push({
    severity: "watch", source: "監視データの鮮度",
    description: "監視スナップショットが90分以上前、または時刻が不正です。GitHub Actionsを確認してください。"
  });
  for (const w of workflows) {
    if (w.health === "block") alerts.push({
      severity: "block", source: w.label,
      description: "最新のGitHub Actions実行が失敗しています。詳細ログを確認してください。",
      url: w.url
    });
    if (w.health === "unknown") alerts.push({
      severity: "watch", source: w.label,
      description: "GitHub Actionsの状態を確認できません。正常とみなさず再取得してください。",
      url: w.url
    });
  }
  return {
    sourceCommit: sha, generatedAt: timestamp.toISOString(),
    ageMinutes, outdated, workflows, series, alerts,
    sources: snapshot.sources,
    scientificValidation,
    alwaysOnActivity,
    operationsPlan: { overall:plan.overall, counts:plan.counts, tasks:incidentTasks },
    healthyRuns: workflows.filter(x => x.health === "ok").length
  };
}

export const SERIES_TABS = Object.freeze([
  { id:"portfolio", label:"5口 Future-OOS",
    description:"事前凍結した5口の累積平均score差（基準 Random / Champion）。26回未完了の暫定値です。",
    choices:[
      { id:"mean_delta_vs_random", label:"Randomとの差", zero:0 },
      { id:"mean_delta_vs_champion", label:"Championとの差", zero:0 }
    ] },
  { id:"v2", label:"v2 26回の信号検証",
    description:"第701回からの事前凍結・二重ソース検証済みだけ。26回終了までは診断値です。",
    choices:[
      { id:"mean_log_edge", label:"log-score差", zero:0 },
      { id:"mean_brier_edge", label:"Brier改善", zero:0 },
      { id:"mean_top7_hits", label:"Top7平均", zero:49/37 }
    ] },
  { id:"adaptive", label:"継続学習の未来検証",
    description:"予測を先に凍結し、確定結果でだけ適応した信号。途中の値は探索的です。",
    choices:[
      { id:"mean_log_edge", label:"log-score差", zero:0 },
      { id:"mean_brier_edge", label:"Brier改善", zero:0 },
      { id:"mean_top7_hits", label:"Top7平均", zero:49/37 }
    ] }
]);
