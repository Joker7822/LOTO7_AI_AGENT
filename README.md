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

現在 `.github/workflows/` には **14本**のworkflowがあります。継続研究とCIの中核は次の2本です。

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
- `.github/workflows/weekly_production_publisher.yml` — 金曜13:00 JSTのProduction発行。OOS完了イベントでも13:00〜14:59 JSTに回復起動
- `.github/workflows/weekly_production_fallback.yml` — 金曜14:00 JSTのProduction fallback。15:00 JST以降は新規freezeをfail closed
- `.github/workflows/verify_sakura_credential_rotation.yml` — Sakura DB/HMAC rotationをattestation + live HMAC/DB transactionで検証し、非secret generationを固定

旧v3の `weekly_loto7.yml` と、一回性の `start_continuous_now.yml` は削除しています。

`Continuous LOTO7 Research v4` は1ランナー内で約4時間研究を繰り返し、正常終了時に次のランナーを起動します。毎日02:00 JSTのスケジュールは回復用です。

公開結果サイトへのアクセスは研究世代ごとには行わず、通常は最大1時間間隔です。金曜日20〜21時台は新結果待ちのため10分間隔・最大90分再試行します。


## Production 5-ticket geometry (effective only for new rounds >= 702)

The canonical Friday Production publisher uses **five nonoverlapping
uniformly sampled 7-number tickets (35 distinct labels)** starting **only
for new, never-before-frozen draw #702 and later**. The 2026-10-30 #701
publisher path and all already-issued immutable ledger predictions continue
unchanged. Existing Champion configuration, preregistered #701 geometry
research and all strict Future-OOS freeze/grade ledgers are protected.

- Policy: `production-disjoint35-layout-v1`, implemented in
  `production_ticket_geometry35.py`, called from
  `weekly_production_prediction.py` **only after its existing frozen-ledger
  early return**. The candidate ticket CSV is a mutable output view; actual
  Production evidence is the existing append-only `predictions.csv`.
- Generation: seeded unbiased permutation of the 37 labels, partition
  the first 35 into five seven-number tickets. Each ticket is unique and
  tickets have **zero** interticket number overlap.
- Preconditions: existing Friday **13:00–19:59 JST** publication gate,
  target >= 702, fresh latest-draw CSV hash, matching secondary
  independently verified result source, and existing ledger not frozen.
  Failure stops new publication; it never rewrites a past prediction.
- Model accounting: prediction `model_version` includes **Champion
  signal identity + separate ticket-geometry policy version**, without
  changing `model_champion.json` or using this policy as Champion/OOS
  promotion evidence. An existing shadow Champion's research tickets
  may have different geometry and are NOT presented as evaluations of this
  new Production ticket layout.
- Selection: under a fair 7-of-37 model the exact composite expectation
  of the 35-number disjoint layout (~2.95215) exceeds that of an anchor
  shared by two tickets (~2.94171). The previously observed historical
  random-anchor high score is not a future-predictive edge. This is a
  **coverage optimization, not a number prediction breakthrough**.
  First-prize odds for five distinct tickets stay at
  `5/C(37,7)`; winning/profit is **not guaranteed**.

## Production source snapshot / credential rotation / fixed holdout

### Production source snapshot

金曜13:00〜14:59 JSTのProduction publisherは `fetch_validate.py --production-snapshot` を使用します。
このモードは**直前の確定済み抽せん回を2ソースで検証**しますが、当日のまだ存在しない抽せん結果をfreshness要件として要求しません。
通常発行は金曜13:00〜15:00 JSTを目標にします。GitHub Actions自体が遅延した場合は、同じ事前snapshotを使って19:59 JSTまでRecoveryを許可します。
20:00 JST以降に未発行の場合は当日結果の取得時間帯に入るため、post-outcome leakageを避けてfail closedです。

### Sakura credential rotation verification

過去のcredential exposureに対する完了状態は
`loto7_agent_output/sakura_credential_rotation_status.json` を正本とします。
`pending_external_rotation_verification` の間はrotation完了とは扱いません。

Sakura側でMySQL passwordとHMAC secretを変更し、`credential_generation` を新しい非secret IDへ変更した後、
`Verify Sakura Credential Rotation` workflowを手動実行します。成功条件は以下です。

- rotation timestampが2026-09-06のexposureより後であること
- 新HMACでSakura endpointの認証に成功すること
- GitHub側とSakura側の `credential_generation` が一致すること
- Sakuraが実DB transactionを成功させること
- secret値をGitへ保存しないこと

成功後は `sakura/credential_generation.txt` をcommitし、以後のsyncはgeneration mismatchをfail closedします。
旧DB password/HMACが実際に拒否されること自体は秘密値を再使用して試験せず、rotation timestampのattestationとして記録します。

### Fixed Future OOS holdout

26 trusted drawsの固定holdoutは途中でリセットしません。
`locked_candidate_version`、`locked_config`、開始回、26回horizon、confirmation policyをcanonical JSON化し、
SHA-256を `future_holdout_state.json` の `protocol_lock_sha256` に固定します。
途中変更を検知すると `invalid_protocol_drift` となり、holdout採点を継続しません。

`future_holdout_evidence.py` はRandomと32-member Matched Ensembleを別々に追跡します。
**26/26 trusted drawsが完了するまでは必ず `not_confirmed_holdout_incomplete`** とし、
完了後に両比較が既存Production閾値（平均score差 >= +0.05、勝率 >= 55%、e-value telemetry >= 20）をすべて満たした場合だけ
`confirmed_operational_future_oos_edge` とします。
これは運用上のprospective confirmation ruleであり、portfolio e-processの数学的妥当性そのものを証明する主張ではありません。

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


## 🌐 AIエージェントのブラウザダッシュボード

学習世代、検証済み抽せん、3つの将来検証、5つの監査役、対応事項をスマートフォンからも確認できる読み取り専用画面を追加しました。

- 画面URL（GitHub Pagesを有効化後）: https://joker7822.github.io/LOTO7_AI_AGENT/
- [GitHub Pagesの初期設定・操作手順](docs/README.md) — 初回のみ Settings → Pages → Deploy from a branch → main /docs を設定します。
- 状態JSONは公開mainから2分ごとに更新されます（CDN反映には時間差があります）。本番予測番号・秘密情報は公開画面に表示しません。
- 過去研究の比較と将来の独立検証は明確に区別し、精度向上が証明されたと誤表示しません。


## 高度な統計検証ラボ

複数モデルの選択バイアスを含む公平抽せん実験、時系列ブロック再標本化、未来の事前凍結予測に対する厳密な逐次e値を追加しました。過去研究と本当の未来の証拠を区別します。

- [統計と安全上の設計](ADVANCED_VALIDATION_LAB.md)
- [統合ブラウザダッシュボード](https://joker7822.github.io/LOTO7_AI_AGENT/)
- 既存のProduction・Champion・登録済み将来検証の台帳には変更しません。


## 自律研究とオンライン文献検索

研究エージェントが1時間ごとに既存の研究・将来検証・ソース状態を監査し、6つの重点作業を巡回します。約6サイクルに1回、[Crossref公式API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)（取得できない場合はOpenAlex）で予測校正や逐次統計検定などの新しい公開論文を検索し、書誌メタデータだけを未検証の研究候補として保存します。

- [常時活動と文献検索の設計・安全ルール](ALWAYS_ON_ACCURACY_RESEARCH.md)
- [ブラウザダッシュボード](https://joker7822.github.io/LOTO7_AI_AGENT/)

登録済み将来検証・Production・Championは変更しません。毎時の実行はGitHub Actionsのベストエフォートで、実行遅延とネットワーク障害は可視化します。


## オンライン収集データの横断分析と安全な実用化

Crossref/OpenAlexの収集済みDOI・論文タイトル・発行年・二重ソース照合記録を
**出典SHA検証→テーマ別集計→信頼度別整理→固定の運用検証手順**へ変換する
`online_research_intelligence.py` を追加しました。

GitHub Actionsで6時間ごとに自動実行し、研究データの鮮度、未照合DOI、
研究試行予算と安全な次の作業をJSON/Markdown/CSVで提供します。
文献の全文を読んだことや予測精度向上を装わず、既存Championや
未来OOSの予測・凍結結果は書き換えません。

手順: [ONLINE_RESEARCH_INTELLIGENCE.md](ONLINE_RESEARCH_INTELLIGENCE.md)。

## 4体の専門自律研究エージェント

既存の研究コーディネータを補強するため、独立実行の専門エージェントを
**4体追加**しました。GitHub Actionsが6時間ごと（ベストエフォート）に
4つのジョブを動かし、各エージェントが監査結果をJSON/Markdownとして保存します。

- `source_sentinel`: 抽せん結果の2ソース検証、CSV SHA、研究ガード鮮度。
- `calibration_analyst`: 過去の校正、理論一様基準、統計的な限界。
- `prospective_custodian`: 26回holdout、Joint Set v2、35数字研究の未来凍結監査。
- `literature_examiner`: オンライン論文の独立照合、未承認手法の採用防止。

詳細: [専門エージェント4体の運用・制約](AUTONOMOUS_RESEARCH_SPECIALISTS.md)。

追加エージェントは**読み取り専用**です。Production・Champion・既存の
第701回凍結予測・登録済み将来OOS・研究試行予算に触れず、
予測精度の改善を自動的には認定しません。

## オンライン研究成果を運用に反映する監査

研究文献のテーマを、実際のデータ鮮度・論文根拠・厳密な事前凍結・
将来OOS・券の配置方式の品質監査につなぐ**読み取り専用の運用監査**を追加しました。

- [オンライン研究の運用監査と安全な実用化](ONLINE_RESEARCH_OPERATIONAL_AUDIT.md)
- `online_research_operational_audit.py` は毎日GitHub Actionsで運用上の
  ブロッカーと対処方針をレポート。現行データ第700回と研究レポート第699回の
  古い証跡を識別し、古い分析を本番昇格の証拠にしません。
- 本番Champion・発行済み予測・OOS台帳・研究試行予算は変更しません。
  論文の全文検証・方法論レビュー・事前登録・未知の将来成績なしに
  予測精度が向上したとは扱いません。

## AI論文レビュー・実験設計エージェント

オンライン収集したCrossref/OpenAlexの論文候補をSHA連結の活動証跡で確認し、**タイトル・DOI・発行年だけに基づく一次評価**を行います。6種類の研究テーマに分類して、仮説・公平な基準・過剰適合対策・中止条件を含む**未承認の実験計画書**を自動起案します。全文を調査した査読や、実際の実験・将来登録を自動実行する機能ではありません。

- [研究レビュー・実験設計の仕様](RESEARCH_LITERATURE_PIPELINE.md)
- 新規研究出力: research_literature_reviews.json / research_experiment_proposals.json / research_literature_review_report.md
- WAIT_FOR_NEW_DATAモードでは既存の試行予算を増やさず、Production・Champion・既存Future-OOSを変更しません。

## 研究論文の検証と限定的な自己修復

毎時の研究エージェントに、[論文のDOI・年・タイトルをCrossref/OpenAlexで照合し、公平抽せんの模擬データで統計手法を点検する機能](RESEARCH_EVIDENCE_RESILIENCE.md)を追加しました。通信時の一時的な503/429などを限定回数で再試行し、壊れた**派生研究レポートだけ**を検証済み元台帳から再構築します。

論文の本文・再現実装を検証済みとは見なしません。実抽せん結果の変更、研究ガードの変更、将来登録済みFuture-OOS、Champion、Productionの無断変更、未承認コードの自動実行・マージは行いません。


## オンライン研究から実用化判断までの科学ゲート

オンラインで収集した論文候補を独立照合し、既存の512世界の公平抽せん実験を理論値と照合して、**次に何を検証すべきか**を自動整理します。論文本文の評価・実験実行・Production採用は未承認のまま維持し、既存のFuture-OOSや研究予算を保護します。

- [研究成果の実用化ゲートと検証ルール](RESEARCH_APPLICATION_GATE.md)
- [ブラウザダッシュボード](https://joker7822.github.io/LOTO7_AI_AGENT/)


## 自律研究エージェントの優先順位付け

オンライン論文レビュー・2サービス照合・公平な抽せんの合成検査・研究承認ゲートに続き、**次に何を調査すべきか**を自動的に決める研究プランナーを追加しました。抽せんの2ソース照合待ちやデータの更新遅延を優先し、同じデータを無制限に再学習することはありません。

- [自律研究の優先順位・安全ルール](RESEARCH_AUTONOMY_ORCHESTRATOR.md)
- [自律研究の状況](https://joker7822.github.io/LOTO7_AI_AGENT/)

各候補は承認前の研究作業であり、Future-OOSやProductionの内容・予測精度が改善したことを意味しません。
