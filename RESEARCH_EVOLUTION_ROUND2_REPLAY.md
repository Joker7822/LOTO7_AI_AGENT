# 研究自己進化 → 第2回から全件再予測

更新日: **2026-11-03（日本時間）**

## 結論

既存の「公開論文/公開Webの収集・書誌照合」「再帰的な数式と変異戦略の自己進化」を、
更新ごとの**第2回から最新確認回までの研究用再予測**に接続する。
実装は `research_cycle_round2_replay.py`、自動化は
`.github/workflows/research_evolution_round2_replay.yml`。

これによって、同じ当せん履歴から選択済みの研究モデルを最新のチェックポイントで
**全期間再適用した場合に何が起こるか**を数値比較できる。
過去に実際に発行された予測を置換したことにはならない。

## 研究の入力と評価の流れ

1. 既存 `always_on_accuracy_agent.py` 等が公開 API / Web の候補を収集。
2. `online_literature_auto_verify.py` は Crossref と OpenAlex で DOI・題名・年を照合。
   これは**書誌照合**であり論文本文の実験再現ではない。
3. 既存 `recursive_self_evolution_agent.py` は
   監査付き制限 AST 上で数式を進化し、変異演算子の試行履歴から選択確率も更新。
   これは論文本文を自動でコード化するものではない。
4. この新ワークフローはモデルの SHA 連鎖状態・CSV SHA・抽せん結果の独立ソースを照合。
   不整合の場合は**再計算を中止**。
5. 最新の研究チャンピオンの数式を第2回から各回に再適用し、
   **第2〜100回は一様確率（履歴不足）**、第101回以降は各回より前の履歴だけから
   37個の包含確率・上位7数字・研究用5口を生成。
6. 予測と確率の SHA-256 を計算してから当該回の正解と照合。
   上位7一致数、5口最大一致数、37指標平均の Bernoulli log/Brier score の
   一様基準との差をまとめる。
7. 再予測全件を GitHub Actions **artifact** に保存（30日間）。
   Champion・Production・発行済み予測・未来 OOS 台帳・研究予算は一切書き換えない。

**自動実行:** 「Recursive Code and Meta Evolution」、
「Open-ended Autonomous Evolution」、「Auto Verify All Online Research References」、
「Always-on Accuracy Research」の成功した実行完了時に再評価する。
加えて6時間ごとの予備スケジュールと手動実行を設定。
GitHub の実行・キュー・無料枠により、毎回即時完了する保証はない。
研究用の再計算は最新の **recursive** チャンピオンを使用する。
open-ended 更新や DOI 更新そのものが、新しいモデル実装に昇格するわけではない。

## 研究論文と検証根拠

- **Bergmeir, Hyndman & Koo, 2018**.
  *A note on the validity of cross-validation for evaluating autoregressive
  time series prediction.* Computational Statistics & Data Analysis 120, 70–83.
  DOI: https://doi.org/10.1016/j.csda.2017.11.003
  時系列評価では、通常の分割手法を無条件に正当化できない。
  この実装は少なくとも各ターゲットの**予測入力を過去に限定**する。
  ただし**候補モデルは履歴全体を見た後に選ばれている**ので、
  厳密な入れ子型（nested）OOS と同等とは主張しない。
- **White, 2000**.
  *A Reality Check for Data Snooping.* Econometrica 68(5), 1097–1126.
  DOI: https://doi.org/10.1111/1468-0262.00152
  多数の候補を同じ履歴で試すと、偶然の高評価を取り込む危険がある。
  再予測報告には `expression_selected_with_hindsight: true` と
  `independent_prospective_evidence: false` を固定する。

上の論文は評価・解釈の設計根拠であり、ロト7の予測優位性を実証していない。
現在の書誌候補から**新しい任意コードを自動生成・実行しない**。
新しい手法の自動実装・因果的な適用性・著者のコードの再現まで
完了したとは扱わない。必要なら本文と公開コードの追加検証が必要。

ロト7は 1〜37 の異なる数字7つを選ぶ商品。
基準の条件付き一様モデルでは、1組の1等確率は
`1 / C(37,7) = 1 / 10,295,472` であり、
過去のスコア改善が将来の当せん確率改善につながると確認されていない。
規則: https://www.mizuhobank.co.jp/takarakuji/products/loto7/index.html

## 実行と確認

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q tests/test_research_cycle_round2_replay.py
python research_cycle_round2_replay.py \
    --repo-root . \
    --out research_output/verified_research_round2_reforecast.json
```

ファイルには `candidate.generation`、
`candidate.checkpoint_record_sha256`、`data_sha256`、
`bibliography`、各回の `forecast_sha256`、
`summary.evolved_101_onward` と `rounds` を含む。

これまでの `full_round2_reforecast.py` は固定研究ベースラインを
比較する別プロトコルとして残す。**新しい再予測は、そのベースラインの
履歴改竄や既存レポートの静かな上書きをしない。**

## 制約

- 研究エージェントが生成した**数学表現**のみを、既存の制限 AST パーサで評価。
  外部 URL、論文タイトル、取得 HTML、生成された任意 Python コードを実行しない。
- 過去の抽せん結果を何度も評価に使うため、結果は**探索的・回顧的**。
  予測の前に数式を選択・凍結した独立将来試験とは違う。
- 既存の研究チャンピオンが同じままでも、新しい研究更新ごとに
  同じモデルで全件を再計算して記録する。これを性能の向上とは呼ばない。
- 全自動で論文本文を読解して未知の手法を採用する機能や、
  改善が立証されたモデルの自動本番昇格は**今回実装していない**。
