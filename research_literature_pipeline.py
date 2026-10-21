#!/usr/bin/env python3
"""Deterministic literature metadata triage and approval-gated experiment planning.

NOT full-text paper reading, peer review, autonomous experimentation or model
selection. Untrusted scholarly metadata never becomes executable instructions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import always_on_accuracy_agent as discovery

VERSION = "research-literature-review-and-design-v1"
REVIEW_FILE = "research_literature_reviews.json"
DESIGN_FILE = "research_experiment_proposals.json"
REPORT_FILE = "research_literature_review_report.md"
DOI = re.compile(r"10\.\d{4,9}/[a-z0-9._;():/-]{1,130}\Z", re.I)
TOPICS = (
    ("calibration", ("calibrat", "reliabilit", "probabilistic forecast")),
    ("online_evaluation", ("prequential", "online learning", "sequential forecast")),
    ("anytime_evidence", ("martingale", "e-value", "sequential test", "betting")),
    ("distribution_shift", ("conformal", "time series", "drift", "distribution shift")),
    ("selection_bias", ("multiple compar", "backtest overfit", "selection bias", "data snoop")),
    ("ensemble", ("ensemble", "forecast combination", "model averaging", "bayes")),
)
# Human-authored fixed templates; no free-form external text enters instructions.
PLANS = {
    "calibration": (
        "Frozen 37-number inclusion forecasts may need calibration auditing.",
        "Evaluate reliability bins and prequential proper scores using only existing frozen predictions.",
        "Brier/log-score and calibration-bin deviation",
        "Seven balls are drawn without replacement: the 37 indicators are not independent."
    ),
    "online_evaluation": (
        "A fixed online learner could differ from the uniform baseline in future data.",
        "Specify update timing, fixed rate, and test-then-train chronology before any future evaluation.",
        "prequential proper-score edge versus uniform 7/37",
        "Backtesting mined draws cannot validate predictive advantage."
    ),
    "anytime_evidence": (
        "A new preregistered forecast could show evidence against conditional uniformity.",
        "Predeclare a new non-overlapping future stream, frozen predictable e-factor and threshold.",
        "future-only nonnegative e-process with conditional mean at most 1",
        "Multiple selective e-tests require multiplicity governance."
    ),
    "distribution_shift": (
        "Chronological model performance may differ by era.",
        "Compare fixed non-overlapping eras, paired block uncertainty and fair-world histories.",
        "era-wise log/Brier edge and descriptive heterogeneity",
        "Drift tools cannot manufacture a lottery prediction signal."
    ),
    "selection_bias": (
        "A selected winner may be an artifact of many attempted optimizers.",
        "Re-run the whole candidate-search pipeline including rejected trials on independent fair histories.",
        "familywise max-statistic under full-pipeline null",
        "Previously mined history is not independent confirmatory evidence."
    ),
    "ensemble": (
        "Fixed probability averaging may reduce variance without improving true accuracy.",
        "Compare original frozen ensemble, fifth expert and uniform comparator on identical chronological targets.",
        "paired Brier/log-score edge and fair-world selection-adjusted comparison",
        "Mixture weights must not be fit on already graded future targets."
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def checked_papers(state: dict, chain: list[dict]) -> list[dict]:
    """Require every listed DOI/title/year to occur in valid SHA-chained discovery."""
    if (state.get("version") != discovery.VERSION or not chain
            or state.get("read_only_scientific_activity") is not True
            or state.get("promotion_authorized") is not False
            or state.get("sequence") != len(chain)
            or state.get("last_record_sha256") != chain[-1]["record_sha256"]):
        raise ValueError("research source lacks a trusted audit-chain anchor")
    origins = {}
    for event in chain:
        if event.get("version") != discovery.VERSION or event.get("read_only") is not True:
            raise ValueError("research journal event changed")
        for paper in event.get("new_papers", []):
            if isinstance(paper, dict):
                origins[paper.get("doi")] = (paper.get("title"), paper.get("year"))
    items = state.get("papers")
    if not isinstance(items, list) or len(items) > 36:
        raise ValueError("invalid bibliography size")
    output, used = [], set()
    for p in items:
        if not isinstance(p, dict):
            raise ValueError("invalid bibliography record")
        doi, title, year, url = (p.get(k) for k in ("doi", "title", "year", "url"))
        if (not isinstance(doi, str) or not DOI.fullmatch(doi) or doi in used
                or not isinstance(title, str) or not 1 <= len(title) <= 200
                or isinstance(year, bool) or not isinstance(year, int)
                or year < 2020 or year > datetime.now(timezone.utc).year
                or p.get("review_status") != "unreviewed"
                or url != "https://doi.org/" + doi
                or origins.get(doi) != (title, year)):
            raise ValueError("paper differs from SHA-anchored discovery metadata")
        used.add(doi)
        output.append({"doi":doi, "title":title, "year":year, "url":url})
    return output


def paper_topics(title: str) -> list[str]:
    title = title.lower()
    return [topic for topic, words in TOPICS if any(w in title for w in words)]


def review(paper: dict) -> dict:
    tags = paper_topics(paper["title"])
    score = min(5, 2 * ("calibration" in tags or "selection_bias" in tags)
                + ("anytime_evidence" in tags) + min(len(tags), 2))
    return {
        **paper, "topics":tags, "triage_score_not_accuracy":int(score),
        "priority": "review_next" if score >= 3 else "background",
        "review_status":"metadata_triage_only",
        "full_text_examined":False, "peer_review_verified":False,
        "reproducibility_verified":False, "lottery_applicability_verified":False,
        "limitations":[
            "DOI/title/year cannot demonstrate methodology or reproducibility",
            "Fair independent lotteries have no established exploitable predictive pattern",
            "Cross-domain relevance requires separate scientific review"
        ],
    }


def proposals(reviews: list[dict], evidence: dict) -> list[dict]:
    active = {topic for r in reviews for topic in r["topics"]}
    output = []
    for topic, _ in TOPICS:
        if topic not in active:
            continue
        hypothesis, design, metric, risk = PLANS[topic]
        output.append({
            "proposal_id":sha((VERSION+"|"+topic).encode())[:16],
            "topic":topic, "source_dois":[r["doi"] for r in reviews if topic in r["topics"]][:4],
            "hypothesis":hypothesis, "design":design, "primary_metric":metric,
            "baseline":"uniform 7-of-37 draw plus an existing frozen comparator",
            "required_controls":[
                "identical chronological targets and matched compute budgets",
                "full search-process reruns on synthetic fair 7-of-37 draws",
                "include all attempted candidates in multiple-comparison correction",
                "freeze every new genuinely prospective prediction before its outcome"
            ],
            "stop_conditions":[
                "unverified result source or missing prefrozen forecast",
                "model or draw-data SHA mismatch",
                "per-data optimizer budget exceeded",
                "new hypothesis not independently preregistered"
            ],
            "critical_risk":risk, "status":"draft_needs_human_method_review",
            "experiment_approved":False, "code_execution_authorized":False,
            "new_trial_budget_granted":False,
            "future_oos_registration_created":False,
            "production_promotion_authorized":False,
            "same_data_search_currently_permitted":evidence["search_enabled"] is True,
        })
    return output


def run(root: Path) -> dict:
    root=root.resolve()
    out=root/"loto7_agent_output"
    evidence=discovery.inspect_evidence(root)
    state_file=out/discovery.STATE
    state=discovery.read_json(state_file)
    chain=discovery.read_chain(out/discovery.LEDGER)
    papers=checked_papers(state,chain)
    reviews=[review(p) for p in papers]
    reviews.sort(key=lambda x:(-x["triage_score_not_accuracy"],x["doi"]))
    designs=proposals(reviews,evidence)
    anchor={
        "version":VERSION, "discovery_state_sha256":sha(state_file.read_bytes()),
        "discovery_chain_tip":chain[-1]["record_sha256"],
        "draw_history_sha256":evidence["draw_history_sha256"],
        "research_mode":evidence["research_mode"],
        "last_resolved_round":evidence["latest_round"],
        "scope":"metadata_only_no_paper_contents"
    }
    reviewed={
        **anchor, "count":len(reviews), "reviews":reviews,
        "full_text_reviewed_count":0, "automatic_model_selection":False,
        "production_promotion_authorized":False,
    }
    planned={
        **anchor, "count":len(designs), "proposals":designs,
        "executed_experiments":0, "new_trials_consumed":0,
        "prior_registration_modified":False,"production_modified":False,
        "requires_human_approval":True,
    }
    for path,obj in ((REVIEW_FILE,reviewed),(DESIGN_FILE,planned)):
        (out/path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    lines=[
        "# Literature metadata reviewer & experiment design queue","",
        "This is not full-text paper review or an automated forecasting experiment.",
        "Discovery chain: "+anchor["discovery_chain_tip"],
        "Research guard: "+evidence["research_mode"]+"; search permitted: "+str(evidence["search_enabled"]),
        "Triaged papers: "+str(len(reviews))+"; non-executable designs: "+str(len(designs)),"",
        "## Read-next list (metadata only)"
    ]
    for r in reviews[:12]:
        lines.append("- DOI "+r["doi"]+" ("+str(r["year"])+") "
                     +r["priority"]+" topics="+(",".join(r["topics"]) or "unknown"))
    lines.extend(["","## Draft-only experiment templates"])
    for p in designs:
        lines.extend(["### "+p["topic"],"- Hypothesis: "+p["hypothesis"],
                      "- Metric: "+p["primary_metric"],
                      "- Plan: "+p["design"],
                      "- Human approval, future preregistration, independent data required."])
    lines.append("No automatic code, Champion, Production, OOS modification or new optimizer trials.")
    (out/REPORT_FILE).write_text("\n".join(lines)+"\n",encoding="utf-8")
    return planned


def main() -> int:
    parser=argparse.ArgumentParser(description="Deterministic metadata review and experimental draft planning")
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    args=parser.parse_args()
    result=run(args.repo_root)
    print(json.dumps({"proposals":result["count"],"mode":result["research_mode"],
                      "experiments_executed":result["executed_experiments"]}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
