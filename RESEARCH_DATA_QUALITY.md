# Research Priority Auto-Improvement / Data Quality Auto-Recovery

導入日: 2026-10-30 (JST)

## 結論

既存の研究専用キューに、監査済み入力だけで再現できる動的な優先順位と、
原本に触れないデータ品質監査を追加します。**予測成績の改善を実証する機能ではありません。**

## 優先アクションの更新

- 「block > watch > info」の安全階層を最優先で固定し、優先度を越える自動昇格を禁止。
- 同一階層内だけで `priority_score` = `impact` + `verified_backlog` + `unresolved_recurrence` によって並べ替え。
- `impact` は固定された監査対象アクションの影響度、`verified_backlog` はDOI未照合・不一致の記録件数（最大10）、`unresolved_recurrence` は前回キューで解決していない同一アクションの継続回数（最大10）。
- 再発判定は同じ履歴SHA、同じ研究ガード、同じ照合状態で、前回生成から**1時間以上**経過した場合のみ。データ変更時は継続回数をリセット。
- 改ざん・壊れた古い派生キューは使用せず、検証済み元データからキューを再生成。
- `safe_autonomous_action=report_only` を維持。高スコアであってもworkflow dispatch、訓練、採用を許可しません。

## データ品質の監査と修復範囲

`research_data_quality.py` は `loto7.csv` と
`loto7_agent_output/source_validation.json` のバイト列を読み取り、

1. ヘッダーの必須列、ラウンド重複・順序・欠番、日付順、未来日を検査。
2. 本数字7個＋ボーナス2個の一意性・1〜37の範囲・相互非重複を確認。
3. CSV SHA256がソース検証記録の `draw_csv_sha256` と一致するか検査。
4. 最終抽せん回・日付・9数字がソース検証記録と一致するか照合。
5. 独立した2つの**公開結果掲載元**による一致状態を確認。第二ソースが非公式の場合でも「公式2ソース」とは表記しません。
6. 次回の抽せん結果更新遅延は、記録された次回公式日程が利用可能ならそれを優先し、**当日20:00 JST以降**から検出。金曜朝に7日経過していても遅延とはしません。

出力は次の **2つの派生ファイルだけ**です。

- `loto7_agent_output/research_data_quality.json`
- `loto7_agent_output/research_data_quality_report.md`

欠落・破損・古い派生品質レポートは監査済み入力から原子的に再生成します。
監査がblockでも原本を補正せず、research priority queueへ「データ品質要確認」を
blockとして送ります。監査をすり抜けるためにCSVや出典SHAを書き換えることはありません。

**自動修正不可:** `loto7.csv`、`source_validation.json`、
登録済みFuture-OOS、Champion、Production、研究試行予算、第三者論文からの未検証コード。

## 定期実行

既存 `always_on_accuracy_research.yml` の毎時ベストエフォート実行で、
研究ゲート生成の後、優先キュー生成の前に品質監査を実行します。
PRでは固定入力の隔離スモーク試験を行います。品質レポートだけを
既存の研究専用成果物ホワイトリストに追加しました。

## 検証

```bash
python -m pytest -q tests/test_research_data_quality.py
python -m pytest -q tests/test_research_autonomy_orchestrator.py
python research_data_quality.py --repo-root .
python research_autonomy_orchestrator.py --repo-root .
```

予測精度の改善は、この機能では認定できません。将来の独立OOS検証と
Production安全ゲートの条件は従来どおり維持します。
