// Public-data-only view model. No tickets, credentials or arbitrary HTML.
export const SOURCES = Object.freeze({
  source: "source_validation.json",
  council: "agent_role_council_summary.json",
  research: "v4_research_state.json",
  holdout: "future_holdout_state.json",
  signal: "joint_set_v2_signal_oos_summary.json",
  learning: "continuous_learning_agent_summary.json",
  champion: "model_champion.json",
  production: "weekly_production_prediction_state.json",
  scout: "predictive_expert_agent_summary.json",
  budget: "research_cycle_guard.json"
});
export const ROLE_NAMES = Object.freeze({
  data_steward: "データ品質",
  prospective_signal_custodian: "事前凍結・先読み防止",
  oos_risk_officer: "将来検証・リスク管理",
  research_skeptic: "研究の健全性",
  release_operations: "本番運用"
});
export const LEVEL_LABELS = Object.freeze({
  ok: "正常", watch: "要確認", block: "異常", unknown: "未取得"
});
export const ISSUE_JA = Object.freeze({
  NO_EARLY_PORTFOLIO_CLAIM: "26回の将来検証は未完了です。結果を確定した改善と解釈しないでください。",
  RESEARCH_TRIAL_LIMIT_APPROACHING: "同じ履歴での研究探索数が上限に近づいています。",
  SOURCE_REFRESH_OVERDUE: "抽せん結果の確認時刻が古くなっています。",
  RESULT_NOT_TWO_SOURCE_VERIFIED: "最新結果の2ソース照合がまだ完了していません。",
  FREEZE_701_NOW: "第700回の確認後、第701回の予測を結果公表前に凍結してください。",
  PRODUCTION_DEADLINE_PASSED: "発行期限を過ぎています。事後発行はできません。"
});

export function num(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
export function japaneseDate(s) {
  if (!s || typeof s !== "string") return "未確認";
  const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(s);
  return m ? m[1] + "/" + m[2] + "/" + m[3] : "未確認";
}
export function jstTimestamp(s) {
  if (!s) return "未取得";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return "未取得";
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone:"Asia/Tokyo", year:"numeric", month:"2-digit", day:"2-digit",
    hour:"2-digit", minute:"2-digit", hour12:false
  }).format(d) + " JST";
}
export function percent(completed, total) {
  const n = num(completed), m = num(total);
  if (n === null || m === null || m <= 0) return 0;
  return Math.round(Math.max(0, Math.min(1, n / m)) * 100);
}
export function displayMetric(n, digits = 3) {
  const x = num(n);
  return x === null ? "未確定" : x.toFixed(digits);
}
export function buildView(values, errors = {}, now = new Date()) {
  const source = values.source || {};
  const council = values.council || {};
  const research = values.research || {};
  const holdout = values.holdout || {};
  const signal = values.signal || {};
  const learning = values.learning || {};
  const champion = values.champion || {};
  const production = values.production || {};
  const scout = values.scout || {};
  const budget = values.budget || {};

  const latestRound = num(source.latest?.round);
  const scheduleRound = num(source.sources?.official_schedule?.round);
  const sourceVerified = source.status === "ok" && source.verification === "verified_two_result_sources";
  const sourceKnown = Boolean(values.source);
  const problems = Object.keys(errors);
  const councilStatus = LEVEL_LABELS[council.overall] ? council.overall : "unknown";
  const learningCount = num(learning.trusted_draws);
  const signalCount = num(signal.trusted_draws);
  const holdoutCount = num(holdout.trusted_draws);
  const learningTarget = num(learning.current_prefrozen_target);
  const signalTarget = num(signal.current_target_round);
  const currentProduction = String(production.target_round || "未取得");
  const productionIsCurrent = production.published === true
    && latestRound !== null && Number(currentProduction.replace(/[^0-9]/g, "")) === latestRound + 1;

  const roles = Object.entries(ROLE_NAMES).map(([id, label]) => {
    const rec = council.roles?.[id] || {};
    const status = LEVEL_LABELS[rec.status] ? rec.status : "unknown";
    return {
      id, label, status, statusLabel: LEVEL_LABELS[status],
      findings: Array.isArray(rec.findings) ? rec.findings.map(x => ({
        code: String(x.code || "UNKNOWN"),
        level: String(x.level || "unknown"),
        description: ISSUE_JA[x.code] || String(x.evidence || x.code || "詳細不明"),
      })) : []
    };
  });
  const handoffs = Array.isArray(council.handoff_tasks) ? council.handoff_tasks.map(t => ({
    owner: ROLE_NAMES[t.owner] || "運用確認",
    priority: t.priority === "block" ? "block" : "watch",
    code: String(t.issue_code || "UNKNOWN"),
    description: ISSUE_JA[t.issue_code] || String(t.evidence || "詳細を確認してください"),
    evidence: String(t.evidence || ""),
  })) : [];
  const inconsistencies = [];
  if (latestRound !== null && num(learning.latest_seen_round) !== null &&
      latestRound !== num(learning.latest_seen_round)) {
    inconsistencies.push("継続学習と抽せん結果の最新回が一致していません。");
  }
  if (sourceVerified && council.roles?.data_steward?.status === "block") {
    inconsistencies.push("抽せん結果の信頼状態と品質監査に不一致があります。");
  }
  if (problems.length) inconsistencies.push("一部の状態ファイルを取得できませんでした。");
  const state = !sourceKnown || !values.council || !values.learning
    ? "unknown" : !sourceVerified || councilStatus === "block" || inconsistencies.length
    ? "block" : councilStatus === "watch" ? "watch" : "ok";

  const completedCheckpoints = [
    {
      id: "learning", name: "継続学習エージェント",
      description: "未知だった結果を採点して重みを更新",
      done: learningCount, total: 26,
      target: learningTarget,
      status: String(learning.status || "未取得"),
      ongoing: true,
      metric: learning.descriptive_future_only?.mean_top7_hits,
      metricLabel: "将来Top7平均"
    },
    {
      id: "signal", name: "v2 予測信号（固定検証）",
      description: "第701回から26回の事前登録テスト",
      done: signalCount, total: num(signal.horizon_trusted_draws) || 26,
      target: signalTarget,
      status: String(signal.status || "未取得"),
      ongoing: false,
      metric: signal.interim_descriptive?.mean_top7_hits,
      metricLabel: "将来Top7平均"
    },
    {
      id: "holdout", name: "5口の将来検証",
      description: "Championと研究候補を未来の結果で比較",
      done: holdoutCount, total: num(holdout.horizon_trusted_draws) || 26,
      target: null,
      status: String(holdout.status || "未取得"),
      ongoing: false,
      metric: null,
      metricLabel: ""
    }
  ];
  const stats = [
    {key:"generation", label:"研究世代", value:num(research.generation), suffix:"世代"},
    {key:"evaluations", label:"研究評価の累計", value:num(research.total_research_evaluations), suffix:"件"},
    {key:"trial", label:"現在のデータでの探索", value:num(budget.signal_trials_this_data),
      suffix:" / " + (num(budget.max_signal_trials_per_data) ?? "—")}
  ];
  const historical = [
    {id:"uniform", label:"ランダム理論値", value:49 / 37},
    {id:"scout", label:"適応エキスパート", value:num(scout.scout?.mean_top7_hits)},
    {id:"v2", label:"従来v2", value:num(scout.v2_reference?.mean_top7_hits)}
  ];
  const srcTime = source.checked_at_jst ? new Date(source.checked_at_jst) : null;
  const staleHours = srcTime && !Number.isNaN(srcTime.getTime())
    ? (new Date(now).getTime() - srcTime.getTime()) / 3600000 : null;
  return {
    state, stateLabel: state === "ok" ? "正常に監視中" : state === "watch" ? "要確認事項あり"
      : state === "block" ? "問題を確認してください" : "一部情報を取得できません",
    latestRound, drawDate: japaneseDate(source.latest?.date),
    latestMain: Array.isArray(source.latest?.main) ? source.latest.main.filter(Number.isInteger) : [],
    latestBonus: Array.isArray(source.latest?.bonus) ? source.latest.bonus.filter(Number.isInteger) : [],
    nextRound: scheduleRound, nextDate: japaneseDate(source.sources?.official_schedule?.date),
    sourceVerified, sourceStatus: sourceKnown ? (sourceVerified ? "2ソース照合済み" : "照合未完了") : "取得できません",
    sourceChecked: jstTimestamp(source.checked_at_jst),
    councilChecked: jstTimestamp(council.checked_at_jst),
    freshnessHours: staleHours,
    fetchedAt: jstTimestamp(new Date(now).toISOString()),
    problems, inconsistencies,
    roles, handoffs, completedCheckpoints, stats, historical,
    scoutP: num(scout.synthetic_null_p_log_edge),
    dataHistoricalRoundCount: num(scout.evaluated_rounds),
    researchMode: String(budget.mode || "未取得"),
    champion: String(champion.model_version || research.champion_version || "未取得"),
    production: {
      target: currentProduction,
      issued: production.published === true,
      isCurrent: productionIsCurrent,
      issuedAt: jstTimestamp(production.published_at_jst),
    },
    promotion: false,
    documentation: "過去60回の研究成績は独立した未来の検証結果ではありません。継続学習の成績も、十分な事前登録済みの評価が集まるまで昇格根拠にはしません。"
  };
}
