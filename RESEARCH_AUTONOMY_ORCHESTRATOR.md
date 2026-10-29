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
