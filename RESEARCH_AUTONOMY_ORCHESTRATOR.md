# Autonomous Research Priority Orchestrator — 自律研究の優先順位

この機能は新しい予測モデルではなく、既存の論文調査、結果監査、書誌照合、実験承認ゲートの結果から **今、安全に取り組むべき研究の次の作業** を選ぶ自律研究コーディネータです。

## 判定ルール

- **停止**：独立した2ソースで抽せん結果を照合できなければ、未検証結果で予測を採点しない。取得先のHTTP 503などは既存の検証workflowで調査する。
- **要確認**：最後に記録した抽せん日から7日以上、未照合・不一致の論文DOI、未承認の実験計画など。
- **正常な待機**：WAIT_FOR_NEW_DATA と VALIDATION_ONLY は安全な研究ガード。変わらない過去データで無制限に試行を追加しない。

どの作業にも安定したID、担当、優先度、根拠、安全な次の対応、入力SHA256の証拠を持たせます。監査結果が不整合な場合は出力しません。

## 安全な責任分界

research_application_gate.verify_inputs と公平抽せんの合成シミュレーション検査に合格した入力だけを評価します。次の2つの独立したレポートだけを生成します。

- loto7_agent_output/research_autonomy_priority_queue.json
- loto7_agent_output/research_autonomy_priority_report.md

毎時の Always-on Accuracy Research workflow の既存監査に続けて実行します。**新規モデルの訓練、自動PRマージ、Actionsの強制再実行、登録済みFuture-OOSの凍結・台帳変更、Champion昇格、Production予測の変更は行いません。**

## ブラウザ

GitHub Pagesの「自律研究エージェントの活動」に「自律研究の優先アクション」カードを追加します。公開するのはホワイトリストで絞った最大6件のアクションのみ。モデル変更権限の偽装、無効な優先順位、原データ・ガードとの不整合があれば「要確認」として非表示にします。

## 再現テスト

    python -m compileall -q .
    python -m pytest -q
    python -m pytest -q tests/test_research_autonomy_orchestrator.py
    node --test docs/tests/*.test.mjs

GitHub Actionsの時間指定はベストエフォートです。検証や優先順位付けを継続することと、将来のロト7予測精度が上がることは別です。

## 研究アクションの結果フィードバック（2026-10-30 JST）

既存の研究優先順位に、監査対象ごとの**観測値の変化**を追加しました。前回キューは生成から1時間以上・7日以内、同じ抽せん履歴SHA・研究ガード・照合状態である場合のみ参照します。過去キューのID、SHA形式、安全フラグ、優先度の内訳に不整合があれば参照しません。

- `feedback_state` は `new` / `improving` / `worsening` / `unchanged` / `still_pending_unmeasured` の5種類。
- DOI未照合・文献書誌不一致・単一ソース・データ品質指摘の**残件数**を前回と比較します。方法論レビューなど数値化できない作業は「測定不能」と明示します。
- 同じ重大度の中で、残件数増加は +5、減少は -5 を優先スコアに反映します。ただし **block > watch > info** の安全階層を超えることはありません。
- `action_feedback.status_counts` と `no_longer_in_queue` を既存の派生キューに追加します。キューから消えたことは実際の対処成功を証明するものではありません。
- 同一時刻の再実行では継続回数を加算せず、同じ出力を再現します。

**科学的・権限上の制約：** 残件数の減少をエージェントの因果的成果とは呼びません。予測精度改善も意味しません。新規モデル訓練、研究予算の変更、自動マージ、Future-OOSの事後採点、Champion・Production変更は許可しません。既存の毎時ワークフローと既存の2出力だけを使用します。


## 継続強化：停滞・悪化の自動検出（2026-10-30 JST）

毎時の証拠付き研究キューについて、前回キューがSHA・安全フラグ・時刻の検証に合格した場合に限り、アクション単位の注意喚起を追加します。

- 残件数の**実測値が3回連続で不変**なら `stalled_needs_review` に分類。改善・悪化があれば連続停滞回数をリセットします。
- 残件数が増えたら `regression_needs_review`、減ったら `observed_progress` と表示します。件数を測定できない人間のレビューは「失敗」扱いしません。
- 測定不能の作業が4回以上継続した場合のみ `human_review_pending` として担当者へのレビュー注意喚起を出します。
- 同一の重大度内に限り、停滞アクションへの追加スコアは**最大+4点**です。 `block > watch > info` の安全順序は変更しません。
- `agent_attention.review_due_codes` に対象コードを表示しますが、勝手なワークフロー再実行・研究試行追加・コード更新・モデル採用は**行いません**。

停滞回数は最大20に制限し、不正な保存済み履歴は利用しません。研究改善は継続して評価できますが、計算資源・研究予算・GitHub Actionsの実行は無制限にはしません。実際の抽せん結果、凍結済みFuture-OOS、Champion、Productionは引き続き保護対象です。


## AIエージェントの自動強化：安全な方針選択（2026-10-30 JST）

既存の毎時自律研究エージェントで、**3つの定義済みの研究アクション優先方針**を安全に比較し、代理評価が厳密に改善する場合のみ優先順を更新します。

- `balanced`: 従来の検証済み優先順位を維持。
- `regression_focus`: 測定された残件数の悪化を優先して調査。
- `stagnation_focus`: 継続的な未解決・停滞のレビューを優先。

比較する目的関数は「**危険信号を持つ研究タスクを同じ重大度内で上位に置く利益 − 不必要な順位入れ替えの罰則**」です。候補の追加点は最大8点、候補の種類は固定3個で、同点なら従来方針を維持します。新しい評価が良くなければ採用せず、同じ入力から同じ選択を再現します。

選ばれた方針と候補の代理評価値は、既存の `loto7_agent_output/research_autonomy_priority_queue.json` の `action_policy` に保存します。追加の自律的実行権限、無制限の計算、生成コードの本番採用、変更内容の自動マージは提供しません。

**重要な限界：** この評価は研究業務の「注意すべきタスクの優先順位」を測る代理指標です。実際の研究効率向上や、ロト7の未来予測精度を実証するものではありません。既存の `block > watch > info`、`report_only`、研究予算・抽せん原本・Future-OOS・Champion・Productionの保護を維持します。

検証コマンド：

```bash
python -m pytest -q tests/test_research_action_policy.py tests/test_research_autonomy_orchestrator.py
```
