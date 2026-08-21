# LOTO7 AI Agent v3 — Continuous Evolution

LOTO7履歴を使い、**バックテスト完了 → Challenger生成・統計検証 → 研究世代更新 → 保存 → 待ち時間なしで次のバックテスト開始**を繰り返す継続進化型エージェントです。

> 予測は当せんを保証しません。ランダム基準や現行Championを上回ったかを継続検証し、改善が確認できないモデルは本番昇格させません。

## 連続自動進化

GitHub Actions `Continuous LOTO7 Evolution v3` は、1回ごとの固定時刻実行ではなく、1つのランナー内でバックテストを連続実行します。

1. ランナー起動時にpytestを実行
2. 最新公開結果を定期取得・形式検証
3. 金曜日20〜21時台に新結果が未反映なら10分間隔で最大90分再試行
4. 楽天の結果を主取得元として利用
5. みずほ銀行の同一回を解析できた場合は本数字・ボーナス数字をクロスチェック
6. 直前実行の研究Winnerを研究親モデルとして継承
7. 1反復あたり6個の新しい変異Challengerを自動生成
8. Champion・研究Winner・新規Challengerを30/60/120回窓でバックテスト
9. ランダム5通りとも比較
10. paired sign-flip検定を実施
11. 各反復の多重検定をBonferroni補正
12. 同一データを繰り返し検証する影響をalpha-spendingで追加補正
13. 条件を満たす場合のみChampion昇格
14. 同一 `loto7.csv` SHA256ではChampion昇格を最大1回に制限
15. 本番予測5通りと研究予測5通りを別々に生成
16. 実測時間・進化履歴・予測・実績・当選照合をコミット
17. **コミット完了後、sleepを入れず直ちに次の反復を開始**

1つのGitHub Actionsランナーは約4時間連続反復し、正常終了時に次のランナーを`workflow_dispatch`で自動起動します。さらに毎日02:00 JSTに回復用スケジュールがあり、連鎖が停止していた場合の再起動点になります。

公開結果サイトへのアクセスは研究反復ごとには行わず、通常は最大1時間間隔、金曜20〜21時台は最大10分間隔に制限します。バックテスト・モデル探索そのものは待ち時間なしで連続します。

## 実行時間の実測

各反復の実測時間を以下へ累積します。

- `loto7_agent_output/execution_metrics.csv`
- `STATUS.md` の `Continuous Runtime`

記録項目:

- 完了日時(JST)
- ランナー内反復番号
- 進化世代
- 実行秒数
- データSHA256
- Champion
- 研究Winner

`STATUS.md` には最新1回の秒数、直近20回平均、累積実測回数を表示します。初回連続実行前は十分な本番実測値がないため、所要時間を確定値として扱いません。

## 「進化し続ける」の意味

### 研究系統

各反復の研究Winnerのパラメータを `evolution_state.json` に保存し、次の反復ではそのモデルを親として新しい変異候補を生成します。

これにより、Championに昇格しなかった研究モデルも次の探索に利用でき、**実行時間が許す限り世代を連続継承する探索系統**になります。

### 本番Champion

研究モデルを無条件に本番採用しません。

昇格には以下を要求します。

- 直近30回: Champion以上
- 直近60回: Championよりスコア改善
- 直近120回: Championよりスコア改善
- 60/120回で最大一致数を悪化させない
- 120回でランダム基準を上回る
- paired sign-flip検定を通過
- 同一反復内の複数Challenger数を考慮した補正済み有意水準を通過
- 同じ抽せんデータでの反復検定を考慮したalpha-spendingを通過

同一データSHAで一度Championが昇格した後は、次の抽せん結果でデータSHAが変わるまで追加昇格を禁止します。実行回数を増やしても、この制限は緩和しません。

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

### 継続研究予測

- `loto7_agent_output/research_candidate_tickets.csv`
- `loto7_agent_output/latest_research_prediction.txt`

研究予測は**各反復で更新**されます。本番監査履歴とは別物です。

## 進化状態・履歴

- `loto7_agent_output/evolution_state.json` — 現在の世代、研究親、Champion、累積評価数、昇格ロック状態
- `loto7_agent_output/evolution_history.jsonl` — 各反復の進化履歴
- `loto7_agent_output/model_evaluation.json` — 最新世代の全バックテスト結果と昇格判定
- `loto7_agent_output/model_champion.json` — 現行Champion
- `loto7_agent_output/agent_state.json` — 最新AI状態
- `loto7_agent_output/execution_metrics.csv` — 各反復の実測所要時間

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

GitHub Actionsは連続運用に必要な範囲に限定します。

```yaml
permissions:
  contents: write
  actions: write
```

`contents: write` は監査・進化状態の自動コミット、`actions: write` は正常終了後に次の同一ワークフローを`workflow_dispatch`するために使用します。アカウント管理権限やSecretsの無条件閲覧権限ではありません。

## CI

`.github/workflows/ci.yml` がPull Requestとmainへのpushで以下を確認します。

- Python compile
- pytest
- v3の継続進化安全策
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
