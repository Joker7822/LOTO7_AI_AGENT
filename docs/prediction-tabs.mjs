// View helpers for the two evidence scopes; inputs are normalized snapshots only.
export function predictionTabFromHash(hash) {
  if(["#roi-v2","#prediction-panel-history","#prediction-tab-history"].includes(hash))return "history";
  if(["#issued-predictions","#prediction-panel-live","#prediction-tab-live"].includes(hash))return "live";
  return null;
}
const finite=n=>typeof n==="number"&&Number.isFinite(n);
const count=n=>Number.isInteger(n)&&n>=0;
const pair=(a,b,d=4)=>finite(a)&&finite(b)?a.toFixed(d)+" / "+b.toFixed(d):"—";
const yen=n=>count(n)?n.toLocaleString("ja-JP")+"円":"—";
export function predictionTabView(ops,view){
  const h=ops?.predictionMetrics?.historical;
  const r=ops?.predictionMetrics?.randomBaseline;
  const p=ops?.predictionMetrics?.referencePayout;
  const hist=h?.status==="historical_only";
  const random=r?.status==="historical_only";
  const payout=p?.status==="historical_hypothetical_only";
  const next=count(view?.nextRound)&&view.nextRound>0?view.nextRound:null;
  const issued=ops?.issuedPrediction;
  const hasIssue=issued?.status==="published";
  const current=hasIssue&&next!==null&&issued.targetRound===next;
  const futureIssue=hasIssue&&next!==null&&issued.targetRound>next;
  const unknown=!ops||next===null||ops.outdated||futureIssue;
  const previous=hasIssue?"直近の発行記録は第"+issued.targetRound+"回です。":"発行済み予測はありません。";
  return {
    "history-tab-period":hist&&count(h.start)&&count(h.end)?"第"+h.start+"〜"+h.end+"回 / 過去の再予測":"検証範囲は未確認",
    "history-tab-rounds":hist&&count(h.rounds)?h.rounds.toLocaleString("ja-JP")+"回":"—",
    "history-tab-top7":hist?pair(h.top7,h.uniform):"—",
    "history-tab-max":random?pair(r.maxHits,r.randomMax):"—",
    "history-tab-score":random&&finite(r.scoreDelta)?(r.scoreDelta>=0?"+":"")+r.scoreDelta.toFixed(4):"—",
    "history-tab-cash":payout&&count(p.cost)&&count(p.payout)?yen(p.cost)+" / "+yen(p.payout):"—",
    "history-tab-roi":payout&&finite(p.roi)?(p.roi*100).toFixed(2)+"%":"—",
    "history-tab-freshness":"公開データを取得・検証できません",
    "live-tab-next":next!==null?"次回 第"+next+"回 LIVE予測":"次回の抽せんは未確認",
    "live-tab-date":next!==null&&view.nextDate?"抽せん予定: "+view.nextDate:"抽せん予定: 未確認",
    "live-tab-state":unknown?"最新状態は未確認":current?"発行済み":"発行待ち",
    "live-tab-note":unknown?"最新状態は確認できません。番号を次回予測として断定しません。":
      current?"抽せん前に正式発行された5口を下に表示します。":
      "次回の正式発行は未確認です。"+previous+" 下の番号は次回予測ではありません。",
    "live-tab-freshness":"公開データを取得・検証できません"
  };
}
