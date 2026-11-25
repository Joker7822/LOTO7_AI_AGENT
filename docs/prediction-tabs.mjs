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
  const roi=ops?.roiCashV2;
  const hist=roi&&roi.status!=="unavailable"&&count(roi.rounds)&&finite(roi.v2Roi);
  const next=count(view?.nextRound)&&view.nextRound>0?view.nextRound:null;
  const issued=ops?.issuedPrediction;
  const hasIssue=issued?.status==="published";
  const current=hasIssue&&next!==null&&issued.targetRound===next;
  const futureIssue=hasIssue&&next!==null&&issued.targetRound>next;
  const unknown=!ops||next===null||ops.outdated||futureIssue;
  const previous=hasIssue?"直近の発行記録は第"+issued.targetRound+"回です。":"発行済み予測はありません。";
  return {
    "history-tab-period":hist?"第2〜"+roi.referenceRound+"回 / 2013-04-12〜"+roi.referenceDate+" / ROI Cash v2":"v2検証範囲は未確認",
    "history-tab-rounds":hist?roi.rounds.toLocaleString("ja-JP")+"回":"—",
    "history-tab-cash":hist?yen(roi.historicalCost)+" / "+yen(roi.v2Payout):"—",
    "history-tab-roi":hist?(roi.v2Roi*100).toFixed(2)+"%":"—",
    "history-tab-net":hist&&Number.isSafeInteger(roi.v2Net)?roi.v2Net.toLocaleString("ja-JP")+"円":"—",
    "history-tab-risk":hist?(roi.withoutSingleWinRoi*100).toFixed(2)+"%":"—",
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
