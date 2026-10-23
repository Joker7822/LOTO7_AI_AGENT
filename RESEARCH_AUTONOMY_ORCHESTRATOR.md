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
