#!/usr/bin/env python3
"""Frequent online discovery -> independent identity check -> bounded research use.

This module works even while the lottery's SCIENCE snapshot is stale. It
doesn't create or revise the SHA-anchored literature intake or model budget;
new web findings are an independent, explicitly provisional sidecar. Only
locally-authored research review actions are derived from external metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import always_on_accuracy_agent as discovery
import online_research_intelligence as intelligence
import research_evidence_resilience as verifier
import research_literature_pipeline as review

VERSION = "frequent-verified-research-feed-v1"
FILE = "online_fresh_research_feed.json"
REPORT = "online_fresh_research_report.md"
MAX_CHECKS = 3
MAX_STORED = 48
LOOKBACK_DAYS = 180
TWO_SOURCE = "two_provider_bibliography_matched"
PREVIOUSLY = "previously_verified_not_refreshed"
KNOWN = {TWO_SOURCE, PREVIOUSLY, "single_provider_only",
         "conflict_do_not_use", "unavailable", "not_yet_checked"}
FIELDS_FALSE = ("full_text_reviewed", "peer_review_confirmed",
                "methods_reproduced_from_paper", "lottery_prediction_improved")


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(record: dict) -> str:
    return json.dumps(record, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def _check_prior(raw: dict, state_sha: str, tip: str) -> tuple[dict, int, dict]:
    if not raw:
        return {}, 0, {}
    if raw.get("version") != VERSION:
        raise ValueError("unexpected new-online-feed schema")
    items = raw.get("candidates")
    if (not isinstance(items, list) or len(items) > MAX_STORED
            or type(raw.get("next_topic_index")) is not int
            or not 0 <= raw["next_topic_index"] < len(discovery.TOPICS)):
        raise ValueError("invalid bounded online feed state")
    if (raw.get("discovery_state_sha256") != state_sha or
            raw.get("discovery_chain_tip") != tip):
        # Do not transfer old validation claims to a changed discovery set.
        return {}, 0, {}
    seen = {}
    for p in items:
        if (not isinstance(p, dict) or
                not review.DOI.fullmatch(str(p.get("doi", ""))) or
                p["doi"] in seen or p.get("status") not in KNOWN or
                type(p.get("year")) is not int or
                not isinstance(p.get("title"), str) or
                not 1 <= len(p["title"]) <= 200 or
                not review.paper_topics(p["title"])):
            raise ValueError("invalid prior discovery or validation record")
        if any(p.get(flag) is not False for flag in FIELDS_FALSE):
            raise ValueError("unapproved external methods or lottery skill claim")
        if p["status"] in (TWO_SOURCE, PREVIOUSLY) and (
                p.get("crossref_consistent") is not True or
                p.get("openalex_consistent") is not True):
            raise ValueError("unsubstantiated provider match")
        seen[p["doi"]] = p
    cycle = raw.get("cycle_count")
    if type(cycle) is not int or cycle < 1:
        raise ValueError("invalid previous research cycle")
    return seen, raw["next_topic_index"], {"cycle_count": cycle}


def _candidate(p: dict, *, now: datetime, since: str) -> dict | None:
    doi = p.get("doi")
    title = p.get("title")
    year = p.get("year")
    if (not isinstance(doi, str) or not review.DOI.fullmatch(doi)
            or not isinstance(title, str) or not 1 <= len(title) <= 200
            or type(year) is not int or not int(since[:4]) <= year <= now.year
            or not review.paper_topics(title)):
        return None
    # Never record arbitrary executable instructions as a research plan.
    return {"doi": doi.lower(), "title": title, "year": year}


def run(root: Path, *,
        discover: Callable[[str, str, str], list[dict]] | None = None,
        verify: Callable[[dict], dict] | None = None,
        now: datetime | None = None) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    state_path = out / discovery.STATE
    chain_path = out / discovery.LEDGER
    # SHA anchor the existing harvested bibliography but do not run the
    # stale-draw scientific guard that controls Production research.
    before = {"state": hash_file(state_path), "chain": hash_file(chain_path)}
    state = discovery.read_json(state_path)
    chain = discovery.read_chain(chain_path)
    anchored = review.checked_papers(state, chain)
    if not chain:
        raise ValueError("missing trusted online discovery lineage")
    tip = chain[-1]["record_sha256"]
    previous_path = out / FILE
    previous = (json.loads(previous_path.read_text(encoding="utf-8"))
                if previous_path.exists() else {})
    known, index, metadata = _check_prior(previous, before["state"], tip)
    if not isinstance(known, dict):
        raise ValueError("invalid candidate registry")

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("UTC-aware verification timestamp required")
    now = now.astimezone(timezone.utc)
    stamp = now.isoformat(timespec="seconds")
    since = (now - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    topic = discovery.TOPICS[index]

    def live_search(provider: str, query: str, from_date: str) -> list[dict]:
        fn = discovery.fetch_crossref if provider == "crossref" else discovery.fetch_openalex
        return fn(query, from_date)

    if discover is None:
        discover = live_search
    if verify is None:
        verify = lambda p: verifier.verify_one(p, verifier.public_get_json)

    results = []
    provider_errors = []
    for provider in ("crossref", "openalex"):
        try:
            items = discover(provider, topic, since)
            if not isinstance(items, list) or len(items) > 10:
                raise ValueError("unbounded discovery response")
            for p in items:
                if not isinstance(p, dict):
                    raise ValueError("invalid public bibliographic hit")
                safe = _candidate(p, now=now, since=since)
                if safe is not None:
                    results.append(safe)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                OSError, ValueError, KeyError) as exc:
            # Do not treat API outage or invalid untrusted metadata as an
            # authenticated negative result.
            provider_errors.append({"provider": provider,
                                    "error": "search_unavailable_or_malformed"})

    anchored_dois = {p["doi"] for p in anchored}
    fresh = {}
    for paper in results:
        if paper["doi"] not in fresh:
            fresh[paper["doi"]] = paper
        elif fresh[paper["doi"]] != paper:
            # A conflicting search result must undergo the exact detail check;
            # preserve the initial identity, never declare it corroborated.
            continue
    # Retain no more than MAX_STORED; prioritize NEW items. Neither a
    # search-result appearance nor count of providers is a verification.
    choices = [p for doi, p in fresh.items() if doi not in anchored_dois]
    choices.sort(key=lambda p: (p["doi"] in known, p["doi"]))
    selected = choices[:MAX_CHECKS]
    verified = {}
    checked = []
    for paper in selected:
        record = verify(paper)
        if (not isinstance(record, dict) or record.get("doi") != paper["doi"]
                or record.get("year") != paper["year"]
                or record.get("status") not in KNOWN):
            raise ValueError("invalid independent bibliographic verification")
        if record["status"] in (TWO_SOURCE, PREVIOUSLY) and (
                record.get("crossref_consistent") is not True or
                record.get("openalex_consistent") is not True):
            raise ValueError("false independent provider match")
        record = {
            **paper, **record, "first_seen_utc": (
                known.get(paper["doi"], {}).get("first_seen_utc") or stamp
            ), "last_checked_utc": stamp,
            "last_two_provider_verified_utc": (
                stamp if record["status"] == TWO_SOURCE else
                known.get(paper["doi"], {}).get("last_two_provider_verified_utc")
            ),
            "found_in_anchored_intake": False,
        }
        for key in FIELDS_FALSE:
            record[key] = False
        verified[paper["doi"]] = record
        checked.append({"doi": paper["doi"], "status": record["status"]})
    # Preserve previous corroboration only as STALE unless rechecked.
    for doi, old in known.items():
        if doi not in verified:
            kept = dict(old)
            if kept["status"] == TWO_SOURCE:
                kept["status"] = PREVIOUSLY
            verified[doi] = kept
    candidates = sorted(verified.values(),
                        key=lambda x: (x.get("last_checked_utc", ""), x["doi"]),
                        reverse=True)[:MAX_STORED]
    counts = dict(sorted(Counter(p["status"] for p in candidates).items()))
    verified_relevant = [p for p in candidates
                         if p["status"] == TWO_SOURCE]
    # Externally supplied titles may inform TOPIC CLASSIFICATION but never
    # become executable, persuasive instructions or model code.
    topics = sorted({
        t for p in verified_relevant
        for t in review.paper_topics(p["title"])
        if t in intelligence.SAFE_METHODS
    })
    handoffs = [
        {"topic": t,
         "fixed_safe_review_task": intelligence.SAFE_METHODS[t][0],
         "constraint": intelligence.SAFE_METHODS[t][1],
         "type": "human_review_only",
         "automatic_method_adoption": False,
         "requires_full_text_and_prospective_validation": True}
        for t in topics
    ]
    if {"state": hash_file(state_path), "chain": hash_file(chain_path)} != before:
        raise ValueError("concurrent online source state update; retry")
    report = {
        "version": VERSION,
        "checked_at_utc": stamp,
        "discovery_state_sha256": before["state"],
        "discovery_chain_tip": tip,
        "anchored_known_papers": len(anchored),
        "topic_searched": topic,
        "next_topic_index": (index+1) % len(discovery.TOPICS),
        "cycle_count": metadata.get("cycle_count", 0)+1,
        "window_days": LOOKBACK_DAYS,
        "max_independent_checks_per_cycle": MAX_CHECKS,
        "search_providers": ["crossref", "openalex"],
        "provider_errors": provider_errors,
        "search_hits_before_dedup": len(results),
        "new_unanchored_dois_seen": len(choices),
        "checked": checked,
        "candidate_count": len(candidates),
        "status_counts": counts,
        "candidates": candidates,
        "verified_topics_this_cycle": topics,
        "safe_application_handoffs": handoffs,
        "unverified_external_inputs_do_not_change_models": True,
        "new_optimizer_trials": 0,
        "automatic_paper_method_execution": False,
        "champion_or_production_modified": False,
        "future_oos_modified": False,
        "claim_of_lottery_predictive_improvement": False,
        "provenance_scope": "discovery_sidecar_only_not_SHA_chained_canonical_intake",
    }
    return report


def markdown(data: dict) -> str:
    s = [
        "# Frequent independent online research — audit",
        "",
        f"- UTC: {data['checked_at_utc']}",
        f"- Search topic: {data['topic_searched']}",
        f"- Source catalog: {data['anchored_known_papers']} SHA-anchored works",
        f"- Search results before dedup: {data['search_hits_before_dedup']}",
        f"- New leads identified: {data['new_unanchored_dois_seen']}",
        f"- DOI detail checks this cycle: {len(data['checked'])}",
        f"- API failures: {len(data['provider_errors'])}",
        "",
        "## Current research sidecar verification",
    ]
    for status, number in data["status_counts"].items():
        s.append(f"- {status}: {number}")
    s += ["", "## Fixed, human-review-only applications"]
    for action in data["safe_application_handoffs"]:
        s.append(f"- {action['topic']}: {action['fixed_safe_review_task']}")
    s += [
        "", "Two-provider DOI/title/year matching is NOT peer review,",
        "full-text methodological replication or proof of lottery skill.",
        "The new sidecar is not a canonical preregistration or model authority.",
        "No trial budget, Champion, Production or prospective OOS edits.",
    ]
    return "\n".join(s) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    args = p.parse_args()
    record = run(args.repo_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / FILE).write_text(json.dumps(
        record, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    (args.out_dir / REPORT).write_text(markdown(record), encoding="utf-8")
    print(stable({
        "new_dois": record["new_unanchored_dois_seen"],
        "checked": len(record["checked"]),
        "confirmed_this_cycle": record["status_counts"].get(TWO_SOURCE, 0),
        "topics_for_review": record["verified_topics_this_cycle"],
        "promotion": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
