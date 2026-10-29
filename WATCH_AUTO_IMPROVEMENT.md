# ダッシュボードの「要確認事項」自動改善

本番Championや将来OOSを変更せず、既存ロール監査で見つかった
「要確認」の**実行可能な研究側の修復と自動検証**を行います。

## 2026年10月29日の実問題

1. **PAIR_CONTEXT_INT8_OVERFLOW**：既存モデルの `pair_context`
   共起回数が`int8`で積算されるため、700回の履歴の27セルが
   オーバーフローしています。監査を隠したり既存モデルを無断で
   書き換えず、別バージョン
   `pair-context-wide-int-v2-research-only` を実装しました。
   整数積算を**行列積の前にint64へ変換**してから実行し、
   誤差なしの共起頻度、確率の正規化、入力値のチェックを確認します。
   さらに最新120回の事前履歴だけを用いた参考再検証で
   旧版とのTop7一致・単独数字の疑似対数スコア差を記録します。
   後付け選択の過去再実行であり、独立した将来検証ではありません。
2. **NO_EARLY_PORTFOLIO_CLAIM**：26回の事前登録された将来検証は
   最新レポートで**7/26回**。未到達はエラーではありません。
   自動作業の対象は「標本が増えたか検証して待機」であり、
   結果の創作、期限後の予測、凍結台帳の書き換えは禁止です。

## 実行

- `.github/workflows/watch_auto_improvement.yml`
- 毎日18:47 JST頃（GitHubのベストエフォート）
- 既存`LOTO7 Agent Role Council`が正常終了した直後
- 手動実行・関連コード変更時
- SHA256付き入力証跡、研究用補正版の監査結果、将来検証待機
  の理由をGitHub Actionsの実行概要・90日保存の成果物として記録
- Gitへの自動書き込みは次の**2ファイルのみ**：
  `loto7_agent_output/watch_auto_improvement_report.json`
  `loto7_agent_output/watch_auto_improvement_report.md`

## 安全性と表示

**旧Productionの警告は、Productionが本当に修正されるまで消しません。**
数値バグを修正した研究用候補が存在しても、
既存Championを変更したことや、予測精度が改善したと
主張しません。登録済み本番/将来予測を動かすには、
別の独立した将来OOSと明示された昇格ガードが必要です。

`WATCH`には正常な26回将来OOS待機も含まれ、
計算バグとは別の理由としてレポートに記載します。
実際の未知コード・ソース信頼異常などは
`needs_existing_workflow_or_human_review`として自動解消を拒否します。

```bash
python -m pytest -q tests/test_watch_auto_improvement.py
python watch_auto_improvement.py --repo-root .
```

参照：
[要確認事項・自動改善Actions](https://github.com/Joker7822/LOTO7_AI_AGENT/actions/workflows/watch_auto_improvement.yml)、
[ロール監査Actions](https://github.com/Joker7822/LOTO7_AI_AGENT/actions/workflows/agent_role_council.yml)

**同じ過去データの試行予算800/800、Champion、
第701回凍結、26回将来検証、Production発行済み券は不変です。**
