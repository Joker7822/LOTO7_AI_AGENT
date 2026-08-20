# LOTO7 AI Agent

LOTO7の履歴データを毎週更新し、ウォークフォワード検証付きの自己更新型アンサンブルで次回候補を**5通り**生成します。

> 注意: 本プロジェクトは当せんを保証するものではありません。出力スコアはモデル内の相対評価であり、実際の当せん確率ではありません。

## 自動実行

GitHub Actions の `Weekly LOTO7 Update` が毎週金曜日 **20:00 JST（11:00 UTC）** に実行されます。

1. `scrapingloto7.py` で最新のLOTO7結果を取得し `loto7.csv` を更新
2. `loto7_evolving_agent.py` でウォークフォワード再検証・戦略重み更新
3. 最新予測を **5通り**生成
4. `loto7.csv` と `loto7_agent_output/` の変更を自動コミット

手動実行 (`workflow_dispatch`) にも対応しています。

## ローカル実行

```bash
python -m pip install -r requirements.txt
python scrapingloto7.py --csv loto7.csv --months 3
python loto7_evolving_agent.py --csv loto7.csv --tickets 5 --out-dir loto7_agent_output
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

## 出力

- `loto7_agent_output/candidate_tickets.csv` — 最新候補 **5通り**
- `loto7_agent_output/prediction_ranking.csv` — 1〜37のモデル相対順位
- `loto7_agent_output/expert_backtest.csv` — 各戦略の時系列バックテスト
- `loto7_agent_output/agent_state.json` — 最新学習状態と検証統計

## 統計上の扱い

モデルは過去データに予測可能な信号があることを前提にしません。ウォークフォワード検証で無作為基準との差を計算し、統計的優位が確認できない場合はその旨を明示します。
