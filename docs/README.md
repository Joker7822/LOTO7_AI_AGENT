# LOTO7 AI AGENT — browser dashboard

A responsive, read-only Japanese dashboard showing the latest public research and operational state of the repository. No secrets, login, external database or production-changing controls are involved.

## Open in a browser (one-time GitHub Pages activation required)

**Intended official URL:** https://joker7822.github.io/LOTO7_AI_AGENT/

At implementation time, GitHub repository metadata reported **has_pages: false**, so this address is not guaranteed to work until the repository owner performs the one-time setup:

1. Open https://github.com/Joker7822/LOTO7_AI_AGENT/settings/pages
2. Under **Build and deployment**, select **Deploy from a branch**.
3. Choose branch **main**, folder **/docs**, and click **Save**.
4. After the first GitHub Pages deployment succeeds, open the intended URL above.

No additional hosting, login, API key or GitHub Actions secret is needed. GitHub Pages automatically publishes website-code changes to the /docs folder from main, once configured. Because the site loads public GitHub JSON directly, agent-state updates do not require repeated website deployments.

## Current-state sources (public and read-only)

The dashboard fetches JSON via raw.githubusercontent.com from main every **120 seconds** while visible (and on refresh button clicks). The currently displayed repository source status can lag due to GitHub CDN caching and scheduled workflow timings. It clearly shows **source verification time** and **browser refresh time** as separate times.

- source_validation.json: latest verified draw/date, main/bonus result and next official schedule;
- agent_role_council_summary.json: overall condition and five scoped agents, with named handoffs;
- v4_research_state.json: current research generation and total evaluations;
- future_holdout_state.json: pre-registered portfolio future holdout, including trusted draw count;
- joint_set_v2_signal_oos_summary.json: independently registered 26-draw v2 signal shadow;
- continuous_learning_agent_summary.json: indefinite prospective learning status, frozen target and future-only actual results;
- model_champion.json, weekly_production_prediction_state.json: model version and publication **status**. The separate public snapshot also now exposes only the five **already-issued** Production tickets from the canonical append-only prediction ledger;
- predictive_expert_agent_summary.json: exploratory historical comparison, never presented as independent future proof;
- research_cycle_guard.json: trial-count guard.

### Privacy and accuracy limits

The GitHub Pages dashboard **now displays only the five already-published Production forecast tickets** after checking the weekly publisher state against the canonical prediction ledger and the correction/invalidation log. Because GitHub Pages is public, these five issued ticket numbers are public information; no password, private Sakura connection, unissued candidate, or registered research Future-OOS vector is exposed. The separately password-protected Sakura prediction viewer remains protected by its own controls.

Failing JSON fetches and cross-system version/round discrepancies produce an **unknown / warning** rather than a fabricated successful score. A WATCH is a governance reminder, not evidence that the agent is broken. Historical Top7 scores are explicitly marked HISTORICAL ONLY; genuinely prospective data are shown separately. Accuracy gains, lottery winnings and Production promotion are never implied by past or partial exploratory data.

This is a read-only visualization; it cannot select a new Champion, alter training code, publish new tickets, retroactively score a draw or modify a preregistered freeze.

## Local preview and checks

Run a static server from the repository root:

    python -m http.server 8000 --directory docs

Open http://localhost:8000/ in a browser with an internet connection. Direct file:// access can restrict JavaScript module imports, so use HTTP.

Run view-model tests without network:

    node --test docs/tests/*.test.mjs
    node --check docs/app.js

GitHub Actions uses .github/workflows/browser_dashboard_ci.yml for validation.

If the official URL shows 404, enable GitHub Pages in Settings first and check the Pages deployment. An inaccessible webpage does not imply the AI agent has stopped. If status tiles say 未取得, check network access to raw.githubusercontent.com and retry 更新.

## 運用監視と精度推移（第2・第3段階）

監視は従来の10個のJSONをブラウザから別々の時刻に読み込む方式から、単一の `docs/data/dashboard_snapshot.json` に統一しました。GitHub Actions `Browser Ops Snapshot` がmainの同じコミットにある公開情報だけを厳選して構成し、GitHub Actionsの最新実行状況はAPIから別途取得して「API取得時点の参考値」として付記します。自動更新は15分ごとの予定（GitHubの遅延あり）と重要な状態ファイルが更新されたときです。ページの再取得は2分ごとです。

ダッシュボードに新たに表示する項目:

- **研究・継続学習・事前凍結・役割監査・Production発行など7つのActionsの最新状態**。正常、実行中、失敗、未取得を区別し、実行ログへのリンクを表示します。失敗を自動で「復旧済み」と偽装しません。
- **90分以上前の監視スナップショットは期限切れとして警告**。同一ソースコミットの短いSHAと作成時刻を表示します。
- **事前登録済みFuture-OOSの累積平均グラフ**。5口のRandom/Championとの差、v2及び継続学習のlog-score/Brier改善/Top7平均をタブで切り替えられます。
- **未観測の将来結果は空表示**。ゼロを実績にしません。既存の5口holdoutと第701回からのv2/適応研究は別の計測系統です。

生成処理は `dashboard_status_snapshot.py` です。事前凍結前の後出し予測や未信頼データ、データと台帳の回別不一致を発見した場合、スナップショットを生成せずActionsが失敗します。自動修復やモデル昇格は行わず、元のregistered state・Champions・Production・予測番号を決して書き換えません。

テストは `python -m pytest -q tests/test_dashboard_status_snapshot.py` と `node --test docs/tests/*.test.mjs` です。CI内の一時キャッシュはファイルが存在しても構いません。Gitの追跡対象でないことを確認します（`tests/test_ephemeral_research_caches.py`）。

**注意:** フローの失敗理由がGitHub APIから取れない場合は「未取得」と表示します。過去の探索済み成績は将来の精度改善を示す統計的証拠ではありません。


## Advanced Scientific Validation Laboratory

The dashboard has a new section showing (1) exploratory side-by-side four/five expert comparisons with a matched full-learner fair-lottery max-statistic experiment and four-draw paired block-bootstrap interval, and (2) an **independently preregistered future-only anytime e-process** from SHA-verified fifth-expert prospective freeze ledgers.

The e-value starts at 1 with **zero new actual future draws**, stays empty until the registered target 701 is graded from a two-source verified result, and does **not** imply lottery winning or Production adoption. Raw 37-number prediction vectors and ticket numbers are never displayed. If research data are missing, stale, or inconsistent with the fifth-expert registration, the site labels them as unavailable rather than successful.

- Lab entrypoint: advanced_validation_lab.py
- Independent workflow: .github/workflows/advanced_validation_lab.yml
- Protocol: ADVANCED_VALIDATION_LAB.md
- One public summary: loto7_agent_output/advanced_validation_lab_summary.json
- New snapshot field: scientific_validation


## 最新の本番予測番号と直近の照合結果

- `public_issued_prediction.py` は新規発行を行わず、`weekly_production_prediction_state.json` が明示的に `published=true` の場合だけ、既存の `predictions.csv` に記録された該当回の**有効な5口**を取り出します。
- `prediction_corrections.csv` の無効化イベント、対象回・基準回・発行時刻（抽せん前）・モデル版・CSV SHAを照合。不一致、重複、番号不正、抽せん後に作られた予測は表示を拒否します。
- まだ確定していない対象回は「公式結果の検証待ち」。`actual_results.csv` の独立2ソース照合済み実結果に限定して数字の一致数を集計します。最新の前回分の照合済み成績も表示します。
- 公開JSONは `docs/data/dashboard_snapshot.json` の `latest_prediction` に**発行済み本番5口と最小限の照合情報のみ**を同時刻のスナップショットとして含めます。研究用候補、Future-OOSの凍結ベクトル、秘密情報、認証情報は含めません。
- **ご注意:** GitHub Pagesは公開サイトのため、5口の予測番号は第三者にも閲覧可能です。購入を推奨するものではなく、当せんを保証しません。

テスト：`python -m pytest -q tests/test_public_issued_prediction.py tests/test_dashboard_status_snapshot.py`、`node --test docs/tests/issued-prediction.test.mjs`。
