# LOTO7 AI Agent v3 — Continuous Evolution

LOTO7履歴を使い、**毎日バックテスト → Challenger生成 → 統計検証 → 研究世代更新 → 条件を満たした場合のみChampion昇格 → 5通り予測 → append-only監査**を自動実行する継続進化型エージェントです。

> 予測は当せんを保証しません。ランダム基準や現行Championを上回ったかを継続検証し、改善が確認できないモデルは本番昇格させません。

## 毎日20:00 JSTに自動進化

GitHub Actions `Daily LOTO7 Evolution v3` は **毎日20:00 JST（11:00 UTC）** に実行します。

1. pytest / compileチェック
2. 最新公開結果を取得・形式検証
3. 金曜日に新結果が未反映なら10分間隔で最大90分再試行
4. 楽天の結果を主取得元として利用
5. みずほ銀行の同一回を解析できた場合は本数字・ボーナス数字をクロスチェック
6. 前日の研究Winnerを研究親モデルとして継承
7. 毎日6個の新しい変異Challengerを自動生成
8. Champion・前日研究Winner・新規Challengerを30/60/120回窓でバックテスト
9. ランダム5通りとも比較
10. paired sign-flip検定を実施
11. 日次の多重検定をBonferroni補正
12. 同一データを毎日再検証する影響をalpha-spendingで追加補正
13. 条件を満たす場合のみChampion昇格
14. 同一 `loto7.csv` SHA256ではChampion昇格を最大1回に制限
15. 本番予測5通りと日次研究予測5通りを別々に生成
16. 進化履歴・予測・実績・当選照合を自動コミット

## 「進化し続ける」の意味

### 研究系統

毎日の研究Winnerのパラメータを `evolution_state.json` に保存し、翌日はそのモデルを親として新しい変異候補を生成します。

これにより、Championに昇格しなかった研究モデルも翌日の探索に利用でき、**日次で世代を継承する探索系統**になります。

### 本番Champion

研究モデルを無条件に本番採用しません。

昇格には以下を要求します。

- 直近30回: Champion以上
- 直近60回: Championよりスコア改善
- 直近120回: Championよりスコア改善
- 60/120回で最大一致数を悪化させない
- 120回でランダム基準を上回る
- paired sign-flip検定を通過
- 当日の複数Challenger数を考慮した補正済み有意水準を通過
- 同じ抽せんデータでの反復検定を考慮したalpha-spendingを通過

同一データSHAで一度Championが昇格した後は、次の抽せん結果でデータSHAが変わるまで追加昇格を禁止します。

## 5通り単位のバックテスト

数字ランキングだけでなく、実際の出力と同じ**5通りポートフォリオ**を評価します。

主な指標:

- 5通り中の最大本数字一致数
- 5通り平均一致数
- 3個以上一致した券が1枚以上あった割合
- 4個以上一致した券が1枚以上あった割合
- 複合スコア
- 同条件ランダム5通りとの差
- Championとのpaired差

## 本番予測と研究予測を分離

### 本番予測

- `loto7_agent_output/candidate_tickets.csv`
- `loto7_agent_output/latest_prediction.txt`
- `loto7_agent_output/predictions.csv`

`predictions.csv` はappend-onlyです。対象回について一度保存した本番予測を、後日の研究結果や当選結果に合わせて変更しません。

### 日次研究予測

- `loto7_agent_output/research_candidate_tickets.csv`
- `loto7_agent_output/latest_research_prediction.txt`

研究予測は**毎日更新**されます。本番監査履歴とは別物です。

## 進化状態・履歴

- `loto7_agent_output/evolution_state.json` — 現在の世代、研究親、Champion、累積評価数、昇格ロック状態
- `loto7_agent_output/evolution_history.jsonl` — 日次進化履歴
- `loto7_agent_output/model_evaluation.json` — 最新世代の全バックテスト結果と昇格判定
- `loto7_agent_output/model_champion.json` — 現行Champion
- `loto7_agent_output/agent_state.json` — 最新AI状態

`evolution_history.jsonl` は前レコードのハッシュを次レコードに含める**ハッシュチェーン**形式で、履歴改変を検知しやすくしています。

## 当選照合・収支

- `loto7_agent_output/actual_results.csv` — append-only実績スナップショット
- `loto7_agent_output/reconciliation.csv` — 予測と実績の照合
- `loto7_agent_output/prediction_results.txt` — 人間向け累積結果

記録項目には、本数字一致数、ボーナス一致数、1〜6等、実績当選金額、1口300円基準の購入額・差引・回収率を含みます。

## データ取得・検証

- 主取得元: 楽天×宝くじ ロト7バックナンバー
- クロスチェック元: みずほ銀行 当せん番号案内
- スケジュール確認: 宝くじ公式サイト

不一致を検出した場合は処理を停止します。第2ソースを機械解析できない場合は `degraded_single_result_source` と明示します。

## 権限

GitHub Actionsは最小権限です。

```yaml
permissions:
  contents: write
```

予測性能と無関係な `write-all` は使用しません。

## CI

`.github/workflows/ci.yml` がPull Requestとmainへのpushで以下を確認します。

- Python compile
- pytest
- v3の日次進化安全策
- 等級判定
- 鮮度ゲート
- 複数ソース解析
- Champion/Challenger判定

## ローカル実行

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q

python fetch_validate.py --csv loto7.csv --max-attempts 1 --interval-seconds 0

python loto7_v3_runner.py \
  --csv loto7.csv \
  --tickets 5 \
  --mutants 6 \
  --out-dir loto7_agent_output

python audit_ledger.py \
  --loto-csv loto7.csv \
  --tickets-csv loto7_agent_output/candidate_tickets.csv \
  --out-dir loto7_agent_output \
  --status-md STATUS.md

python evolution_status.py
```

## 公式当せん条件

ロト7の等級条件は宝くじ公式の条件に従います。2等は本数字6個＋ボーナス1個、6等は本数字3個＋ボーナス1個または2個です。
