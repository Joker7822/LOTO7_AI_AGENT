# Autonomous open-access paper method laboratory

Updated **2026-11-04 JST**. This is a **safe, bounded, automated research-method
adaptation**, not universal autonomous reproduction of arbitrary source code.

## Current architecture

Daily GitHub Actions runs `paper_method_autonomy.py` on the trusted
Crossref/OpenAlex two-provider bibliography. For one previously unattempted DOI:

1. **Fetch the real open-access article body** via an OpenAlex OA PDF location
   on an explicit HTTPS allowlist. Reject missing/unsupported/unextractable
   text, untrusted redirect hosts, oversized PDF (5 MB), or more than 40 pages.
   An abstract or DOI landing page does not count as the paper.
2. **Read the paper's mathematical and experimental text** in bounded,
   overlapping 28,000-character windows (up to 8 windows). The article is
   untrusted model input, never executable code.
3. **Extract and instantiate a new algorithmic expression** through an
   explicitly configured OpenAI inference API. The model must return only
   `method`, `exact_quote`, `expression`, `limitation` JSON. The quoted
   20–150 characters must literally occur in the paper section. The expression
   must satisfy the repository's constrained arithmetic AST: 7 prior-only
   feature vectors, numeric constants, mathematical operators and 4 numeric
   functions. It can generate expressions not authored in repository code.
   Python statements, imports, attribute access, arbitrary library calls,
   external downloaded scripts, and executable paper text are forbidden.
4. **Reproduce the derived algorithm's outputs** on four independent
   synthetic 7-of-37 histories. Verify determinism, 37 finite
   probabilities, sum of 7, nonuniform behavior, and exact result-target
   exclusion. Also measure a **fixed last-48-draw prior-only historical
   Brier-screen** against the uniform 7/37 baseline; reject candidates
   whose average advantage is not positive. This historical screen is
   affected by candidate/DOI selection and does **not** prove real skill.
5. **Register the candidate** with DOI, paper-body SHA256, expression SHA256,
   literal paper excerpt, deterministic tests, and historical screen result.
   New valid papers accumulate in a bounded-math candidate queue. They are
   not inserted into Production.
6. **Start a precommitted 26-draw future-only study** using
   `paper_method_future_shadow.py`. Issue full 37-number probability
   vectors before each next official draw's JST calendar day, audit
   hashes and timestamps, grade only verified future results, and maintain
   an e-process against the mathematically fair baseline.
7. **Automatically adopt the research model**, and actually run it for
   the next research forecast via `research_paper_adopted_predict.py`,
   only after all 26 new draws have occurred and the research e-value
   reaches at least 40 (precommitted alpha = 0.025). The output is
   `research/autonomous_paper_methods/adopted_model_preview.json`.
   If the evidence fails or has not arrived, there is no adopted preview.

Existing Production, Champion, public purchasing outputs, real draw
history, and all previously registered prospective OOS books remain
**untouched**. This new model is only an automatically adopted **research
shadow** model, pending a separately authorized Production promotion gate.
The first prospective study is fixed to one candidate; queued candidates
do **not** automatically start second prospective trials in this version.
That requires a preregistered multiplicity-adjusted protocol.

## Provider setup (required to activate paper analysis)

**GitHub Models was retired on 2026-07-30.** Its old
`models.github.ai` API and `models: read` workflow permission are not
used; past advice to rely on GitHub Models is outdated.

Add `OPENAI_API_KEY` as a **GitHub Actions repository secret**, in the
repository settings, not in Git, and enable sufficient API quota. The workflow
uses the Chat Completions endpoint
`https://api.openai.com/v1/chat/completions`, configurable via the
`PAPER_LLM_MODEL` environment variable (default `gpt-4o-mini`).

With no key, the discovery step returns
`awaiting_openai_api_key` **without marking papers as attempted**.
It must not claim any article was interpreted. Existing future studies
can still grade their already registered predictions.

Other runtime requirements: online access to OpenAlex and an accessible
allowlisted OA full-text PDF, Python 3.12, NumPy, pandas and `pypdf`.
The public CI validates deterministic processing without a real API key.
It does not prove that a live OA paper and live AI service completed.

## Scientific limitations

A new expression based on a paper is a **domain adaptation**. Anchoring a
quote and executing the mathematics in a sandbox is not a faithful
independent replication of the paper's original empirical results or proof.
Some methodologies cannot be represented by the allowed grammar; these
are automatically rejected, not silently replaced by arbitrary code.

Even a positive historical score is selected with hindsight. The next
**26 future draws**, and the preregistered e-process, are what can
provide conditional fair-lottery evidence. If all published choices are
independent and uniformly distributed, no historical algorithm is known
to make their actual numbers inherently more predictable.

To run validation:

```bash
python -m pip install -r requirements.txt pytest pypdf
python -m pytest -q tests/test_paper_method_autonomy.py \
  tests/test_paper_method_adopted_predict.py
OPENAI_API_KEY=... python paper_method_autonomy.py --repo-root .
python paper_method_future_shadow.py --repo-root .
python research_paper_adopted_predict.py --repo-root .
```

## Primary sources

- GitHub: GitHub Models retirement, effective 2026-07-30:
  https://docs.github.com/en/github-models
- OpenAlex: Open access locations and `best_oa_location`:
  https://help.openalex.org/data/locations/
- OpenAI: Chat Completions and structured/JSON outputs:
  https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat
- Freund & Schapire (1997), *A Decision-Theoretic Generalization of
  On-Line Learning and an Application to Boosting*, DOI
  https://doi.org/10.1006/jcss.1997.1504 (example of a candidate
  method, not proof of reproduced lottery prediction accuracy).
