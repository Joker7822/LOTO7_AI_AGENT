# Autonomous Research Priority Queue

- Generated: 2026-10-24T09:46:29+09:00
- Guard: **WAIT_FOR_NEW_DATA**; verified draw source: **False**
- Priorities: block=1, watch=8, info=3
- Read-only; does not launch workflows, change Production or create future grades.

1. **[block] 抽せん結果の独立2ソース照合**
   - Assigned: source_verifier / source_integrity
   - Reason: 照合済みでない最新結果を採点や新規予測の凍結に利用できません。
   - Next: 既存の結果検証workflowと独立した発表元を照合してください。単一ソースで成功扱いしません。
2. **[watch] 最新の抽せんデータ更新を確認**
   - Assigned: source_verifier / source_integrity
   - Reason: 記録された最終抽せん日から 8 日が経過しています。
   - Next: 公式抽せん日程と検証済み結果を確認し、取得先HTTP 503等の通信障害は既存の再試行手順で調査してください。
3. **[watch] 文献書誌情報の不一致を確認**
   - Assigned: literature_verifier / bibliography
   - Reason: 1 件のDOIで独立サービスの書誌照合結果が不一致です。
   - Next: 元のDOIと著者・タイトルを確認してください。対立するメタデータから研究計画を承認しないでください。
4. **[watch] 未照合の学術文献を一次確認**
   - Assigned: literature_verifier / bibliography
   - Reason: 7 件の候補DOIがCrossref/OpenAlexによる照合待ちです。
   - Next: 既存の上限付き照合を次の定期サイクルで続けてください。未照合論文を学術的根拠として扱わないでください。
5. **[watch] 研究計画レビュー：anytime_evidence**
   - Assigned: methodology_reviewer / experiment_review
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
6. **[watch] 研究計画レビュー：calibration**
   - Assigned: methodology_reviewer / experiment_review
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
7. **[watch] 研究計画レビュー：distribution_shift**
   - Assigned: methodology_reviewer / experiment_review
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
8. **[watch] 研究計画レビュー：ensemble**
   - Assigned: methodology_reviewer / experiment_review
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
9. **[watch] 研究計画レビュー：online_evaluation**
   - Assigned: methodology_reviewer / experiment_review
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
10. **[info] 真正将来検証の標本数を確保**
   - Assigned: oos_custodian / prospective_integrity
   - Reason: 第701回開始の登録済み検証で、精度改善と呼べるだけの実測がありません。
   - Next: 既存の事前登録と凍結手順を守り、抽せん結果が出た後の遡及的な予測作成はしないでください。
11. **[info] 片側の論文登録サービスを再確認**
   - Assigned: literature_verifier / bibliography
   - Reason: 片側のみ検証された論文が 1 件あります。
   - Next: 既存workflowの接続復旧・上限付き再試行で確認してください。2ソース照合済みと偽りません。
12. **[info] 同一履歴の新規探索を停止**
   - Assigned: research_governor / research_governance
   - Reason: 研究ガードが WAIT_FOR_NEW_DATA のため、探索を再開しません。
   - Next: 新しい検証済み結果を待つ間、データ品質監査・文献照合・未承認実験計画の準備だけを続けてください。

Historical research alone is not evidence of lottery prediction ability.
