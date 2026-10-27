# 自律AIの自己書換え・学習・自動昇格 — 実装と安全境界

## どこまで自律化したか

- **自己学習**：既存の `autonomous_evolution_lab.py` は検証済み
  抽せん履歴に基づき候補を選び、毎データSHA最大4候補の履歴
  診断を行い、SHA256連結ログに記録します。新結果・正式な
  予算ガードがなければ停止し、同一履歴で無制限探索しません。
- **自己改変**：追加した `autonomous_self_rewrite.py` が、その
  履歴から選んだ研究候補を**再現可能なPython研究プログラム**に
  自動変換します。元データ・既存の評価結果・台帳・研究予算を
  検査し、保存したスコアを独立再計算してから出力します。
- **ソースの自動更新**：GitHub Actionsが6時間ごと（GitHubの
  ベストエフォート）に実行。問題がない場合のみ
  `research/autonomous_generated/research_model.py` と
  `research_model_manifest.json` をmainに自動コミットします。
  権限はこの隔離された2つの研究用ファイルに限定し、
  実際の予測発行・モデル本体には影響しません。
- **本番Champion自動昇格**：既存の `research_v4_no_production.py`
  と`strict_oos_governance.py` / `matched_permutation_ensemble.py`
  が、信頼済みの**実際に未来だった抽せん**を採点した際、
  事前凍結Champion、独立Uniform Random、32組の形状一致
  Permutation Ensembleと比較して既存基準を満たした場合に
  自動昇格を行います。本PRではその門番を緩めません。
  凍結済み本番の5口は遡及変更しません。

## 重要な違い

研究用の自動生成Pythonコードは**現在の正式Championのモデル形式とは別**
です。生成したからといって即時に本番昇格することはありません。
この隔離コードをProductionの予測関数として直接importする
経路も設けません。正式にそのモデル形式を利用するには、
独立の候補凍結・将来評価への登録と検証が必要です。

**無制限の任意コード実行、AIによるガード解除、研究予算の
勝手なリセット、未来抽せん後の遡及的凍結、未検証論文の
自動取り込み・即時本番昇格は許可していません。**

これにより、自由なコード更新によって本番の安全性・監査能力を
失うことなく、研究領域で自律的なモデル進化の結果を保存できます。

## 出力

```text
research/autonomous_generated/research_model.py
research/autonomous_generated/research_model_manifest.json
```

生成ソースに固定の研究メソッド
`probability_vector(prior_history)` が作成されます。
manifestには対象回、データSHA、採用候補ID、研究状態SHA、
出力コードのSHA、正式Future-OOSによる自動昇格判定の監査、
研究専用/本番不可の明示が入ります。

## 検証

```bash
python -m pytest -q tests/test_autonomous_self_rewrite.py
python autonomous_self_rewrite.py --repo-root .
```

専用GitHub ActionsはPR時と定期時にテストを実施し、
危険なコード挿入、既存学習結果の改ざん、古いスナップショット、
本番権限混入、同一入力での非再現性を検証します。
既存の第699回固定データ回帰環境では新しい第700回の
学習状態を無理に更新せず、鮮度不一致として保留します。

## 性能・期待値について

宝くじの公平・独立な抽せんに対して、過去に良かった研究候補が
本当に未来を予測できるとは限りません。新しい研究ソースの生成は
**予測性能の実証ではありません**。また5口の券配置を改良しても、
5種類の異なる7数字組の1等当せん確率そのものは変わりません。
