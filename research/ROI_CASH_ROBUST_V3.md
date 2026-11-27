# Robust combination refinement v3 (research only)

2026-11-28. Existing v2 remains unchanged. Refine only its five seven-number disjoint groups with up to four cross-ticket swaps. Use the preceding 104 draws split into two 52-draw blocks. Cap total training reward at 3,000 yen per draw and add 300 yen equivalent for three or more main hits in any ticket; require that neither capped cash nor frequency of three-plus main hits deteriorates in either block. This is training regularization, NOT independent validation or a forecast of actual profits.

Reuse existing chronological v2 ranking replay; score uncapped public payout, maximum hits, 3+/4+ rates, cash differences after removing four biggest positive paired differences, against v2, rank-order, and 32 deterministic same-35 random layouts. No future vectors, purchase, promotion, or ledger changes. Missing payout suppresses cash metrics. All past outcomes were available at development time, including round 705; historical evaluation is exploratory. Independent future data and a separate locked protocol are needed before deployment.

Bounded exception to research expansion policy: reuse one existing manual/PR read-only workflow, no new agent or schedule, finish at report artifact and do not automatically extend or promote. Fixed parameters selected as engineering defaults, not proven optimal.
