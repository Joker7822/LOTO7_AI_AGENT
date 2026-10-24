# Autonomous Evolution Lab — 自律研究エージェント

更新: 2026-10-24 JST

## スコープ

LOTO7 AI Agentに追加する制約付き自律研究ループです。自己改変する汎用人工知能(AGI)、無制限の自律AIではありません。公平な抽せんで将来の当せん確率が改善した証拠は現時点ではありません。

外部LLM、シークレット、任意のコード生成・実行は必要ありません。

## 自律ループ

1. Observe: CSVのSHA、最新回、研究ガード、独立した結果照合記録を監査
2. Gate: 未検証データ、履歴SHA不一致、研究停止モード、上限到達なら実験を停止
3. Propose: 定義済みの小さなパラメータ範囲で、研究候補を1つずつ生成。4回目だけ過去3候補の履歴診断結果から限定的に変異
4. Test: 直近48回の各抽せんで、それ以前の履歴のみを使い計算。一様モデル比log-score、Top7、16回×3区間を診断
5. Remember: SHA連結のJSONL監査台帳と状態JSONにデータSHA・候補・結果を記録し、改変・不整合なら停止
6. Reflect: 歴史上の「診断リーダー」を保存。ただしProduction Championとは別物
7. Repeat: GitHub Actionsが1日4回再判定。履歴SHAあたり最大4試行で停止し、真正な新しい検証済みデータを待機

## 禁止・保護範囲

- 過去の抽せんCSV、公開Productionの5口、Champion、予測ランキングを書き換えない
- 凍結済みFuture-OOS、事前登録モデル・プロトコルを変更しない
- 公式研究ガード、ソース検証フラグ、シークレットを変更しない
- コード自動編集、任意のシェル実行、GitHub Actionsの無制限再起動をしない
- ワークフローからGitに追加するのは次の3ファイルに限定:
  - loto7_agent_output/autonomous_evolution_state.json
  - loto7_agent_output/autonomous_evolution_journal.jsonl
  - loto7_agent_output/autonomous_evolution_report.md

## 安全と科学的な解釈

- 単一ソースでは実験禁止。「verified_two_result_sources」フラグと直近CSVの日付・数字・独立ソース一致レコードを確認
- 研究ガードの試行上限・停止モードを尊重し、ガード自身を書き換えない。追加の診断試行は独立の履歴別台帳で管理
- 同じ過去48回を使って候補を選んでいるため、歴史上の最良スコアには選択バイアスがある
- 将来の予測優位を主張するには、別に事前登録したFuture-OOSの十分な結果が必要で、本エージェントには自動本番採用権限がない
- 台帳のSHAは偶発的改変・不整合を検出するが、Git管理者による全履歴改変を原理的に排除するものではない
- GitHub Actionsのcronはベストエフォートであり、完全な24時間連続稼働を保証しない

## テストと運用

1. python -m pytest -q tests/test_autonomous_evolution_lab.py
2. python autonomous_evolution_lab.py --repo-root .
3. GitHub Actions: .github/workflows/autonomous_evolution_lab.yml

2026-10-24時点で第700回の結果の独立2ソース照合が未完了の間、WAIT_FOR_INDEPENDENT_RESULT_SOURCEとなり、診断試行は実行されません。
