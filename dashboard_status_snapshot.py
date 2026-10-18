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
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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
    if len(data) != int(holdout["trusted_draws"]):
        raise error("portfolio trusted result count differs from 26-draw state")
    if not all(result_is_trusted(r) and before_draw(r) for r in data):
        raise error("portfolio unverified or non-prefrozen result")
    vs_random = [float(r["delta_vs_random"]) for r in data]
    vs_champion = [float(r["delta_vs_champion"]) for r in data]
    for collection in (vs_random, vs_champion):
        if any(not (-100 < v < 100) for v in collection):
            raise error("portfolio result score out of expected bounds")
    return [
        {"round": int(r["round"]), "date": r["draw_date"],
         "mean_delta_vs_random": cumulative(vs_random)[i],
         "mean_delta_vs_champion": cumulative(vs_champion)[i],
         "holdout_max_hits": int(r["holdout_max_hits"])}
        for i, r in enumerate(data)
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


def create_snapshot(root: Path, workflows: list[dict], *, now: datetime | None = None,
                    ref: str | None = None) -> dict:
    out = root / "loto7_agent_output"
    sources, sha = read_sources(out)
    series = read_future_series(out, sources)
    if len(workflows) != len(WORKFLOWS):
        raise error("workflow telemetry missing items")
    filenames = [x.get("file") for x in workflows]
    if filenames != list(WORKFLOWS):
        raise error("workflow order/identity mismatch")
    moment = (now or datetime.now(JST)).astimezone(JST)
    return {
        "version": VERSION,
        "generated_at_jst": moment.isoformat(timespec="seconds"),
        "source_commit": ref or subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "state_hashes_sha256": hashlib.sha256(json.dumps(sha, sort_keys=True).encode()).hexdigest(),
        "sources": sources, "workflows": workflows, "series": series,
        "limitations": "Read-only point-in-time repository state; API run statuses sampled separately. Historical charts never constitute prospective proof. No Production promotion.",
    }


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
