# LOTO7 AI Agent v4 — Continuous Research + Future OOS Governance

LOTO7履歴を使って研究モデルを**待ち時間なしで連続探索**しつつ、Production Championの昇格は**未来の抽せん結果で事前凍結したshadow候補を評価した時だけ**許可する構成です。

> 予測は当せんを保証しません。過去データを大量に探索して良く見えたモデルを、そのまま本番採用しないことを最優先にしています。

## v4の基本構造

### 1. Continuous Research

- 研究Winnerを次世代の親に継承
- 1世代あたり局所変異と大域random restartを混在
- 30 / 60 / 120回窓で研究スコアを比較
- 上位モデルを `candidate_pool.json` に保存
- 研究予測5通りは各世代で更新
- 研究終了後はsleepせず次世代へ進む

過去データの研究スコアは**探索順位専用**です。Production Champion昇格には使いません。

### 2. Frozen Shadow Models

新しい抽せん結果を取り込んだ時点で、次回用のshadow候補を最大6モデル選び、各モデルの5通りを事前凍結します。

- `loto7_agent_output/shadow_registry.json`
- Championの5通りも同時に凍結
- 同じ対象回について後から書き換えない

### 3. Future OOS Evaluation

次の抽せん結果が取得されたら、凍結済みshadowとChampionを**実際に未知だった未来の結果**で比較します。

- `loto7_agent_output/shadow_oos_results.csv` — append-only OOS結果
- `loto7_agent_output/oos_candidate_state.json` — 累積OOS証拠

単一ソースしか検証できない抽せん結果は記録には残しますが、Champion昇格の統計証拠には数えません。

### 4. Production Promotion

Production Championの昇格条件は以下です。

- 信頼済み未来OOS: 8回以上
- anytime-valid e-process の e-value: 20以上
- Championに対する平均複合score差: +0.05以上
- OOS勝率: 55%以上
- 直近の抽せん結果が `verified_two_result_sources`

過去30/60/120回バックテストの結果だけでは**昇格しません**。

## 過去回の回別予測・精度確認

`historical_replay.py` は、過去の各抽せん回を順番に再生して精度を確認します。

- 第101回以降を標準評価対象とする
- 対象回 `t` の予測時には **`t` より前の履歴だけ**を使用
- 対象回の当選結果は5口を固定した後にだけ照合
- 固定baseline設定を使うため、研究Winnerを後から過去へ当てはめるselection leakageを避ける
- Top7の平均本数字一致数を理論random平均と比較
- 5口ポートフォリオの最大一致数、平均一致数、3個以上/4個以上一致率、複合scoreを評価
- 各回32個のrandom 5口ポートフォリオと同条件比較
- 1〜6等の等級も回別・口別に記録

出力:

- `loto7_agent_output/historical_round_predictions.csv` — 各回×5口の予測と一次照合
- `loto7_agent_output/historical_round_accuracy.csv` — 各回のTop7/5口精度とrandom比較
- `loto7_agent_output/historical_replay_summary.json` — 累積指標
- `loto7_agent_output/historical_accuracy_report.md` — 人間向け精度レポート

### 過去予測の独立照合

`historical_reconcile.py` は `historical_round_predictions.csv` に埋め込まれた実績値をそのまま信用せず、`loto7.csv` を別に読み直して各予測を再照合します。

- 基準回 / 対象回 / 予測5口を追跡
- 本数字・ボーナス数字の一致数を再計算
- 1〜6等を再判定
- 各回で公表された1口あたり当選金額を参照
- 1口300円として参考購入額・参考差引を記録
- replay側に埋め込まれた実績と `loto7.csv` が不一致ならfail closed
- 金額は過去の公表配当を使う参考値で、実際に購入していた場合の実現損益とは区別

追加出力:

- `loto7_agent_output/historical_reconciliation.csv` — 1口単位の独立照合台帳
- `loto7_agent_output/historical_reconciliation_summary.json` — 照合・等級・参考金額集計
- `loto7_agent_output/historical_reconciliation_report.md` — 人間向け照合レポート

### Nested Champion / Research / Random比較

`nested_replay.py` は、現在のResearch Winnerを過去へ後付けせず、v2時点で事前定義されていた `baseline / stable / balanced / adaptive` の4モデルから、各対象回より**前に確定していた予測成績だけ**でResearchモデルを選びます。

標準では直近120回を対象に、次の3者を同条件で比較します。

- Champion reference: baseline
- Nested Research selector: 過去時点で選ばれた事前定義モデル
- Random reference: 各回32個のrandom 5口ポートフォリオ平均

評価指標は平均最大一致、1口平均一致、3個以上/4個以上一致回率、複合score、ResearchのChampion/Randomに対するscore差、回別勝率、deterministic bootstrap 95%信頼区間です。

出力:

- `loto7_agent_output/nested_replay_rounds.csv`
- `loto7_agent_output/nested_replay_summary.json`
- `loto7_agent_output/nested_replay_report.md`

historical replay / reconciliation / nested replayはすべて**精度確認用の診断**です。v4 Production Championの昇格条件である未来OOS証拠には加算しません。

`loto7.csv` または関連予測ファイルのSHA・評価条件が変わった時だけ再計算し、同じデータではcache判定でスキップします。

## GitHub Actions構成

現在 `.github/workflows/` には **12本**のworkflowがあります。継続研究とCIの中核は次の2本です。

- `.github/workflows/continuous_loto7_v4.yml` — 継続研究・OOS評価・過去回精度replay・独立照合・nested比較・監査
- `.github/workflows/ci.yml` — コード変更時のcompile / pytest / Sakura secret-file guard

補助・診断・本番運用workflowとして、以下も存在します。

- `.github/workflows/champion_calibration_oos.yml`
- `.github/workflows/champion_ranking_calibration.yml`
- `.github/workflows/friday_result_check_watchdog.yml`
- `.github/workflows/joint_set_research.yml`
- `.github/workflows/publish_production_now.yml`
- `.github/workflows/signal_expert_attribution_oos.yml`
- `.github/workflows/signal_meta_research.yml`
- `.github/workflows/strict_oos_bootstrap.yml`
- `.github/workflows/sync_sakura_prediction_db.yml`
- `.github/workflows/weekly_production_fallback.yml`

旧v3の `weekly_loto7.yml` と、一回性の `start_continuous_now.yml` は削除しています。

`Continuous LOTO7 Research v4` は1ランナー内で約4時間研究を繰り返し、正常終了時に次のランナーを起動します。毎日02:00 JSTのスケジュールは回復用です。

公開結果サイトへのアクセスは研究世代ごとには行わず、通常は最大1時間間隔です。金曜日20〜21時台は新結果待ちのため10分間隔・最大90分再試行します。

## Git checkpointとCI負荷

研究計算は連続しますが、Gitへは原則**10世代ごと**にcheckpointします。新データ取得・OOS採点・shadow凍結・Champion昇格など重要イベント時は即checkpointします。

CIは以下の変更時だけ起動します。

- Pythonコード
- `tests/**`
- `requirements.txt`
- `sakura/**`
- workflow定義

`STATUS.md` や `loto7_agent_output/**` だけの自動checkpointではCIを起動しません。

## 主な出力

### Production

- `loto7_agent_output/model_champion.json`
- `loto7_agent_output/candidate_tickets.csv`
- `loto7_agent_output/latest_prediction.txt`
- `loto7_agent_output/predictions.csv` — append-only

### Research

- `loto7_agent_output/v4_research_state.json`
- `loto7_agent_output/candidate_pool.json`
- `loto7_agent_output/v4_research_evaluation.json`
- `loto7_agent_output/research_candidate_tickets.csv`
- `loto7_agent_output/latest_research_prediction.txt`

### Historical Accuracy / Reconciliation / Nested

- `loto7_agent_output/historical_round_predictions.csv`
- `loto7_agent_output/historical_round_accuracy.csv`
- `loto7_agent_output/historical_replay_summary.json`
- `loto7_agent_output/historical_accuracy_report.md`
- `loto7_agent_output/historical_reconciliation.csv`
- `loto7_agent_output/historical_reconciliation_summary.json`
- `loto7_agent_output/historical_reconciliation_report.md`
- `loto7_agent_output/nested_replay_rounds.csv`
- `loto7_agent_output/nested_replay_summary.json`
- `loto7_agent_output/nested_replay_report.md`

### Future OOS Governance

- `loto7_agent_output/shadow_registry.json`
- `loto7_agent_output/shadow_oos_results.csv`
- `loto7_agent_output/oos_candidate_state.json`

### Audit / Runtime

- `loto7_agent_output/actual_results.csv`
- `loto7_agent_output/reconciliation.csv`
- `loto7_agent_output/prediction_results.txt`
- `loto7_agent_output/execution_metrics.csv`
- `STATUS.md`

## データ取得・検証

- 主取得元: 楽天×宝くじ ロト7バックナンバー
- 優先クロスチェック元: みずほ銀行 当せん番号案内
- フォールバッククロスチェック元: 楽天銀行 当せん番号案内 / 埋め込みbacknumber
- スケジュール確認: 宝くじ公式サイト

みずほ側が取得できない場合は楽天銀行側を試し、対象回・本数字・ボーナス数字・取得できる場合は抽せん日まで一致した時だけ `verified_two_result_sources` とします。解析可能な第2ソースが主取得元と食い違った場合はfail closedです。どちらの第2ソースも機械解析できない場合は `degraded_single_result_source` とし、研究は継続しますがProduction昇格用OOS証拠には数えません。

詳細は `VALIDATION.md` を参照してください。

## ローカル検証

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m compileall -q .
python -m pytest -q

python fetch_validate.py --csv loto7.csv --max-attempts 1 --interval-seconds 0
python historical_replay.py --csv loto7.csv --out-dir loto7_agent_output --if-stale
python historical_reconcile.py \
  --predictions loto7_agent_output/historical_round_predictions.csv \
  --loto-csv loto7.csv \
  --out-dir loto7_agent_output \
  --if-stale
python nested_replay.py --csv loto7.csv --out-dir loto7_agent_output --last-n 120 --if-stale
python loto7_v4_runner.py --csv loto7.csv --out-dir loto7_agent_output
python audit_ledger.py \
  --loto-csv loto7.csv \
  --tickets-csv loto7_agent_output/candidate_tickets.csv \
  --out-dir loto7_agent_output \
  --status-md STATUS.md
python v4_status.py
```

## 注意

ロト7は確率的な抽せんです。バックテスト改善や研究世代数の増加は、将来の当せんを保証しません。v4は、探索量を増やすことよりも**未来OOSで再現した改善だけを本番採用する**ことを重視しています。
