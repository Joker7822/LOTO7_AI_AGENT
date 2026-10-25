# Disjoint Geometry v1 — Independent Future-OOS Research Registry

**Registered 2026-10-25 JST before draw #701 (scheduled 2026-10-30).**
The archived GitHub pull-request/commit timeline is the actual evidence of
preregistration. A date string alone is not proof that a forecast predates a
drawing.

This is a **separate, research-only, fixed 26-draw validation** of the
35-number, five-disjoint-ticket coverage geometry. It must **never replace or
feed into** the existing Production Champion, issued Prediction ledgers,
strict Future OOS, matched-permutation ensemble, or Joint Set v2 signal
shadow. It does not assert that lottery numbers are predictable.

## Frozen at registration

- Immutable model: `fair-uniform-disjoint-five-ticket-geometry-v1`.
- Source code: `balanced_uniform_portfolio.py` locked by SHA-1 Git blob ID.
- Evaluator: `disjoint_future_oos.py` separately locked by Git blob ID.
- First eligible target: draw **701** (2026-10-30); 700 is the already verified
  parent. Historical results 1–700 are excluded from any prospectively scored
  draw.
- Planned fixed sample: 26 trusted draws **701–726**, with no interim tuning.
- Candidate: 5 independent blocks of 7 **without overlap**, 35 distinct
  numbers in total, chosen from a deterministic uniform permutation.
- Control: five **distinct** independently sampled uniform 7-number tickets,
  generated at the same time with a fixed independent RNG seed. This is a
  separately frozen reference; it is not the geometry-matched ensemble used
  by the Production Champion.
- Candidate seed: `20261025 + target_round * 1009 + 1000000`;
  reference seed = candidate seed + `443322`.
- Primary endpoint **fixed 26-draw mean paired composite-score difference
  versus independently frozen random**. Composite-score weights are
  `max_hits + 0.35 * any_ge3 + 0.75 * any_ge4 + 0.10 * mean_ticket_hits`.
- Secondary: 3+/4+ event rates and average maximum matches.
- Only descriptive interim means, **no interim significance or automatic
  promotion**. Even a strong 26-draw advantage would be a demonstration of
  portfolio coverage, *not* ability to predict lottery balls.

The initial candidate and comparator tickets for #701 are committed into
`research/disjoint_future_oos/freeze_0701.json`, so they can be inspected
before the draw date. File metadata include registered data SHA-256, both
source-code lock identifiers, draw date and all exact ticket labels.

## Fail-closed sequential operation

1. The source-validation guard must confirm **two agreeing result sources**,
   correct CSV round/date/numbers/bonus and matching CSV SHA-256. If not,
   the recorder **does not grade**.
2. The target must have its own immutable `freeze_0NNN.json` committed
   *before* its drawing. A missing prior freeze cannot be reconstructed after
   a result appears: the process refuses retrospectively filling gaps.
3. The script appends at most one immutable `grade_0NNN.json` for an observed
   trusted result, including actual seven numbers, independent source digest,
   exact score components, and the committed freeze fingerprint.
4. Only **after** verification can it freeze the next draw, and only if the
   published `sources.official_schedule` round/date match and the wall
   clock is **before 18:00 JST on the intended draw date**. If late, do not
   create a false prospective result.
5. All earlier freeze/grade files are rechecked against deterministic
   seed generation, implementation locks, prior data hashes and scores.
   Any changed code, registry corruption, missing files or noncontiguous
   grade sequence causes failure.
6. A dedicated GitHub Actions workflow runs tests, reads the independent
   source snapshot, and appends **only new** freeze/grade JSON records in
   `research/disjoint_future_oos/`. It cannot change Champion/Production
   files. Source verification pushes and the daily scheduled run trigger it.

## Verify without writing

```bash
python -m pytest -q tests/test_disjoint_future_oos.py
python disjoint_future_oos.py --mode verify
```

Append only a genuinely verified next draw (normally handled by GitHub Actions):

```bash
python disjoint_future_oos.py --mode advance
```

At the time of registration (2026-10-25), the only resolved draw is #700,
so the valid progress is **0/26 graded, #701 prefrozen**. Do not fabricate
results for #701–#726 or retrospectively include previously known draws.

## Scientific limitations

The exact fair-world 5-ticket geometry advantage is a combinatorial fact
under a conditionally uniform draw. For five distinct tickets the first-prize
probability remains exactly `5/C(37,7)`, **regardless of geometry**. Coverage
can change the chance of at least one ticket having 3+ matching main numbers,
without increasing the ability to predict the next seven numbers. The fixed
26-draw OOS comparison is a prospective implementation/coverage diagnostic,
not an independent claim of a lottery forecast edge or expected profit.
