# Four independently scheduled, bounded research specialists

**Four new agents** complement the existing hourly research orchestrator,
without granting new prediction-model authority. Each of the four is a
separate GitHub Actions matrix job with a distinct, deterministic Python
entrypoint, advisory decision, checks, JSON report, Markdown report and
30-day archived artifact.

## Responsibilities

| Specialist | Responsibilities | Fail-closed outcome |
| --- | --- | --- |
| `source_sentinel` | Independent 2-source draw verification, source CSV SHA, trial-budget guard freshness | No result-based grading if current source is untrusted |
| `calibration_analyst` | Chronological baseline replay, Top7 theoretical 49/37, proper statistical caution, stale advanced-science SHA | Past p-values and portfolio scores are descriptive, never promotion evidence |
| `prospective_custodian` | Existing locked 26-draw formal holdout, Joint Set v2 and disjoint35 future freeze chains, immutable implementation hashes | Missing freeze, SHA drift, unauthorized tuning or changed registered horizon raises an exception |
| `literature_examiner` | Online DOI-check provenance, approval-gated experimental drafts, conflicts and unreviewed methods | Unverified paper content cannot execute models or authorize Production |

## Execution

The four specialist jobs run **every six hours** (GitHub's best-effort
schedule), independently with `contents: read` and no persisted checkout
credentials. You can also dispatch them manually from GitHub Actions.
Independent jobs mean a blocked source check does not erase the other
agents' ability to report their observations. Each job runs regression tests
against the same repository snapshot.

```bash
python -m pytest -q tests/test_research_specialist_agents.py
python research_specialist_agents.py --agent source_sentinel
python research_specialist_agents.py --agent calibration_analyst
python research_specialist_agents.py --agent prospective_custodian
python research_specialist_agents.py --agent literature_examiner
```

Outputs are *untracked/disposable* files:

```text
research_output/autonomous_specialists/source_sentinel.json
research_output/autonomous_specialists/calibration_analyst.json
research_output/autonomous_specialists/prospective_custodian.json
research_output/autonomous_specialists/literature_examiner.json
```

and matching Markdown summaries. The GitHub workflow uploads one artifact
per specialist. The report includes a current `pass/watch/block` advisory
state, specific verified findings, input evidence and explicit false values
for all mutation, budget, experimental execution and publication privileges.

## Special pinned-history CI rules

Full repository regressions intentionally replace the checked-in draw
result data with the 699-draw fixture from a pinned commit; its latest
source is **not** two-source verified. The source sentinel reports
`block`, without inventing source trust or overwriting the data. It is
correct for the same job to report `pass` for the verified 700-draw live
repository. Other specialists evaluate the fixture's own historical
snapshots without treating historical performance as future evidence.

## Important limits

These specialists **do not** self-write code, launch new optimizer trials,
fetch undisclosed external algorithms, buy tickets, change source data,
rewrite ledger predictions, change the existing #701 pre-freeze, extend
the research trial budget, promote Champion, or alter preregistered Future
OOS experiments. They produce bounded actionable diagnostics, not
autonomous deployment decisions.

Even four agreeing research agents would not establish an ability to
predict a conditionally fair and independent lottery. Improvement in
prediction accuracy, first-prize odds or financial returns is not claimed.
