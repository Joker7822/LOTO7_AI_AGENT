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
  const alerts = [];
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
