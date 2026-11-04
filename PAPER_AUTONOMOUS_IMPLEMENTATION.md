# Proprietary, in-repository full-text research engine

**2026-11-05 (JST).** The method-generation layer uses a **self-developed,
deterministic Python engine** (`independent_paper_engine.py`) and
**does not call OpenAI API, GitHub Models, Ollama, or any commercial inference
provider**. It needs **no LLM key, account, hosted model, or GPU**.

This is an evidence-grounded **rule engine and restricted mathematical
compiler**, not an LLM trained from scratch. It cannot understand or faithfully
implement all unknown mathematical algorithms from arbitrary papers. Unsupported
methods are rejected rather than silently invented.

## The self-developed research pipeline

1. Daily GitHub Actions selects one paper whose Crossref and OpenAlex
   bibliographic identities have already been independently checked. To obtain
   a publication it can query public OpenAlex metadata and download its
   original open-access full-text PDF over HTTPS from allowlisted sites.
   **Those services supply documents only, not AI analysis.**
2. The local parser extracts actual PDF text using `pypdf`; metadata-only
   abstracts and papers without extractable body text do not qualify.
3. The local rule engine searches bounded overlapping full-text passages
   for a method claim, a combination/operator claim, and at least **two**
   explicitly mentioned supported algorithmic signal classes:
   short- or long-term frequency, exponential recency/decay, occurrence gaps,
   co-occurrence/interaction, and inverse-frequency variants. It records a
   **literal 20–150-character excerpt** from that text.
4. The original mathematical compiler maps only validated signal terms
   to known prior-only features. It constructs a bounded numeric AST
   expression such as `(hot20 + 0.5 * pair)` when the paper's method
   statement explicitly combines the matching concepts.
   The coefficient **0.5 is chosen by this project**, not automatically
   reconstructed from the article. This is a new *domain adaptation*,
   **not reproduction of the publication's implementation**.
   Paper text cannot provide Python statements, imports, functions or paths.
5. The existing scientific gates remain: deterministic reruns on four
   synthetic historical prefixes; probability shape/range/sum invariants;
   target-result leakage checks; chronological 48-target historical score
   screen against the fair 7-of-37 benchmark.
6. Only candidates surviving those gates join the separate research queue.
   A first model is registered and its next real draw predictions frozen
   before the draw date, using signed hashes and the independent source audit.
   A preregistered **26-future-draw** evidence test at `alpha=0.025`
   requires `E >= 40` to automatically adopt that model for **research
   shadow predictions**.
7. After scientific adoption the project automatically runs
   `research_paper_adopted_predict.py`, which validates the prospective
   evidence and candidate provenance before emitting research-only next-draw
   probabilities. Production, Champion, published tickets and other
   prospective ledgers are not modified.

## Operation

The workflow `.github/workflows/autonomous_fulltext_paper_lab.yml`
installs requirements plus `pypdf`, executes the research pipeline daily
and on the relevant merge, and commits only allowlisted research files.

No `OPENAI_API_KEY`, `PAPER_LLM_MODEL`, cloud-model credentials, third-party
LLM service, or GitHub Models permission is required.

```bash
python -m pip install -r requirements.txt pytest pypdf
python -m pytest -q tests/test_independent_paper_engine.py \
  tests/test_paper_method_autonomy.py \
  tests/test_paper_fulltext_end_to_end.py \
  tests/test_paper_method_adopted_predict.py
python paper_method_autonomy.py --repo-root .
python paper_method_future_shadow.py --repo-root .
python research_paper_adopted_predict.py --repo-root .
```

The last two commands do **not** promise an accepted model when no verified
candidate or future results exist. A published article's forecast method
need not transfer to a lottery with independently drawn numbers.

## What has and has not been completed

**Implemented:** local extraction/feature mapping/AST construction, quote and
source provenance, synthetic reproducibility, chronological historical triage,
future-only study, automatic **research-model** selection, and research
prediction after evidence-based adoption. All use code owned by this
repository rather than an AI inference API.

**Not claimed:** a general-purpose independently trained language model,
universal implementation of previously unseen arbitrary algorithms,
replication of papers' original published trials, a demonstrated advantage
over fair lotteries, or automatic Production/Champion replacement. A second
or subsequent paper candidate's separate future trial also requires a
multiplicity-adjusted registration before activation.

## Source references

- OpenAlex open-access locations: https://help.openalex.org/data/locations/
- Python standard-library regular expressions:
  https://docs.python.org/3/library/re.html
- Python AST validation:
  https://docs.python.org/3/library/ast.html
- Independently reviewed reference: Freund and Schapire (1997),
  DOI https://doi.org/10.1006/jcss.1997.1504
