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

export function normalizeIssuedPrediction(value) {
  if (!value || value.status === "not_published") {
    return {status:"not_published",tickets:[],latestVerified:null,currentResult:null};
  }
  const validNumbers=(nums, size)=>Array.isArray(nums) && nums.length===size &&
    nums.every((n,i)=>Number.isInteger(n) && n>=1 && n<=37 && (i===0 || nums[i-1]<n));
  const dateOk=t=>typeof t==="string" && /^\d{4}-\d\d-\d\d$/.test(t);
  const timeOk=t=>typeof t==="string" && !Number.isNaN(Date.parse(t)) && /[+-]\d\d:\d\d$/.test(t);
  if(value.version!=="issued-production-forecast-public-v1" ||
     value.status!=="published" ||
     value.no_future_oos_vectors!==true || value.accuracy_claim!==false ||
     value.exposure!=="publicly_issued_production_only" ||
     !Number.isInteger(value.target_round) || value.target_round<1 ||
     value.source_base_round!==value.target_round-1 ||
     !dateOk(value.draw_date) || !timeOk(value.published_at_jst) ||
     typeof value.model!=="string" || !/^[A-Za-z0-9._-]{1,100}$/.test(value.model) ||
     !Array.isArray(value.tickets) || value.tickets.length!==5) {
    throw new Error("公開済みProduction予測の整合性を確認できません");
  }
  const tickets=value.tickets.map((t,i)=>{
    if(t.ticket!==i+1 || !validNumbers(t.numbers,7)){
      throw new Error("公開予測の口数・数字が不正です");
    }
    return {ticket:t.ticket,numbers:[...t.numbers]};
  });
  const gradeResult=(result,round)=>{
    if(result==null)return null;
    if(result.round!==round || !dateOk(result.date) ||
       !validNumbers(result.main,7) || !validNumbers(result.bonus,2) ||
       result.bonus.some(n=>result.main.includes(n)) ||
       !Array.isArray(result.tickets) || result.tickets.length!==5 ||
       (round!==value.target_round && result.source_verification!=="verified_two_result_sources")) {
      throw new Error("公開済み予測の当選照合根拠が不正です");
    }
    const checked=result.tickets.map((t,i)=>{
      if(t.ticket!==i+1 || !Number.isInteger(t.main_hits) ||
         !Number.isInteger(t.bonus_hits) ||
         t.main_hits<0 || t.main_hits>7 || t.bonus_hits<0 || t.bonus_hits>2 ||
         typeof t.grade!=="string" ||
         !["1等","2等","3等","4等","5等","6等","はずれ"].includes(t.grade)){
        throw new Error("公開済み予測の当選結果が不正です");
      }
      return {ticket:t.ticket,mainHits:t.main_hits,bonusHits:t.bonus_hits,grade:t.grade};
    });
    if(round===value.target_round){
      for(const t of checked){
        const p=tickets[t.ticket-1].numbers;
        const mh=p.filter(n=>result.main.includes(n)).length;
        const bh=p.filter(n=>result.bonus.includes(n)).length;
        if(mh!==t.mainHits || bh!==t.bonusHits)throw new Error("当選結果が公開予測と不一致です");
      }
    }
    return {round:result.round,date:result.date,main:[...result.main],
            bonus:[...result.bonus],tickets:checked};
  };
  const currentResult=gradeResult(value.current_result,value.target_round);
  if(!["awaiting_independently_verified_draw","independently_verified"].includes(value.result_status) ||
      (value.result_status==="independently_verified")!==Boolean(currentResult)){
    throw new Error("公開済み予測の結果検証状態が不正です");
  }
  const lastVerified=value.latest_verified
    ? gradeResult(value.latest_verified,value.target_round-1) : null;
  return {
    status:"published",targetRound:value.target_round,drawDate:value.draw_date,
    publishedAt:value.published_at_jst,model:value.model,
    tickets,resultStatus:value.result_status,currentResult,lastVerified,
  };
}

export function normalizeResearchApplication(value) {
  if (!value || value.status === "not_yet_published") {
    return {status:"not_yet_published",tasks:[]};
  }
  if (value.status !== "research_review_ready_only") {
    return {status:"stale_or_unsafe",tasks:[]};
  }
  const topics = new Set(["calibration","online_evaluation","anytime_evidence",
                          "distribution_shift","selection_bias","ensemble"]);
  if (value.actual_prediction_accuracy_improvement_verified !== false ||
      value.synthetic_control !== "passed" ||
      !Number.isInteger(value.papers) || value.papers < 0 ||
      !Number.isInteger(value.verified_dois) || value.verified_dois < 0 ||
      !Number.isInteger(value.proposal_count) ||
      !Array.isArray(value.tasks) || value.tasks.length !== value.proposal_count ||
      value.tasks.length > 6 || !["SEARCH","VALIDATION_ONLY","WAIT_FOR_NEW_DATA"].includes(value.research_mode)) {
    return {status:"stale_or_unsafe",tasks:[]};
  }
  const result = [];
  for(const item of value.tasks){
    if(!topics.has(item.topic) ||
       !["bibliography_needs_verification","awaiting_full_text_and_methodology_review"].includes(item.status) ||
       item.requires_human_approval !== true ||
       !Number.isInteger(item.two_provider_matches) || item.two_provider_matches < 0 ||
       item.two_provider_matches > 4){
      return {status:"stale_or_unsafe",tasks:[]};
    }
    result.push({topic:item.topic,status:item.status,twoProviderMatches:item.two_provider_matches});
  }
  return {
    status:"research_review_ready_only",papers:value.papers,verifiedDois:value.verified_dois,
    researchMode:value.research_mode,trustedSource:value.trusted_result_source===true,
    syntheticControl:"passed",tasks:result
  };
}

export function normalizeResearchPriorities(value) {
  if (!value || value.status === "not_yet_published") {
    return {status:"not_yet_published",tasks:[],totalTasks:0};
  }
  if (value.status !== "audited_research_plan") {
    return {status:"stale_or_unsafe",tasks:[],totalTasks:0};
  }
  const priorities={block:0,watch:1,info:2};
  const lanes=new Set(["source_integrity","prospective_integrity",
                        "research_governance","bibliography","experiment_review"]);
  if (value.promotion_authorized !== false ||
      !["SEARCH","VALIDATION_ONLY","WAIT_FOR_NEW_DATA"].includes(value.research_mode) ||
      typeof value.source_two_verified !== "boolean" ||
      !Number.isInteger(value.total_tasks) || value.total_tasks < 0 ||
      !value.counts || !Array.isArray(value.tasks) || value.tasks.length > 6 ||
      value.tasks.length > value.total_tasks ||
      ["block","watch","info"].some(p => !Number.isInteger(value.counts[p]) || value.counts[p]<0) ||
      Object.values(value.counts).reduce((a,b)=>a+b,0)!==value.total_tasks) {
    return {status:"stale_or_unsafe",tasks:[],totalTasks:0};
  }
  let prev=-1;
  const tasks=[];
  for(const t of value.tasks){
    if(!Object.hasOwn(priorities,t.priority) || !lanes.has(t.lane) ||
       priorities[t.priority]<prev || t.safe_autonomous_action!=="report_only" ||
       ["title","reason","next_step","owner"].some(k=>typeof t[k]!=="string" ||
         !t[k].trim() || t[k].length>320)) {
      return {status:"stale_or_unsafe",tasks:[],totalTasks:0};
    }
    prev=priorities[t.priority];
    tasks.push({priority:t.priority,lane:t.lane,title:t.title,reason:t.reason,
                nextStep:t.next_step,owner:t.owner});
  }
  return {status:"audited_research_plan",tasks,totalTasks:value.total_tasks,
          counts:value.counts,researchMode:value.research_mode,
          sourceTwoVerified:value.source_two_verified};
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
  const issuedPrediction = normalizeIssuedPrediction(snapshot.latest_prediction);
  const scientificValidation = normalizeScientificValidation(snapshot.scientific_validation);
  const alwaysOnActivity = normalizeAlwaysOnActivity(snapshot.always_on_accuracy, now);
  const researchApplication = normalizeResearchApplication(snapshot.research_application);
  const researchPriorities = normalizeResearchPriorities(snapshot.research_priorities);
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
    issuedPrediction,
    scientificValidation,
    alwaysOnActivity,
    researchApplication,
    researchPriorities,
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
