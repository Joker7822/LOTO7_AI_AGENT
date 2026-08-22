# LOTO7 Validation and Nested Replay

## Result-source validation

`fetch_validate.py` uses:

1. **Primary result**: Rakuten×宝くじ backnumber (`scrapingloto7.py`)
2. **Preferred secondary result**: Mizuho Bank winning-number page
3. **Fallback secondary result**: Rakuten Bank public winning-number/backnumber page
4. **Schedule context**: 宝くじ公式サイト

A secondary result is accepted only when target round, main numbers, bonus numbers, and (when present) draw date match the primary result. If any parseable secondary source disagrees, validation fails closed. If Mizuho is unavailable but Rakuten Bank matches, the result can still reach `verified_two_result_sources`. If neither secondary endpoint is parseable, the system stays `degraded_single_result_source`, continues research, and does not use that result as trusted Production-promotion evidence.

The official site is schedule context rather than a second winning-number source because its LOTO7 product page directs users to the Mizuho winning-number service for result confirmation.

## Nested walk-forward comparison

`nested_replay.py` compares three tracks over the most recent 120 completed draws by default:

- **Champion reference**: the predeclared baseline configuration
- **Nested Research selector**: chooses among the original v2 predeclared `baseline`, `stable`, `balanced`, and `adaptive` configurations
- **Random reference**: 32 deterministic random 5-ticket portfolios per draw

For target row `t`, the Research selector may use only the scored predictions from rows strictly before `t`. The target result is not included in model selection. The currently discovered v4 Research Winner is deliberately **not** inserted retrospectively because it was discovered using later historical data and would introduce selection leakage.

Outputs:

- `loto7_agent_output/nested_replay_rounds.csv`
- `loto7_agent_output/nested_replay_summary.json`
- `loto7_agent_output/nested_replay_report.md`

The summary includes mean max hits, mean ticket hits, 3+/4+ round rates, composite score, Research deltas versus Champion and Random, deterministic bootstrap 95% confidence intervals, and round win rates.

## Governance boundary

Historical replay, reconciliation, and nested replay are diagnostics only. They never directly promote the Production Champion. Production promotion continues to require pre-frozen future OOS evidence under the v4 e-process gate.
