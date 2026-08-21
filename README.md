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

## 連続GitHub Actions

使用するworkflowは2本だけです。

- `.github/workflows/continuous_loto7_v4.yml` — 継続研究・OOS評価・監査
- `.github/workflows/ci.yml` — コード変更時のcompile / pytest

旧v3の `weekly_loto7.yml` と、一回性の `start_continuous_now.yml` は削除しています。

`Continuous LOTO7 Research v4` は1ランナー内で約4時間研究を繰り返し、正常終了時に次のランナーを起動します。毎日02:00 JSTのスケジュールは回復用です。

公開結果サイトへのアクセスは研究世代ごとには行わず、通常は最大1時間間隔です。金曜日20〜21時台は新結果待ちのため10分間隔・最大90分再試行します。

## Git checkpointとCI負荷

研究計算は連続しますが、Gitへは原則**10世代ごと**にcheckpointします。新データ取得・OOS採点・shadow凍結・Champion昇格など重要イベント時は即checkpointします。

CIは以下の変更時だけ起動します。

- Pythonコード
- `tests/**`
- `requirements.txt`
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
- クロスチェック元: みずほ銀行 当せん番号案内
- スケジュール確認: 宝くじ公式サイト

取得結果が食い違った場合は処理を停止します。第2ソースを機械解析できない場合は `degraded_single_result_source` とし、研究は継続しますがProduction昇格用OOS証拠には数えません。

## ローカル検証

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m compileall -q .
python -m pytest -q

python fetch_validate.py --csv loto7.csv --max-attempts 1 --interval-seconds 0
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
