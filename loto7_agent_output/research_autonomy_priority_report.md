# Autonomous Research Priority Queue

- Generated: 2026-10-30T10:17:35+09:00
- Guard: **WAIT_FOR_NEW_DATA**; verified draw source: **True**
- Priorities: block=0, watch=8, info=3
- Read-only; does not launch workflows, change Production or create future grades.
- Observed backlog changes are NOT causal evidence of agent effectiveness.
- Feedback: new=11, improving=0, worsening=0, unchanged=0, still_pending_unmeasured=0
- Attention due: 0 tasks (advisory only).

1. **[watch] 文献書誌情報の不一致を確認**
   - Assigned: literature_verifier / bibliography
   - Observed: new; backlog=4; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 4 件のDOIで独立サービスの書誌照合結果が不一致です。
   - Next: 元のDOIと著者・タイトルを確認してください。対立するメタデータから研究計画を承認しないでください。
2. **[watch] 未照合の学術文献を一次確認**
   - Assigned: literature_verifier / bibliography
   - Observed: new; backlog=8; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 8 件の候補DOIがCrossref/OpenAlexによる照合待ちです。
   - Next: 既存の上限付き照合を次の定期サイクルで続けてください。未照合論文を学術的根拠として扱わないでください。
3. **[watch] 研究計画レビュー：anytime_evidence**
   - Assigned: methodology_reviewer / experiment_review
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
4. **[watch] 研究計画レビュー：calibration**
   - Assigned: methodology_reviewer / experiment_review
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
5. **[watch] 研究計画レビュー：distribution_shift**
   - Assigned: methodology_reviewer / experiment_review
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
6. **[watch] 研究計画レビュー：ensemble**
   - Assigned: methodology_reviewer / experiment_review
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
7. **[watch] 研究計画レビュー：online_evaluation**
   - Assigned: methodology_reviewer / experiment_review
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
8. **[watch] 研究計画レビュー：selection_bias**
   - Assigned: methodology_reviewer / experiment_review
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。
   - Next: Verify DOI/title/year with both Crossref and OpenAlex before reading methodology. 人の明示的な承認がない限り研究試行も本番採用も行いません。
9. **[info] 片側の論文登録サービスを再確認**
   - Assigned: literature_verifier / bibliography
   - Observed: new; backlog=1; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 片側のみ検証された論文が 1 件あります。
   - Next: 既存workflowの接続復旧・上限付き再試行で確認してください。2ソース照合済みと偽りません。
10. **[info] 真正将来検証の標本数を確保**
   - Assigned: oos_custodian / prospective_integrity
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 第701回開始の登録済み検証で、精度改善と呼べるだけの実測がありません。
   - Next: 既存の事前登録と凍結手順を守り、抽せん結果が出た後の遡及的な予測作成はしないでください。
11. **[info] 同一履歴の新規探索を停止**
   - Assigned: research_governor / research_governance
   - Observed: new; backlog=None; delta=None
   - Agent attention: routine_monitoring; consecutive unchanged observations=0
   - Reason: 研究ガードが WAIT_FOR_NEW_DATA のため、探索を再開しません。
   - Next: 新しい検証済み結果を待つ間、データ品質監査・文献照合・未承認実験計画の準備だけを続けてください。

No longer in current queue (not proof of action success): 

Historical research alone is not evidence of lottery prediction ability.
