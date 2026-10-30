#!/usr/bin/env python3
"""Build a public, atomic read-only browser telemetry snapshot.

Read ONLY existing evidence; all output stays under docs/data. Dedicated
workflows retain exclusive authority to freeze, grade, publish and promote.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agent_operations_planner import build_plan
from public_issued_prediction import preview as issued_production_preview
from loto7_evolving_agent import fingerprint_file

VERSION = "loto7-ops-snapshot-v1"
JST = timezone(timedelta(hours=9))
TRUST = "verified_two_result_sources"
SOURCE_FILES = {
    "source": "source_validation.json",
    "council": "agent_role_council_summary.json",
    "research": "v4_research_state.json",
    "holdout": "future_holdout_state.json",
    "signal": "joint_set_v2_signal_oos_summary.json",
    "learning": "continuous_learning_agent_summary.json",
    "champion": "model_champion.json",
    "production": "weekly_production_prediction_state.json",
    "scout": "predictive_expert_agent_summary.json",
    "budget": "research_cycle_guard.json",
}
WORKFLOWS = {
    "continuous_loto7_v4.yml": "継続研究",
    "continuous_learning_agent.yml": "継続学習",
    "agent_role_council.yml": "役割監査",
    "joint_set_v2_signal_oos.yml": "v2将来検証",
    "weekly_production_publisher.yml": "本番発行",
    "friday_result_check_watchdog.yml": "抽せん結果確認",
    "browser_dashboard_ci.yml": "画面検証",
}
# A minimal public projection; never copy arbitrary secrets, portfolios,
# signed payloads, full registered vectors or hidden configuration.
PUBLIC_FIELDS = {
    "source": ("status", "verification", "checked_at_jst", "latest"),
    "council": ("overall", "checked_at_jst", "roles", "handoff_tasks", "latest_resolved_round"),
    "research": ("generation", "total_research_evaluations", "champion_version", "last_run_jst"),
    "holdout": ("status", "trusted_draws", "horizon_trusted_draws", "graded_rounds", "start_target_round"),
    "signal": ("status", "trusted_draws", "horizon_trusted_draws", "current_target_round", "start_target_round", "interim_descriptive"),
    "learning": ("status", "trusted_draws", "current_prefrozen_target", "latest_seen_round", "descriptive_future_only", "drift_monitoring"),
    "champion": ("model_version",),
    "production": ("published", "target_round", "published_at_jst"),
    "scout": ("evaluated_rounds", "scout", "v2_reference", "synthetic_null_p_log_edge"),
    "budget": ("mode", "signal_trials_this_data", "max_signal_trials_per_data"),
}


def error(message: str) -> ValueError:
    return ValueError("dashboard evidence: " + message)


def read_object(path: Path) -> dict:
    if not path.is_file():
        raise error("required public report missing: " + path.name)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise error("not a JSON object: " + path.name)
    return data


def read_sources(out: Path) -> tuple[dict, dict]:
    projected, hashes = {}, {}
    for name, filename in SOURCE_FILES.items():
        source = out / filename
        data = read_object(source)
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        view = {key: data[key] for key in PUBLIC_FIELDS[name] if key in data}
        if name == "source":
            # Expose only the official next-round schedule, not scrape internals.
            view["sources"] = {"official_schedule": data.get("sources", {}).get("official_schedule", {})}
        if name == "council":
            # Reject non-object and escaped HTML is handled by textContent in UI.
            view["roles"] = {name: {
                "status": r.get("status"), "findings": [
                    {"code": f.get("code"), "level": f.get("level"), "evidence": f.get("evidence")}
                    for f in r.get("findings", [])
                ]
            } for name, r in data.get("roles", {}).items()}
            view["handoff_tasks"] = [
                {"owner": t.get("owner"), "priority": t.get("priority"),
                 "issue_code": t.get("issue_code"), "evidence": t.get("evidence")}
                for t in data.get("handoff_tasks", [])
            ]
        if name == "scout":
            # Only mean historical scores, not raw model or training values.
            view["scout"] = {"mean_top7_hits": data.get("scout", {}).get("mean_top7_hits")}
            view["v2_reference"] = {"mean_top7_hits": data.get("v2_reference", {}).get("mean_top7_hits")}
        projected[name] = view
    return projected, hashes


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def result_is_trusted(row: dict) -> bool:
    return str(row.get("trusted", "")).lower() == "true" and row.get("source_verification") == TRUST


def before_draw(row: dict) -> bool:
    frozen = row.get("frozen_at_jst", "")
    date = row.get("draw_date", "")
    try:
        timestamp = datetime.fromisoformat(frozen)
        deadline = datetime.fromisoformat(date + "T20:00:00+09:00")
        return timestamp.tzinfo is not None and timestamp < deadline
    except (TypeError, ValueError):
        return False


def cumulative(values: list[float]) -> list[float]:
    return [round(sum(values[:i]) / i, 10) for i in range(1, len(values) + 1)]


def require_rounds(observed: list[int], expected: list[int], kind: str) -> None:
    if observed != expected or len(observed) != len(set(observed)):
        raise error(kind + ": stored trusted rounds disagree with prospective registration")


def read_portfolio(out: Path, holdout: dict) -> list[dict]:
    data = rows(out / "future_holdout_results.csv")
    expected = [int(r) for r in holdout.get("graded_rounds", [])]
    if not data and not expected:
        return []
    observed = [int(r["round"]) for r in data]
    require_rounds(observed, expected, "portfolio")
    # The ledger also records correctly labelled UNTRUSTED outcomes. Those
    # observations are useful for diagnostics, but must never enter public
    # prospective score series or count toward the fixed trusted horizon.
    if len(data) != int(holdout.get("all_draws", len(expected))):
        raise error("portfolio all-draw count differs from the ledger")
    if not all(before_draw(r) for r in data):
        raise error("portfolio non-prefrozen result")
    trusted_data = []
    for row in data:
        if result_is_trusted(row):
            trusted_data.append(row)
        elif (str(row.get("trusted", "")).lower() != "false"
              or row.get("source_verification") == TRUST):
            raise error("portfolio unverified or contradictory trust flags")
    if len(trusted_data) != int(holdout["trusted_draws"]):
        raise error("portfolio trusted result count differs from 26-draw state")
    vs_random = [float(r["delta_vs_random"]) for r in trusted_data]
    vs_champion = [float(r["delta_vs_champion"]) for r in trusted_data]
    for collection in (vs_random, vs_champion):
        if any(not (-100 < v < 100) for v in collection):
            raise error("portfolio result score out of expected bounds")
    return [
        {"round": int(r["round"]), "date": r["draw_date"],
         "mean_delta_vs_random": cumulative(vs_random)[i],
         "mean_delta_vs_champion": cumulative(vs_champion)[i],
         "holdout_max_hits": int(r["holdout_max_hits"])}
        for i, r in enumerate(trusted_data)
    ]


def read_signal(out: Path, summary: dict, state: dict) -> list[dict]:
    data = rows(out / "joint_set_v2_signal_oos_results.csv")
    trusted = int(summary["trusted_draws"])
    require_rounds(
        [int(r["round"]) for r in data],
        [int(v) for v in state.get("graded_rounds", [])],
        "v2 signal"
    )
    if len(data) != trusted:
        raise error("v2 signal grades disagree with source-of-truth state")
    if data and not all(result_is_trusted(r) and before_draw(r) for r in data):
        raise error("v2 signal result lacks trusted prefrozen vector")
    # Do not let malformed/partially committed rows raise KeyError or be
    # mistaken for a valid scored Future-OOS record.
    required = {
        "round", "draw_date", "bernoulli_log_edge_vs_uniform",
        "bernoulli_brier_edge_vs_uniform", "top7_hits",
    }
    if any(not required.issubset(r) or any(not r.get(key) for key in required)
           for r in data):
        raise error("v2 signal result lacks required scoring evidence")
    log_edges = [float(r["bernoulli_log_edge_vs_uniform"]) for r in data]
    brier_edges = [float(r["bernoulli_brier_edge_vs_uniform"]) for r in data]
    top7 = [int(r["top7_hits"]) for r in data]
    return [
        {"round": int(r["round"]), "date": r["draw_date"],
         "mean_log_edge": cumulative(log_edges)[i],
         "mean_brier_edge": cumulative(brier_edges)[i],
         "mean_top7_hits": cumulative(top7)[i]}
        for i, r in enumerate(data)
    ]


def read_learning(out: Path, summary: dict, state: dict) -> list[dict]:
    path = out / "continuous_learning_agent_results.jsonl"
    grades = []
    if path.exists():
        previous = "GENESIS"
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                raise error("adaptive graded ledger has an empty line")
            record = json.loads(line)
            if record.get("previous_record_sha256") != previous:
                raise error("adaptive graded ledger SHA chain broken")
            digest = record.get("record_sha256")
            original = {key: value for key, value in record.items() if key != "record_sha256"}
            canonical = json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            if hashlib.sha256(canonical.encode()).hexdigest() != digest:
                raise error("adaptive graded ledger SHA integrity failure")
            if record.get("source_verification") != TRUST:
                raise error("adaptive ledger has an untrusted actual result")
            previous = digest
            grades.append(record)
    require_rounds(
        [int(g["target_round"]) for g in grades],
        [int(x) for x in state.get("graded_rounds", [])],
        "adaptive signal"
    )
    if len(grades) != int(summary["trusted_draws"]):
        raise error("adaptive ledger differs from registered grading state")
    log_edges = [float(r["log_edge"]) for r in grades]
    brier_edges = [float(r["brier_edge"]) for r in grades]
    top7 = [int(r["top7_hits"]) for r in grades]
    return [
        {"round": int(r["target_round"]), "date": r["draw_date"],
         "mean_log_edge": cumulative(log_edges)[i],
         "mean_brier_edge": cumulative(brier_edges)[i],
         "mean_top7_hits": cumulative(top7)[i]}
        for i, r in enumerate(grades)
    ]


def read_future_series(out: Path, sources: dict) -> dict:
    signal_state = read_object(out / "joint_set_v2_signal_oos_state.json")
    learning_state = read_object(out / "continuous_learning_agent_state.json")
    return {
        "portfolio": read_portfolio(out, sources["holdout"]),
        "v2": read_signal(out, sources["signal"], signal_state),
        "adaptive": read_learning(out, sources["learning"], learning_state),
        "scope": "genuinely_prospective_prefrozen_only_descriptive_no_automatic_promotion",
    }


def workflows_from_api(repository: str, token: str | None = None, timeout: int = 10) -> list[dict]:
    if repository != "Joker7822/LOTO7_AI_AGENT":
        raise error("unexpected repository for workflow run telemetry")
    output = []
    for filename, label in WORKFLOWS.items():
        url = f"https://api.github.com/repos/{repository}/actions/workflows/{filename}/runs?branch=main&per_page=5"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "loto7-monitor-snapshot"}
        if token:
            headers["Authorization"] = "Bearer " + token
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
            runs = data.get("workflow_runs", [])
            if not isinstance(runs, list):
                raise ValueError("malformed run list")
            latest = runs[0] if runs else {}
            status = latest.get("status")
            conclusion = latest.get("conclusion")
            if not latest:
                health = "unknown"
            elif status != "completed":
                health = "running" if status in ("queued", "waiting", "in_progress", "pending", "requested") else "unknown"
            else:
                health = "ok" if conclusion == "success" else "warning" if conclusion in ("skipped", "neutral", "cancelled") else "block"
            link = latest.get("html_url", "")
            if link and not link.startswith(f"https://github.com/{repository}/actions/runs/"):
                raise ValueError("unexpected workflow URL")
            output.append({
                "file": filename, "label": label, "health": health,
                "status": status, "conclusion": conclusion,
                "run_id": latest.get("id"),
                "url": link or None, "updated_at": latest.get("updated_at"),
                "recent_failure_count": sum(1 for r in runs if r.get("conclusion") in ("failure", "timed_out")),
            })
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            output.append({
                "file": filename, "label": label, "health": "unknown", "status": None,
                "conclusion": None, "url": None, "run_id": None, "updated_at": None,
                "recent_failure_count": None, "error": type(exc).__name__,
            })
    return output


def scientific_research_projection(root: Path, out: Path) -> tuple[dict, str | None]:
    """Public summaries only, never candidate full vectors or graded numbers."""
    path = out / "advanced_validation_lab_summary.json"
    if not path.exists():
        return {"status": "not_yet_published", "future_draws": None}, None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    raw = read_object(path)
    if raw.get("version") != "advanced-validation-lab-v1":
        return {"status": "invalid_protocol_version", "future_draws": None}, digest
    candidate_state = read_object(out / "accuracy_extension_agent_state.json")
    candidate_reg = read_object(out / "accuracy_extension_agent_registration.json")
    current_history = fingerprint_file(root / "loto7.csv")
    new_hypothesis = raw.get("source_model_manifest_sha256") == candidate_reg["algorithm_manifest"]["manifest_sha256"]
    future = raw.get("future_e_monitor", {})
    hist = raw.get("historical_exploratory", {})
    observed = future.get("verified_prefrozen_draws")
    if (raw.get("historical_data_sha256") != current_history or not new_hypothesis
            or not isinstance(observed, int) or observed != candidate_state.get("trusted_draws")
            or len(future.get("series", [])) != observed):
        return {"status": "stale_or_mismatched_evidence", "future_draws": None}, digest
    best = hist.get("matched_full_budget_fair_draws", {})
    bootstrap = hist.get("paired_block_bootstrap", {})
    original = hist.get("original_four", {})
    candidate = hist.get("candidate_five", {})
    result = {
        "status": "verified_diagnostic_only",
        "model_family": "four_vs_five_experts",
        "candidate_protocol": "predeclared_701_start",
        "history_round_start": hist.get("round_start"),
        "history_round_end": hist.get("round_end"),
        "original_four_top7": original.get("mean_top7_hits"),
        "candidate_five_top7": candidate.get("mean_top7_hits"),
        "original_four_log_edge": original.get("mean_log_edge"),
        "candidate_five_log_edge": candidate.get("mean_log_edge"),
        "historical_selection_adjusted_p_exploratory_only": best.get(
            "max_statistic_selection_adjusted_empirical_tail_p"
        ),
        "historical_matched_fair_worlds": best.get("worlds"),
        "historical_paired_block_ci": {
            "low95": bootstrap.get("low95"), "high95": bootstrap.get("high95"),
            "mean_five_minus_four": bootstrap.get("mean_five_minus_four")
        },
        "future_draws": observed,
        "future_current_e": future.get("current_e_value"),
        "future_max_e": future.get("max_e_value"),
        "future_threshold": future.get("ville_threshold"),
        "future_threshold_crossed": future.get("threshold_crossed"),
        "future_e_series": [
            {"round": r.get("round"), "e_value": r.get("e_value")}
            for r in future.get("series", [])
        ],
        "inference_scope": "conditional_fair_null_for_one_future_prefrozen_stream_only",
        "promotion_eligible": False,
    }
    return result, digest


def always_on_research_projection(out: Path) -> tuple[dict, str | None]:
    """Expose only nonsecret, unreviewed research bibliographic metadata."""
    path = out / "always_on_accuracy_research_state.json"
    if not path.exists():
        return {"status": "not_yet_started"}, None
    raw = read_object(path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    if (raw.get("version") != "always-on-accuracy-research-v1"
            or raw.get("read_only_scientific_activity") is not True
            or raw.get("promotion_authorized") is not False):
        return {"status": "invalid_or_unsafe"}, checksum
    papers = []
    for paper in raw.get("papers", [])[:8]:
        doi = paper.get("doi", "")
        url = paper.get("url", "")
        if (not isinstance(doi, str) or not doi.startswith("10.")
                or not isinstance(url, str) or not url.startswith("https://doi.org/")):
            continue
        papers.append({
            "title": str(paper.get("title", ""))[:200], "url": url[:240],
            "year": paper.get("year"), "review_status": "unreviewed"
        })
    return {
        "status": raw.get("status"),
        "sequence": raw.get("sequence"),
        "last_activity_jst": raw.get("last_activity_jst"),
        "current_phase": raw.get("current_phase"),
        "current_activity": str(raw.get("current_activity", ""))[:150],
        "online_search_status": str(raw.get("online_search_status", ""))[:80],
        "research_mode": raw.get("research_mode"),
        "two_source_verified": raw.get("two_source_verified"),
        "new_papers_count": raw.get("new_papers_count"),
        "papers": papers,
        "promotion_authorized": False,
        "review_notes": [str(note)[:160] for note in raw.get("review_notes", [])[:6]],
    }, checksum


def research_application_projection(root: Path, out: Path) -> tuple[dict, str | None]:
    """Only show bounded, review-only readiness, never untrusted commands."""
    path = out / "research_application_readiness.json"
    if not path.is_file():
        return {"status": "not_yet_published"}, None
    raw = read_object(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    research_mode = read_object(out / "research_cycle_guard.json").get("mode")
    if (raw.get("version") != "research-application-gate-v1"
            or raw.get("input_draw_sha256") != fingerprint_file(root / "loto7.csv")
            or raw.get("research_mode") != research_mode
            or raw.get("new_experiments_executed") != 0
            or raw.get("automatic_model_training") is not False
            or raw.get("auto_production_release") is not False
            or raw.get("future_oos_or_production_changed") is not False
            or raw.get("actual_prediction_accuracy_improvement_verified") is not False
            or raw.get("synthetic_control", {}).get("status") != "synthetic_controls_passed"):
        return {"status": "stale_or_unsafe"}, digest
    allowed = {
        "bibliography_needs_verification",
        "awaiting_full_text_and_methodology_review",
    }
    queue = raw.get("application_queue")
    if not isinstance(queue, list) or len(queue) > 6 or raw.get("proposal_count") != len(queue):
        return {"status": "stale_or_unsafe"}, digest
    tasks = []
    for task in queue:
        if (task.get("status") not in allowed
                or task.get("experiment_execution_allowed") is not False
                or task.get("production_adoption_allowed") is not False
                or task.get("requires_human_approval") is not True):
            return {"status": "stale_or_unsafe"}, digest
        tasks.append({
            "topic": str(task.get("topic", ""))[:50],
            "status": task["status"],
            "two_provider_matches": len(task.get("two_provider_matched_dois", [])),
            "requires_human_approval": True,
        })
    return {
        "status": "research_review_ready_only",
        "research_mode": research_mode,
        "trusted_result_source": raw.get("trusted_result_source") is True,
        "papers": raw.get("reviewed_publication_count"),
        "verified_dois": raw.get("two_provider_bibliographic_matches"),
        "proposal_count": len(tasks),
        "synthetic_control": "passed",
        "actual_prediction_accuracy_improvement_verified": False,
        "tasks": tasks,
    }, digest


def research_priority_projection(root: Path, out: Path) -> tuple[dict, str | None]:
    """Only whitelist safe research next-actions; never project executable commands."""
    path = out / "research_autonomy_priority_queue.json"
    if not path.exists():
        return {"status": "not_yet_published", "tasks": []}, None
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    raw = read_object(path)
    auth = raw.get("authority", {})
    forbidden = (
        "automated_model_training", "research_budget_override",
        "retroactive_future_freeze", "registered_oos_modification",
        "production_or_champion_update", "workflows_dispatched",
    )
    guard = read_object(out / "research_cycle_guard.json")
    source = read_object(out / "source_validation.json")
    trusted = (source.get("status") == "ok" and
               source.get("verification") == "verified_two_result_sources")
    original = raw.get("tasks")
    counts = raw.get("counts")
    if (raw.get("version") != "research-priority-orchestrator-v1"
            or not isinstance(auth, dict)
            or any(auth.get(k) is not False for k in forbidden)
            or raw.get("draw_history_sha256") != fingerprint_file(root / "loto7.csv")
            or raw.get("research_mode") != guard.get("mode")
            or raw.get("source_two_verified") is not trusted
            or raw.get("latest_source_round") != source.get("latest", {}).get("round")
            or not isinstance(original, list) or len(original) > 20
            or not isinstance(counts, dict)
            or any(counts.get(key) != sum(x.get("priority") == key for x in original)
                   for key in ("block", "watch", "info"))):
        return {"status": "stale_or_unsafe", "tasks": []}, checksum
    priority = {"block": 0, "watch": 1, "info": 2}
    lanes = {"source_integrity", "prospective_integrity",
             "research_governance", "bibliography", "experiment_review"}
    visible = []
    previous = 0
    seen = set()
    for row in original:
        if (not isinstance(row, dict) or row.get("priority") not in priority
                or row.get("lane") not in lanes
                or row.get("safe_autonomous_action") != "report_only"
                or row.get("human_approval_required_for_model_change") is not True
                or row.get("forecast_or_production_change_authorized") is not False
                or row.get("new_optimizer_trials_authorized") is not False
                or priority[row["priority"]] < previous
                or not isinstance(row.get("id"), str)
                or not re.fullmatch(r"[0-9a-f]{16}", row["id"])
                or row["id"] in seen):
            return {"status": "stale_or_unsafe", "tasks": []}, checksum
        previous = priority[row["priority"]]
        seen.add(row["id"])
        if len(visible) < 6:
            visible.append({
                "priority": row["priority"],
                "lane": row["lane"],
                "owner": str(row.get("owner", ""))[:70],
                "title": str(row.get("title", ""))[:110],
                "reason": str(row.get("reason", ""))[:200],
                "next_step": str(row.get("next_step", ""))[:280],
                "safe_autonomous_action": "report_only",
            })
    return {
        "status": "audited_research_plan",
        "research_mode": guard["mode"],
        "source_two_verified": trusted,
        "total_tasks": len(original),
        "counts": {k: counts[k] for k in ("block", "watch", "info")},
        "tasks": visible, "promotion_authorized": False,
    }, checksum


def create_snapshot(root: Path, workflows: list[dict], *, now: datetime | None = None,
                    ref: str | None = None) -> dict:
    out = root / "loto7_agent_output"
    sources, sha = read_sources(out)
    series = read_future_series(out, sources)
    latest_prediction, prediction_hashes = issued_production_preview(
        root, sources["source"], read_object(out / "weekly_production_prediction_state.json")
    )
    sha.update(prediction_hashes)
    scientific, research_hash = scientific_research_projection(root, out)
    always_on, activity_hash = always_on_research_projection(out)
    application, application_hash = research_application_projection(root, out)
    priorities, priority_hash = research_priority_projection(root, out)
    if priority_hash is not None:
        sha["research_priority"] = priority_hash
    if application_hash is not None:
        sha["application_gate"] = application_hash
    if activity_hash is not None:
        sha["always_on_research"] = activity_hash
    if research_hash is not None:
        sha["scientific_validation"] = research_hash
    if len(workflows) != len(WORKFLOWS):
        raise error("workflow telemetry missing items")
    filenames = [x.get("file") for x in workflows]
    if filenames != list(WORKFLOWS):
        raise error("workflow order/identity mismatch")
    moment = (now or datetime.now(JST)).astimezone(JST)
    snapshot = {
        "version": VERSION,
        "generated_at_jst": moment.isoformat(timespec="seconds"),
        "source_commit": ref or subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "state_hashes_sha256": hashlib.sha256(json.dumps(sha, sort_keys=True).encode()).hexdigest(),
        "sources": sources, "workflows": workflows, "series": series,
        "scientific_validation": scientific,
        "latest_prediction": latest_prediction,
        "always_on_accuracy": always_on,
        "research_application": application,
        "research_priorities": priorities,
        "limitations": "Read-only point-in-time repository state; API run statuses sampled separately. Historical charts never constitute prospective proof. No Production promotion.",
    }
    snapshot["operations_plan"] = build_plan(snapshot, now=moment)
    return snapshot


def main() -> int:
    p = argparse.ArgumentParser(description="Build atomic public dashboard telemetry from main evidence")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, default=Path("docs/data/dashboard_snapshot.json"))
    p.add_argument("--fetch-workflows", action="store_true")
    args = p.parse_args()
    if args.fetch_workflows:
        workflows = workflows_from_api("Joker7822/LOTO7_AI_AGENT", os.environ.get("GITHUB_TOKEN"))
    else:
        workflows = [
            {"file": name, "label": label, "health": "unknown", "status": None, "conclusion": None,
             "run_id": None, "url": None, "updated_at": None, "recent_failure_count": None}
            for name, label in WORKFLOWS.items()
        ]
    snapshot = create_snapshot(args.repo_root.resolve(), workflows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "version": snapshot["version"], "portfolio_draws": len(snapshot["series"]["portfolio"]),
        "signal_draws": len(snapshot["series"]["v2"]),
        "adaptive_draws": len(snapshot["series"]["adaptive"]),
        "workflows": len(workflows), "source_commit": snapshot["source_commit"][:12],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
