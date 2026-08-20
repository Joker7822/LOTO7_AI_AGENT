# LOTO7 AI Agent

LOTO7の履歴データを毎週更新し、ウォークフォワード検証付きの自己更新型アンサンブルで次回候補を**5通り**生成します。

> 注意: 本プロジェクトは当せんを保証するものではありません。出力スコアはモデル内の相対評価であり、実際の当せん確率ではありません。

## 自動実行

GitHub Actions の `Weekly LOTO7 Update` が毎週金曜日 **20:00 JST（11:00 UTC）** に実行されます。

1. `scrapingloto7.py` で最新のLOTO7結果を取得し `loto7.csv` を更新
2. `loto7_evolving_agent.py` でウォークフォワード再検証・戦略重み更新
3. 最新予測を **5通り**生成
4. `prediction_tracker.py` で過去予測と最新当せん結果を自動照合
5. 等級・当せん金額を累積履歴へ保存
6. 最新予測と累積照合結果をUTF-8テキストへ出力
7. `loto7.csv` と `loto7_agent_output/` の変更をAIエージェント名義で自動コミット

手動実行 (`workflow_dispatch`) にも対応しています。

## AIエージェント権限

ワークフローは `permissions: write-all` を使用し、GitHub Actions の `GITHUB_TOKEN` でワークフローに付与可能なリポジトリ権限をすべて read/write で使用できる設定です。

これは **GitHubアカウント管理者権限やSecretsの内容を無条件に開示する設定ではありません**。Secretsはワークフローが明示的に参照したものだけが利用対象です。

## ローカル実行

```bash
python -m pip install -r requirements.txt

python scrapingloto7.py --csv loto7.csv --months 3

python loto7_evolving_agent.py \
  --csv loto7.csv \
  --tickets 5 \
  --out-dir loto7_agent_output

python prediction_tracker.py \
  --loto-csv loto7.csv \
  --tickets-csv loto7_agent_output/candidate_tickets.csv \
  --history-csv loto7_agent_output/prediction_history.csv \
  --results-txt loto7_agent_output/prediction_results.txt \
  --latest-txt loto7_agent_output/latest_prediction.txt
```

## 予測ロジック

- 直近20/50/100/200回の出現率
- EWMA（半減期10/30/60回）
- 出現間隔
- recent-cold
- 短期モメンタム
- 直前回との過去共起
- ウォークフォワード検証
- Hedge型オンライン重み更新
- 一様分布への縮約による過信抑制
- 5候補間の数字重複を抑えるポートフォリオ生成

## 当選照合

`prediction_tracker.py` は、各対象回の予測5通りを変更せず累積保存し、対象回の結果が `loto7.csv` に入った時点で自動照合します。

等級判定:

- 1等: 本数字7個一致
- 2等: 本数字6個 + ボーナス数字1個以上一致
- 3等: 本数字6個一致
- 4等: 本数字5個一致
- 5等: 本数字4個一致
- 6等: 本数字3個 + ボーナス数字1個以上一致
- その他: はずれ

当選金額は予測値ではなく、対象回の `loto7.csv` に保存された各等級の**実際の当選金額**を使用します。

公式当選条件:
https://www.takarakuji-official.jp/brand/suji/lineup-loto7/

## 出力

### 最新予測

- `loto7_agent_output/candidate_tickets.csv` — 最新候補5通り（CSV）
- `loto7_agent_output/latest_prediction.txt` — 最新候補5通り（閲覧用テキスト）

### 累積履歴・当選結果

- `loto7_agent_output/prediction_history.csv` — 全予測の累積監査履歴
- `loto7_agent_output/prediction_results.txt` — 当選結果・一致数・等級・当選金額の累積閲覧用テキスト

### モデル情報

- `loto7_agent_output/prediction_ranking.csv` — 1〜37のモデル相対順位
- `loto7_agent_output/expert_backtest.csv` — 各戦略の時系列バックテスト
- `loto7_agent_output/agent_state.json` — 最新学習状態と検証統計

## 累積履歴の動作

予測は対象回ごとに一度だけ保存します。同じ対象回についてワークフローを再実行しても、既存の予測5通りを後から書き換えません。

次の抽せん結果が取得されると:

1. 前回保存した5通りを実際の本数字・ボーナス数字と照合
2. 本数字一致数・ボーナス一致数を計算
3. 1等〜6等または「はずれ」を判定
4. `loto7.csv` の実績当選金額を記録
5. 次回向け5通りを新規保存
6. `prediction_results.txt` と `latest_prediction.txt` を再生成

これにより、予測を後から当選結果に合わせて変更しない監査可能な履歴になります。

## 統計上の扱い

モデルは過去データに予測可能な信号があることを前提にしません。ウォークフォワード検証で無作為基準との差を計算し、統計的優位が確認できない場合はその旨を明示します。
