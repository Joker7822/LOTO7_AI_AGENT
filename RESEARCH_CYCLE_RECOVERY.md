# 研究サイクル更新遅延の安全な自動復旧

## 原因（2026年10月29日時点）

- 第700回の抽せんデータ・2ソース検証と研究予算ガードは、同じ
  `fa6ee78c...` SHAに更新済みです。
- しかし登録済みの高度統計検証レポート
  `advanced_validation_lab_summary.json` は
  **第699回の `5e4fa6...` SHA**のままです。
- 1時間ごとの`always_on_accuracy_research.yml`は、古い科学
  レポートを新しいデータへ流用することを拒否し、
  研究活動レポートの更新も停止していました。
- 独立した2時間ごとのオンライン論文検索は別経路なので、
  この問題が直接停止させるものではありません。
- また従来は登録済み高度統計検証が**土曜日の週1回**中心で、
  新しい検証済みデータが来ても復旧が遅れることがありました。
- GitHub Actionsの`GITHUB_TOKEN`でプッシュされたコミットは、
  通常の`push`トリガーで他のActionsを連鎖起動しません。

## 修正

1. **登録済み高度統計検証**：`advanced_validation_lab.yml`を
   3時間ごとのチェックへ増強。新しい信頼済みデータでは既存
   `advanced_validation_lab.py`が、元の統計手続き・コードSHA
   をチェックし、最新CSV SHAのレポートを生成します。
   同じデータSHAの歴史的32-world計算は既存のキャッシュを再利用。
2. **研究サイクル**：登録済み高度統計検証workflowが
   `success`で完了すると、`workflow_run`から
   1時間ごとの研究サイクルを追加起動します。通常の
   1時間ごとのcronも継続します。
3. **自動判断**：`research_cycle_provenance_recovery.py`が
   最新抽せん結果・2ソース照合・研究予算のデータSHA・
   高度科学レビューのデータSHAを横断比較。
   `REFRESH_REGISTERED_SCIENCE`と
   `WAIT_FOR_INDEPENDENT_SOURCE`、
   `WAIT_FOR_RESEARCH_GUARD`、
   `READY_FOR_BOUNDED_RESEARCH`を別々に記録します。
4. **活動証跡**：高度科学レビューが現在のSHAに追いついてから、
   既存のSHA連結研究journalへ新しい監査サイクルを記録します。
   完了前は更新したように見せず、GitHub Actionsのsummaryへ
   明確な停止理由を表示します。

## 安全な待機と故障の違い

`WAIT_FOR_NEW_DATA`は**故障ではありません**。同じ抽せん
履歴に対する800/800回の探索予算を消費済みなので、新しい
独立確認済み抽せんがなければ最適化を増やしてはいけません。
一方、`always_on_accuracy_research_state.json`の監査・研究
計画・文献管理は新しいデータSHAの科学根拠が追いついた後、
学習予算とは独立して更新可能です。

この復旧は、研究予算のリセット、過去のモデル選択、
Champion自動昇格、発行済みProduction券、
第701回の凍結ベクトル・将来26回OOSの採点を**実行しません**。

## 検証

```bash
python -m pytest -q tests/test_research_cycle_provenance_recovery.py
python research_cycle_provenance_recovery.py --repo-root .
```

GitHub Actions:
- [登録済み高度統計検証](https://github.com/Joker7822/LOTO7_AI_AGENT/actions/workflows/advanced_validation_lab.yml)
- [1時間ごとの研究サイクル](https://github.com/Joker7822/LOTO7_AI_AGENT/actions/workflows/always_on_accuracy_research.yml)

GitHubスケジュールはベストエフォートで、指定時刻の実行は
保証しません。科学レポートの再計算が失敗した場合は
高信頼の古い科学結果を捏造せず、停止理由を残します。
