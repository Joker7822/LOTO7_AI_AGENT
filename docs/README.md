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
- model_champion.json, weekly_production_prediction_state.json: only model version and publication **status** — no ticket numbers;
- predictive_expert_agent_summary.json: exploratory historical comparison, never presented as independent future proof;
- research_cycle_guard.json: trial-count guard.

### Privacy and accuracy limits

The page **never displays stored production prediction tickets or any secret**. The separately password-protected Sakura prediction viewer remains protected by its existing controls.

Failing JSON fetches and cross-system version/round discrepancies produce an **unknown / warning** rather than a fabricated successful score. A WATCH is a governance reminder, not evidence that the agent is broken. Historical Top7 scores are explicitly marked HISTORICAL ONLY; genuinely prospective data are shown separately. Accuracy gains, lottery winnings and Production promotion are never implied by past or partial exploratory data.

This is a visualization; it cannot select a new Champion, alter training code, publish tickets, retroactively score a draw or modify a preregistered freeze.

## Local preview and checks

Run a static server from the repository root:

    python -m http.server 8000 --directory docs

Open http://localhost:8000/ in a browser with an internet connection. Direct file:// access can restrict JavaScript module imports, so use HTTP.

Run view-model tests without network:

    node --test docs/tests/*.test.mjs
    node --check docs/app.js

GitHub Actions uses .github/workflows/browser_dashboard_ci.yml for validation.

If the official URL shows 404, enable GitHub Pages in Settings first and check the Pages deployment. An inaccessible webpage does not imply the AI agent has stopped. If status tiles say 未取得, check network access to raw.githubusercontent.com and retry 更新.
