# 頻繁なオンライン研究情報の収集・独立検証・実用化連携

新規 `frequent_online_research_feed.py` と
GitHub Actions `frequent_online_research_feed.yml` を追加しました。

## 情報収集

- **2時間ごと**（GitHub Actionsのベストエフォート実行）
- 最新**180日**の研究から、6つの事前登録されたテーマを順番に検索
- CrossrefとOpenAlexの公開論文書誌APIの両方で検索
- 新規DOIを照合し、**1実行で最大3件**の論文を独立確認
- 最大48件の候補を保存して、一定サイズで運用
- DOI/タイトル/発行年の一致状態、収集日時、元の研究収集台帳のSHAを記録
- 研究の既存データが第699回の古い参照を使っていても、
  **文献の新着検索は実行**できます。抽せん予測には影響しません。

## 検証

新しい文献は収集結果に掲載されたというだけでは採用しません。
Crossref/OpenAlex両方の詳細取得でDOI・タイトル・発行年を照合します。
不一致・単独ソース・API障害では未検証として隔離。
過去の一致を次回の「新たに照合済み」として流用しません。
既存のSHA256付き研究収集台帳は読み取り専用で、書き換えません。

公開論文の**書誌情報が実在・整合している**ことだけを確認します。
論文全文、査読状況、方法論の再現性、実際のLOTO7への予測力、
改善された当せん確率や期待収支までは自動認定しません。

## 安全な実用化

情報を得ただけで本番モデルへ反映せず、既存の6研究テーマへ分類し、
地元の固定テンプレートから*方法論レビューの次のタスク*を生成。
この新しいレポートは既存の `research_intelligence_core.py` が
`frequent_verified_online_research` として取り込み、研究課題の
優先度判断に役立てられます。

**オンライン論文本文やタイトルの文字列を、コード実行や
Championの昇格命令として使いません。**

## 出力先

- `loto7_agent_output/online_fresh_research_feed.json`：
  過去に収集済みの論文と、新着候補の独立したサイドカーレポート。
  6テーマの循環位置、確認日時、独立照合状態、検証済みの研究分野、
  ローカルで定めたレビュータスクを含みます。
- `loto7_agent_output/online_fresh_research_report.md`：
  人が読める概要。
- 90日保存のGitHub Actions成果物と実行サマリー。

自動コミットを許可するファイルはこの2件だけです。
本番Champion、LOTO7の抽せん結果、Production発行済み予測、
事前凍結の将来OOS、研究予算、収集元SHA連結台帳は保護します。

## 手動実行・テスト

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q tests/test_frequent_online_research_feed.py
python frequent_online_research_feed.py --repo-root .
python research_intelligence_core.py --repo-root .
```

公開APIの障害は成功扱いにせず、失敗・未検証として記録。
APIの利用回数と候補数、外部データのサイズを制限しています。

[自動収集と検証の実行履歴](https://github.com/Joker7822/LOTO7_AI_AGENT/actions/workflows/frequent_online_research_feed.yml)
