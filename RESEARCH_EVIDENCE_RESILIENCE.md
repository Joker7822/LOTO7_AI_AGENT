# Research Verification & Bounded Self-Healing

**目的:** 公開論文を収集 → 出典を照合 → 方法論を公平な模擬抽せんで検証 → 研究計画に反映。予測精度向上の証拠が得られたという意味ではありません。

## 外部論文の検証

6時間周期で新しい論文を検索したサイクルに限り、最大3件のDOIをCrossrefとOpenAlexの公開APIから照合します。DOI・出版年・正規化タイトルを比較し、two_provider_bibliography_matched、single_provider_only、conflict_do_not_use、unavailable、previously_verified_not_refreshed、not_yet_checkedに分類します。

単なるDOI一致や抄録の有無だけで論文の本文を理解した、査読済み、またはロト7への適用効果が証明されたとは表示しません。出版社が保有する抄録全文を記録せず、外部文面を実行命令として扱いません。

- Crossref API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- OpenAlex API: https://help.openalex.org/api/

## 方法論の研究・活用（安全なサンドボックス）

固定シードによる一様7-of-37の512世界×24回を作成します。適切な一様周辺確率と、わざと偏らせた固定予測をBrier/対数スコアと逐次e値の帰無検査で比較します。これは校正・prequential評価・anytime有効性の安全性チェックです。実世界のLOTO7抽せん履歴、登録済みFuture-OOS、モデル学習・昇格には一切使用しません。論文に記載された実装を実際に再現した、とは主張しません。

## 自己修復可能な範囲

1. 公開書誌APIのHTTP 408/429/5xxや一時的タイムアウトは最大3回だけ再試行します。
2. 一時障害では以前確認した書誌情報を現在の検証成功と偽らず、previously_verified_not_refreshedとして表示します。
3. 壊れた派生研究レポートだけは、SHA連結と研究ガードを検査した元データから再生成します。
4. 固定された公平抽せんシミュレーションを再実行します。

自動修復しないもの: 実抽せんCSV、SHA連結監査元台帳、研究予算、登録済みFuture-OOS、Champion、Production、未承認コード。証拠の不整合、科学的推論の誤り、コード変更を伴う不具合はCI失敗・人の承認へエスカレーションします。コードの自動生成・無審査マージ・長時間研究の無条件再実行は行いません。

## 新しい専用出力（研究のみ）

- loto7_agent_output/research_verified_publications.json
- loto7_agent_output/research_method_sandbox.json
- loto7_agent_output/research_self_repair_report.json
- loto7_agent_output/research_verified_method_report.md

従来の毎時GitHub Actionsに組み込み、元の6研究ファイルと上記4ファイルだけをステージします。GitHub Actionsの毎時スケジュールはベストエフォートです。

検証コマンド: python -m pytest -q tests/test_research_evidence_resilience.py

**注意:** 自動オンライン検証が全論文について常時成功すること、あるいは公平な抽せんに対して予測の優位性が生まれることは保証できません。
