# オンライン研究文献の自動照合・巡回検証

LOTO7 AIはCrossref/OpenAlexの**公開書誌情報**から収集した文献候補を、
新しい専用エージェント `online_literature_auto_verify.py` で自動検証します。

## 何を検証するか

各DOIについて、CrossrefとOpenAlexの独立したAPIで次を突き合わせます。

- DOIが収集時のIDと一致するか
- 論文タイトルのトークン一致が十分か
- 発表年が一致するか
- 2社とも一致／過去に一致／単一社のみ／不一致／未確認／取得失敗
- 前回の照合日時、今回の照合日時、今回の照合失敗要因
- 研究元のSHA256付き収集台帳と論文リストが改変されていないか

**論文の全文・査読状況・コードの再現性・LOTO7に対する予測力を検証した
と主張するものではありません。** 査読や再現試験は別の作業です。

## 改善したポイント

従来の文献検証は定期的な探索フェーズで先頭3件に偏り、
収集分析が第699回の古い抽せん履歴を使っている場合、
オンライン論文の再照合更新が止まることがありました。

今回の専用検証は**全16件に巡回カーソルを持ちます**。
1回につき最大3件のDOIを照合するので、文献数16件なら
正常に実行された6サイクルで全候補に一度ずつ照会できます
（16件すべてに再検証を成功保証する意味ではありません）。
新規候補を収集するとSHA付き原典から再構築します。

抽せん歴の評価・モデル学習は従来の独立したソースガードを維持。
論文の公開書誌情報の検証だけは、研究予算や科学レポートが
`WAIT_FOR_NEW_DATA` のときも動作できます。

## スケジュールと監査

`.github/workflows/online_literature_auto_verify.yml`

- GitHub Actions **6時間ごと**（日本時間04:07/10:07/16:07/22:07、実行時刻はベストエフォート）
- 手動実行可能
- SHA付きの研究元文書が更新された際にも実行
- 変更可能なファイルは **2件のみ**:
  `loto7_agent_output/research_verified_publications.json`
  `loto7_agent_output/research_verified_publications_auto_report.md`
- 他のモデル、Champion、第701回事前凍結、Production発行データ、
  将来OOS台帳は一切変更しない
- Actionsの「実行概要」に検証件数・状態と、90日保存のJSON/Markdownを掲載

見方:
- `two_provider_bibliography_matched`: **このサイクル**で両社照合済み
- `previously_verified_not_refreshed`: 過去に両社一致したが今回未照合、または取得失敗。新鮮な証明として扱わない
- `single_provider_only`: 1社だけに整合性が確認できた
- `conflict_do_not_use`: 出典情報に矛盾。研究採用から除外する
- `not_yet_checked`: 未検証
- `unavailable`: API取得できず確認不能

## 検証コマンド

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q tests/test_online_literature_auto_verify.py
python online_literature_auto_verify.py --repo-root .
```

後者はCrossref/OpenAlexへアクセスします。公開APIのエラーには
既存の最大3回・短い再試行のみを使い、成功結果を捏造しません。

このデータの用途は、研究文献の信頼性向上、
矛盾の早期発見、全文レビューの優先順位付けまでです。
**論文書誌が一致したことを予測精度の実証や本番昇格の根拠にしません。**
