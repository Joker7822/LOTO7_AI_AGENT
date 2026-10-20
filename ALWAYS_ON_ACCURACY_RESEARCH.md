# Always-on Accuracy Research Agent

## 目的と「常時活動」の意味

GitHub Actionsが **毎時17分（UTC）のベストエフォート**で動き、毎回最新の原データ・研究ガード・26回固定holdout・v2・継続学習・第5モデル候補・高度統計ラボの整合性を監査し、そのあと重点作業を1つ巡回します。GitHubによるスケジュール遅延や停止もあるため、**24時間動くサーバープロセス**だとは主張しません。最終活動日時と実行状態はダッシュボードから確認できます。

1. 抽せんデータの信頼性・鮮度
2. 未来の予測凍結と採点の保護
3. 多重比較・過剰適合の診断
4. 未来の校正・厳密な逐次e値の点検
5. **オンライン研究文献検索**
6. 同一データでの試行予算・次に行う検証の準備

すべての回で安全監査は実施しますが、同じデータで予測モデルを無制限に再探索することはありません。研究ガードが VALIDATION_ONLY/WAIT_FOR_NEW_DATA なら検証だけを続けます。

## オンラインから何を取得するか

Crossrefの公式の**公開REST API**にアクセスして、予め人が選んだ6種類の関連研究トピックを順番に調べます。毎回1トピックを検索し、最大4件の新規論文メタデータ（タイトル・DOI・公開年）を取得します。

- online probabilistic forecasting calibration
- prequential prediction test then train
- betting martingales e values sequential testing
- time series conformal prediction drift
- multiple comparisons backtest overfitting
- ensemble probabilistic forecast verification

公開日・DOI・タイトルを検査して重複排除し、候補は最大36件に制限します。Crossrefから不明な実行コード、PDF、長文、利用者の認証情報や予測番号は取得・保存しません。リンクは \`doi.org\` のみ許可します。

**研究文献の記載内容を、予測精度の改善やコード変更の根拠として即時採用しません。** 論文の新規性・再現性・適用対象・比較方法・抽せんの独立性・ライセンスを別途評価し、必要なら新しい研究だけを別途事前登録します。外部資料に「システム指示を無視しろ」と書かれても命令として実行しない設計です。

Crossref公式API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/

## 活動履歴・改ざん防止

エージェントが書き込めるのは以下3ファイルだけです。

- \`loto7_agent_output/always_on_accuracy_research_journal.jsonl\`: 連続するSHA256鎖で活動を記録
- \`loto7_agent_output/always_on_accuracy_research_state.json\`: 最新活動・研究ガード・未検証の論文候補
- \`loto7_agent_output/always_on_accuracy_research_report.md\`: 人向け活動報告

同一履歴での試行予算は既存の \`research_cycle_guard.json\` に委譲し、それ自体を増やさない。もし入力が欠ける・未来台帳と真正採点数が矛盾する・SHA鎖が書き換えられるなどの異常があれば**停止**します。Crossrefだけが落ちた場合は \`online_unavailable\` と表示して次の監査を継続します。

ダッシュボードの「自律研究エージェントの活動」には最終日時・累計活動回数・今回の監査・研究モード・検索状況・未検証論文候補が表示されます。

## 安全性

**禁止:** 予測番号の後出し作成や更新、元データの書き換え、研究予算を無視した継続探索、登録済みFuture-OOS台帳の変更、Champion / Productionの昇格・発行、未検証の外部コード実行、オンライン論文を読んだだけで精度向上と主張すること。

**許可:** 原データの品質監査、研究不足の説明、過剰適合防止、限定的な論文検索、検索候補の未査読・未検証リスト化、改ざん検知できる活動記録、ダッシュボードでの表示。

## 実行確認

    python -m pytest -q tests/test_always_on_accuracy_agent.py
    python always_on_accuracy_agent.py --repo-root .

GitHub Actionsは \`.github/workflows/always_on_accuracy_research.yml\`。PRでは独立した一時フォルダーでドライランし、mainの科学的データを変更しません。ネットワーク検索は約6時間に1回の予定ですが、Actionsの遅延、制限、ネットワーク障害で実際の間隔が長くなることがあります。
