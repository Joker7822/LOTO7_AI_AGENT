# Full-text paper adaptation → synthetic reproduction → future-only automatic research adoption

Last implemented: **2026-11-03 JST**.

## What is actually automated

The new workflow `.github/workflows/autonomous_fulltext_paper_lab.yml` runs
daily, independently of the legacy DOI/abstract-only bibliographic researcher.
It uses the existing checked bibliography as its discovery feed.

1. Select one DOI whose title/year identity matched **both** OpenAlex and Crossref.
   Unverified, conflicting, or unknown DOIs are not selected.
2. Ask OpenAlex for the best open-access PDF, and allow only explicitly approved
   scholarly hosts via HTTPS with redirect validation. Refuse missing,
   unavailable, unauthorised, oversized or unextractable full text. **A DOI,
   title, abstract, or landing page is not passed off as the full paper.**
3. Download the actual PDF and extract its text using `pypdf` (max 5 MB,
   max 40 pages; a text body must have >=1500 characters).
4. GitHub Models (`models: read`, `GITHUB_TOKEN`) reads the paper content
   as untrusted data. It must propose a **closed JSON shape** with an excerpt
   literally anchored in the downloaded full text and a candidate mathematical
   expression. The source text is never treated as executable instructions.
5. Validate the expression with the repository's existing restricted AST
   (7 historical feature vectors; numeric constants and basic arithmetic plus
   `sqrt`, `abs`, `tanh`, `log1p`; no imports, file/network access,
   arbitrary Python statements, calls to other APIs, or external scripts).
6. Reproduce the same candidate probabilities twice for **four**
   independently generated synthetic 7-of-37 histories; check value ranges,
   exact determinism, normalization to seven expected selected numbers, and
   target-leakage invariance. Reject uniform-equivalent and invalid methods.
   **This is NOT a claim to reproduce the original publication's empirical
   experiments, proofs, or code.**
7. Automatically register the first acceptable candidate as an isolated
   **experimental paper-derived model**. Maintain a SHA-256 paper hash,
   mathematical expression hash, method quote, DOI and limitations.
8. Independently, **freeze the next unobserved draw** in
   `research/autonomous_paper_methods/future_state.json`: 37 full
   probabilities, model expression hash, verified history prefix,
   official scheduled draw date, freeze timestamp, SHA-chained event hash.
   Only forecasts issued before the draw's **JST calendar day** are eligible.
9. After the trusted result is confirmed, recompute frozen Brier loss
   against the fair model `7/37` and append a SHA-chained grading event.
   Data revision, event gaps, changed predictions or untrusted draw results
   make the process stop rather than retroactively rebuild evidence.
10. After a fixed **26** future trusted draws, use an anytime-valid,
    precommitted evidence process to decide whether to auto-adopt the
    **research-only shadow candidate**:
    `e_t = 1 + (Brier_uniform - Brier_candidate)` (per-ball averages);
    `E = product(e_t)`. Under the conditional fair 7-of-37 null,
    the expected Brier advantage is nonpositive, each factor is
    nonnegative, and the conditional expected factor is <=1.
    The pre-registered first candidate uses `alpha=0.025`,
    requiring `E >= 40` and all 26 grades. A failed candidate is
    automatically marked `insufficient_future_evidence_do_not_adopt`.
    This version permits **only one** prospective paper candidate, preventing
    uncorrected repeated future selection; other candidates remain queued
    for future explicit multiplicity-governed expansions.

## Boundaries — essential to honest interpretation

A general scientific publication cannot automatically be converted into an
arbitrary faithful experimental replication by a finite allowlisted formula
interpreter. Novel techniques outside the permitted mathematical grammar are
**rejected** and need a separately reviewed extension. GitHub Models can
misinterpret articles; a literal excerpt anchor verifies grounding, not the
semantic fidelity of the derived model. Conversion produces a
**research-domain adaptation**, not publication-level replication.

Nor does a paper's success in another domain establish lotteries are
forecastable. On a conditionally fair 7-of-37 draw, an arbitrary ticket
is still one of `C(37,7) = 10,295,472` possibilities.

**Automatic adoption means research shadow only.** This system never edits
the existing Champion, `loto7.csv`, issued Production tickets, previously
registered prospective evidence, or registered OOS ledgers.
No production changes are made. To allow later Production promotion, a
separate explicitly governed policy with independent validation is required.

## Sources

- **Freund & Schapire (1997)**, *A Decision-Theoretic Generalization of
  On-Line Learning and an Application to Boosting*, JCSS 55(1), 119–139.
  DOI: https://doi.org/10.1006/jcss.1997.1504
  (related methodology for multiplicative weights and sequential evidence).
  Open full-text copy:
  https://www.eecs.harvard.edu/cs286r/courses/fall10/papers/hedge.pdf
- **OpenAlex documentation (as of 2026-11-03)** on
  `best_oa_location.pdf_url`:
  https://help.openalex.org/data/locations/
- **GitHub Models and Actions (2025-05 onward)**:
  https://github.blog/ai-and-ml/llms/solving-the-inference-problem-for-open-source-ai-projects-with-github-models/

## Running

```bash
python -m pip install -r requirements.txt pytest pypdf
python -m pytest -q tests/test_paper_method_autonomy.py
# Requires online scholarly PDF access and GitHub Models token;
# the local CSV and the existing trusted bibliography are used.
GITHUB_TOKEN=... python paper_method_autonomy.py --repo-root .
python paper_method_future_shadow.py --repo-root .
```

The first command does **not** guarantee an eligible method: a paper may lack
OpenAlex OA full text, be inaccessible, or not be expressible in the safety
grammar. In that case the output contains a blocker, not fabricated success.
The second command does not backdate forecasts; until the 26 new verified
draws occur, it reports pending evidence rather than "adopted".

The independent `research_cycle_round2_replay.py` created in the parent PR
continues to re-run the latest recursive model from round 2 as an explicitly
retrospective exploratory comparison. Historical replay cannot replace this
new future-only scientific confirmation.
