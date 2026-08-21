# LOTO7 AI Agent v2

LOTO7の履歴を毎週更新し、**最新結果の鮮度確認 → 複数ソース検証 → 5通り単位バックテスト → Champion/Challenger選択 → 最新5通り予測 → append-only監査台帳 → 当選照合**を自動実行します。

> 予測は当せんを保証しません。モデルがランダム基準を上回ったかを継続的に検証し、改善が確認できないChallengerは昇格させません。

## 自動実行

GitHub Actions `Weekly LOTO7 Update v2` は毎週金曜日 **20:00 JST（11:00 UTC）** に開始します。

1. pytestで回帰テスト
2. 楽天バックナンバーから最新結果を取得
3. 金曜20時時点で最新回が未反映なら10分間隔で最大90分再試行
4. 本数字7個・ボーナス2個・重複・1〜37範囲を検証
5. みずほ銀行の同一回結果を取得できた場合は楽天と本数字・ボーナス数字を照合
6. 2ソース間で不一致なら処理停止
7. みずほ側が解析できない場合は `degraded_single_result_source` として明示
8. Champion/Challengerを直近60回・120回の5券ポートフォリオで比較
9. 両評価窓でChampionを上回ったChallengerのみ昇格
10. 最新5通りを生成
11. 予測・実績を別々のappend-only台帳へ保存し、照合結果を再生成
12. `STATUS.md` と閲覧用テキストを更新し、自動コミット

## 権限

GitHub Actionsは最小権限で運用します。

```yaml
permissions:
  contents: write
```

`write-all` は使用しません。予測性能に不要な権限を付与しないためです。

## データ取得・検証

- 主取得元: 楽天×宝くじ ロト7バックナンバー
- 照合元: みずほ銀行 当せん番号案内（ロト7）
- スケジュール確認: 宝くじ公式サイト

`loto7_agent_output/source_validation.json` に、取得時刻・最新回・鮮度条件・ソース照合状態を保存します。

## 自己進化 / Champion-Challenger

`loto7_v2_runner.py` が現行Championと複数Challengerを同じ時系列条件で評価します。各過去時点では、その時点より前のデータだけを使用します。

評価対象は「数字ランキング」だけではなく、実際の出力と同じ**5通り**です。

主な指標:

- 5通り中の最大本数字一致数
- 5通り平均一致数
- 5通りのどれかが3個以上一致した割合
- 5通りのどれかが4個以上一致した割合
- 同条件のランダム5通りとの差
- 直近60回と120回の両窓

Challengerは60回・120回の両方でスコア改善し、最大一致数を悪化させない場合だけ昇格できます。

## 監査台帳

### 不変の予測台帳

`loto7_agent_output/predictions.csv`

予測作成時点の以下を保存し、後から当選結果に合わせて変更しません。

- 対象回
- 予測5通り
- 作成時刻
- モデルバージョン
- Git SHA
- データSHA256
- 戦略重み

### 実績スナップショット台帳

`loto7_agent_output/actual_results.csv`

当選結果と各等級の実績当選金額を別台帳へ追加します。後日金額が補完・訂正された場合も、古いスナップショットを消さず新しい版を追加します。

### 派生照合結果

`loto7_agent_output/reconciliation.csv`

予測台帳と実績台帳から毎回再生成します。1〜6等条件、本数字一致、ボーナス一致、実績当選金額、1口300円を基準にした差引を記録します。

`loto7_agent_output/prediction_results.txt` では、累積購入額・当選額・差引・回収率も確認できます。

## 主な出力

- `STATUS.md` — 最新取得回、最新予測対象、モデル、データSHA、ソース検証状態
- `loto7_agent_output/latest_prediction.txt` — 最新予測5通り
- `loto7_agent_output/prediction_results.txt` — 累積当選照合・収支
- `loto7_agent_output/predictions.csv` — append-only予測台帳
- `loto7_agent_output/actual_results.csv` — append-only実績台帳
- `loto7_agent_output/reconciliation.csv` — 派生照合結果
- `loto7_agent_output/model_champion.json` — 現行Champion
- `loto7_agent_output/model_evaluation.json` — Champion/Challenger比較
- `loto7_agent_output/source_validation.json` — 複数ソース検証
- `loto7_agent_output/agent_state.json` — モデル・データ・検証状態

## ローカル実行

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
python fetch_validate.py --csv loto7.csv --max-attempts 1 --interval-seconds 0
python loto7_v2_runner.py --csv loto7.csv --tickets 5 --out-dir loto7_agent_output
python audit_ledger.py --loto-csv loto7.csv --tickets-csv loto7_agent_output/candidate_tickets.csv --out-dir loto7_agent_output --status-md STATUS.md
```

## 公式当せん条件

ロト7の等級条件は宝くじ公式サイトの条件に従います。2等は本数字6個＋ボーナス1個、6等は本数字3個＋ボーナス1個または2個です。
