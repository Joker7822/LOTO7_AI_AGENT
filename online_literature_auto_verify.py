#!/usr/bin/env python3
"""Independently refresh *bibliographic identity* for the entire online DOI queue.

Rotates through every SHA-anchored discovery record, not merely the first
three. Crossref/OpenAlex metadata is untrusted; neither a matching DOI nor
an abstract proves peer review, usable methods, or lottery prediction skill.

This lane is deliberately INDEPENDENT of the lottery science freshness guard:
outdated #699 research does not authorize model work, but it must not block
public bibliographic checking. Only research_verified_publications.json and
its descriptive Markdown report may be written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import always_on_accuracy_agent as discovery
import research_evidence_resilience as verify
import research_literature_pipeline as literature

VERSION = "online-bibliography-rotation-v1"
REPORT = "research_verified_publications_auto_report.md"
MAX_PER_RUN = 3
MAX_PAPERS = 36
SAFETY_FLAGS = (
    "full_text_reviewed", "peer_review_confirmed",
    "methods_reproduced_from_paper", "lottery_prediction_improved",
)
ALLOWED = {
    "two_provider_bibliography_matched", "previously_verified_not_refreshed",
    "single_provider_only", "conflict_do_not_use", "unavailable",
    "not_yet_checked",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prior_records(previous: dict, state_sha: str, chain_tip: str,
                   paper_map: dict[str, dict]) -> tuple[dict[str, dict], int]:
    if not previous:
        return {}, 0
    if (previous.get("version") != verify.VERSION or
            previous.get("discovery_state_sha256") != state_sha or
            previous.get("discovery_tip_sha256") != chain_tip):
        # New discovery SHA means an old match cannot be silently carried
        # forward to newly changed titles/years; reverify from scratch.
        return {}, 0
    records = previous.get("verifications")
    if not isinstance(records, list) or len(records) > MAX_PAPERS:
        raise ValueError("malformed previous bibliography")
    checked = {}
    for rec in records:
        if not isinstance(rec, dict):
            raise ValueError("invalid prior bibliographic record")
        doi = rec.get("doi")
        if (doi not in paper_map or doi in checked or
                rec.get("year") != paper_map[doi]["year"] or
                rec.get("status") not in ALLOWED):
            raise ValueError("prior DOI list or status mismatch")
        if any(rec.get(flag) is not False for flag in (
            "full_text_reviewed", "peer_review_confirmed",
            "lottery_prediction_improved",
        )) or rec.get("methods_reproduced_from_paper") is True:
            raise ValueError("unapproved methodological claims in bibliography")
        if rec["status"] in ("two_provider_bibliography_matched",
                             "previously_verified_not_refreshed") and (
                rec.get("crossref_consistent") is not True or
                rec.get("openalex_consistent") is not True):
            raise ValueError("forged two-provider bibliographic status")
        checked[doi] = rec
    if set(checked) != set(paper_map):
        # Keep the unchanged known DOI records, but do not assert an
        # all-paper previous verification after a partial file.
        return {}, 0
    cursor = previous.get("rotation_next_index", 0)
    if type(cursor) is not int or cursor < 0 or cursor >= max(1, len(paper_map)):
        raise ValueError("invalid bounded verification cursor")
    return checked, cursor


def _priority_indices(out: Path, state_sha: str, chain_tip: str,
                      papers: list[dict], known: dict[str, dict],
                      previous: dict) -> tuple[list[int], str | None, int]:
    """Trusted queue may steer ONE bounded DOI check; stale plans steer zero.

    Recompute selection from actual corroboration statuses, never execute a
    task's free-text instructions or let a task bypass source attestation.
    """
    path = out / "research_autonomy_priority_queue.json"
    evidence = out / verify.EVIDENCE
    if not path.is_file() or not evidence.is_file():
        return [], None, 0
    queue_sha = digest(path)
    queue = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(queue, dict):
        raise ValueError("priority queue is not an object")
    if (queue.get("version") != "research-priority-orchestrator-v1"
            or queue.get("input_evidence_sha256", {}).get("bibliography")
                != digest(evidence)
            or queue.get("source_two_verified") is not True
            or queue.get("authority", {}).get("workflows_dispatched") is not False
            or queue.get("authority", {}).get("production_or_champion_update") is not False):
        return [], None, 0  # A stale queue must never be an authority.
    codes = set()
    for item in queue.get("tasks", []):
        if not isinstance(item, dict):
            raise ValueError("malformed research priority task")
        if item.get("lane") != "bibliography":
            continue
        if (item.get("safe_autonomous_action") != "report_only"
                or item.get("forecast_or_production_change_authorized") is not False
                or item.get("new_optimizer_trials_authorized") is not False):
            raise ValueError("attempt to elevate a bibliography priority")
        codes.add(item.get("code"))
    priority_statuses = []
    for code, status in (
        ("REVIEW_BIBLIO_CONFLICTS", "conflict_do_not_use"),
        ("VERIFY_UNCHECKED_DOIS", "not_yet_checked"),
        ("RETRY_SINGLE_PROVIDER", "single_provider_only"),
    ):
        if code in codes:
            priority_statuses.append(status)
    indices = [i for status in priority_statuses
               for i, paper in enumerate(papers)
               if known.get(paper["doi"], {}).get("status") == status]
    if not indices:
        return [], queue_sha, 0
    cursor = previous.get("priority_rotation_cursor", 0)
    if type(cursor) is not int or cursor < 0:
        raise ValueError("invalid priority rotation cursor")
    return indices, queue_sha, cursor % len(indices)


def build(root: Path, *, fetch: Callable[[str], tuple[dict, int]] | None = None,
          now: datetime | None = None) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    state_path = out / discovery.STATE
    chain_path = out / discovery.LEDGER
    state = discovery.read_json(state_path)
    journal = discovery.read_chain(chain_path)
    papers = literature.checked_papers(state, journal)
    if len(papers) > MAX_PAPERS or len({p["doi"] for p in papers}) != len(papers):
        raise ValueError("research DOI intake exceeds limit or has duplicates")
    if not journal:
        raise ValueError("no trusted bibliographic discovery chain")
    if (state.get("last_record_sha256") != journal[-1]["record_sha256"] or
            state.get("sequence") != len(journal)):
        raise ValueError("state/chain tip inconsistency")
    state_sha = digest(state_path)
    tip = journal[-1]["record_sha256"]
    paper_map = {p["doi"]: p for p in papers}
    previous = verify.read_prior(out / verify.EVIDENCE)
    known, start = _prior_records(previous, state_sha, tip, paper_map)

    fetch = fetch or verify.public_get_json
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("verification time must be timezone aware")
    stamp = now.astimezone(timezone.utc).isoformat(timespec="seconds")
    size = len(papers)
    count = min(MAX_PER_RUN, size)
    priority, queue_sha, priority_cursor = _priority_indices(
        out, state_sha, tip, papers, known, previous
    )
    selected = []
    next_cursor = previous.get("priority_rotation_cursor", 0)
    if priority and count:
        selected.append(priority[priority_cursor])
        next_cursor = (priority_cursor + 1) % len(priority)
    # Reserve the remaining two slots for the round-robin so that stale or
    # continually conflicting citations cannot starve the rest of the corpus.
    rotation = []
    for offset in range(size):
        index = (start + offset) % size
        if index not in selected:
            rotation.append(index)
            if len(selected) + len(rotation) == count:
                break
    selected.extend(rotation)
    positions = set(selected)
    refreshed = []
    failures = 0
    output = []
    for index, paper in enumerate(papers):
        old = known.get(paper["doi"])
        if index in positions:
            item = verify.verify_one(paper, fetch)
            item["last_checked_at_utc"] = stamp
            item["verification_attempts"] = (
                min(1_000_000, int(old.get("verification_attempts", 0)) + 1)
                if old else 1
            )
            item["last_two_provider_matched_at_utc"] = (
                stamp if item["status"] == "two_provider_bibliography_matched"
                else old.get("last_two_provider_matched_at_utc") if old else None
            )
            # Total provider outage: preserve previous VERIFIED identity only
            # as STALE. An explicit identity conflict is never suppressed.
            if (item["status"] == "unavailable" and old and
                    old["status"] in ("two_provider_bibliography_matched",
                                      "previously_verified_not_refreshed")):
                errors = item["source_errors"]
                item = {**old, "status": "previously_verified_not_refreshed",
                        "last_checked_at_utc": stamp,
                        "verification_attempts": item["verification_attempts"],
                        "source_errors": errors}
            refreshed.append({"doi": paper["doi"], "status": item["status"]})
            failures += len(item.get("source_errors", {}))
        elif old:
            item = dict(old)
            if item["status"] == "two_provider_bibliography_matched":
                item["status"] = "previously_verified_not_refreshed"
        else:
            item = {"doi": paper["doi"], "year": paper["year"],
                    "status": "not_yet_checked"}
        # Explicitly deny extrapolation from metadata to scientific results.
        for flag in SAFETY_FLAGS:
            item[flag] = False
        output.append(item)

    counts = Counter(p["status"] for p in output)
    latest_draw = state.get("latest_resolved_round")
    if type(latest_draw) is not int or latest_draw < 1:
        raise ValueError("malformed discovery round")
    result = {
        "version": verify.VERSION,
        "auto_verifier_version": VERSION,
        "discovery_state_sha256": state_sha,
        "discovery_tip_sha256": tip,
        "research_mode": state["research_mode"],
        "latest_round": latest_draw,
        "searched_this_cycle": bool(selected),
        "initial_verification_attempted": True,
        "verification_reason": "independent_rotating_online_bibliography",
        "max_dois_per_cycle": MAX_PER_RUN,
        "rotation_start_index": start,
        "rotation_next_index": (start + len(rotation)) % size if size else 0,
        "priority_queue_sha256": queue_sha,
        "priority_rotation_cursor": next_cursor,
        "priority_dois_checked": [papers[i]["doi"] for i in selected[:1]]
            if priority else [],
        "rotation_total_candidates": size,
        "rotation_attempted_dois": [papers[i]["doi"] for i in selected],
        "verification_time_utc": stamp,
        "verifications": output,
        "two_provider_matches_this_cycle": sum(
            rec["status"] == "two_provider_bibliography_matched"
            for rec in output
        ),
        "verification_status_counts": dict(sorted(counts.items())),
        "provider_failures_or_conflicts_this_cycle": failures,
        "full_text_reviewed_count": 0,
        "automatic_adoption": False,
        "future_registry_changed": False,
        "production_changed": False,
    }
    return result


def markdown(result: dict) -> str:
    c = result["verification_status_counts"]
    lines = [
        "# Online literature automatic verification",
        "",
        f"- Research source draw (NOT current lottery result): #{result['latest_round']}",
        f"- DOI candidates: {result['rotation_total_candidates']}",
        f"- Attempted this cycle: {len(result['rotation_attempted_dois'])} / "
        f"{result['max_dois_per_cycle']} max",
        f"- Next rotation index: {result['rotation_next_index']}",
        f"- Source SHA256: `{result['discovery_state_sha256']}`",
        f"- SHA chain tip: `{result['discovery_tip_sha256']}`",
        f"- Run (UTC): {result['verification_time_utc']}",
        "", "## Bibliographic status",
    ]
    for status in sorted(ALLOWED):
        lines.append(f"- {status}: {c.get(status, 0)}")
    lines.extend(["", "## DOI records checked this cycle"])
    for doi in result["rotation_attempted_dois"]:
        rec = next(x for x in result["verifications"] if x["doi"] == doi)
        lines.append(f"- `{doi}`: **{rec['status']}**")
    lines += [
        "", "**Independent Crossref/OpenAlex matching checks DOI, title and year,",
        "not peer-review status, full-text accuracy, reproducibility or real",
        "lottery prediction skill.** No new optimizer trials, automatic model",
        "adoption, Champion promotion, or future OOS rewrites.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Rotate independent online DOI checks")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--output-dir", type=Path,
                   default=Path("loto7_agent_output"))
    args = p.parse_args()
    report = build(args.repo_root)
    target = args.output_dir
    target.mkdir(parents=True, exist_ok=True)
    (target / verify.EVIDENCE).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (target / REPORT).write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "checked": report["rotation_attempted_dois"],
        "status": report["verification_status_counts"],
        "next_index": report["rotation_next_index"],
        "automatic_adoption": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
