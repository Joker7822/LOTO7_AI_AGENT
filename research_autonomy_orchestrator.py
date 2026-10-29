#!/usr/bin/env python3
"""Guarded autonomous research queue: choose safe next work, not new lottery bets.

Consumes only evidence already audited by existing research agents. Distinguishes
data blockages, harmless waiting, human methodology review and safe repeatable
bibliographic verification. Cannot run models, change source results or alter
registered prospective experiments/Production.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import always_on_accuracy_agent as discovery
import research_application_gate as gate
import research_evidence_resilience as verification
import research_literature_pipeline as literature
import research_data_quality as quality_guard

VERSION = "research-priority-orchestrator-v1"
QUEUE = "research_autonomy_priority_queue.json"
REPORT = "research_autonomy_priority_report.md"
JST = timezone(timedelta(hours=9))
SEVERITY = {"block": 0, "watch": 1, "info": 2}
ALLOWED_LANES = {"source_integrity", "prospective_integrity",
                 "research_governance", "bibliography", "experiment_review"}
ALLOWED_OWNERS = {"source_verifier", "oos_custodian", "research_governor",
                  "literature_verifier", "methodology_reviewer"}
SAFE_DOI = re.compile(r"10\.\d{4,9}/[a-z0-9._;():/-]{1,130}\Z", re.I)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def task(code: str, severity: str, lane: str, owner: str, title: str,
         reason: str, next_step: str, evidence: str,
         *, doi: str | None = None) -> dict:
    if severity not in SEVERITY or lane not in ALLOWED_LANES or owner not in ALLOWED_OWNERS:
        raise ValueError("unknown research action category")
    if doi is not None and not SAFE_DOI.fullmatch(doi):
        raise ValueError("invalid DOI in research work item")
    identity = digest((VERSION + "|" + code + "|" + (doi or "")).encode())[:16]
    return {
        "id": identity, "code": code, "priority": severity,
        "lane": lane, "owner": owner, "title": title,
        "reason": reason, "next_step": next_step,
        "evidence": evidence, "doi_url": "https://doi.org/" + doi if doi else None,
        "human_approval_required_for_model_change": True,
        "safe_autonomous_action": "report_only",
        "new_optimizer_trials_authorized": False,
        "forecast_or_production_change_authorized": False,
    }



FEEDBACK_VERSION = "research-action-feedback-v1"
BACKLOG_KEYS = {
    "VERIFY_UNCHECKED_DOIS": "unchecked_count",
    "REVIEW_BIBLIO_CONFLICTS": "conflict_count",
    "RETRY_SINGLE_PROVIDER": "single_count",
}
SAFE_TASK_CODE = re.compile(r"(?:[A-Z_]+|REVIEW_METHOD:[a-z_]+)\Z")
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")


def measured_backlog(item: dict | None) -> int | None:
    """Strictly parse bounded counts from locally authored action evidence."""
    if not isinstance(item, dict):
        return None
    key = BACKLOG_KEYS.get(item.get("code"))
    evidence = item.get("evidence")
    if not isinstance(evidence, str):
        return None
    if key:
        match = re.fullmatch(re.escape(key) + r"=(0|[1-9]\d{0,5})", evidence)
        return int(match.group(1)) if match else None
    if item.get("code") == "REVIEW_DATA_QUALITY":
        match = re.fullmatch(r"quality_codes=([A-Z_]+(?:,[A-Z_]+)*)", evidence)
        return len(match.group(1).split(",")) if match else None
    return None


def previous_queue_is_eligible(candidate: dict, *, info: dict,
                               clock: datetime) -> bool:
    """Past advisory output is bounded telemetry, never an authority source."""
    if (candidate.get("version") != VERSION
            or candidate.get("draw_history_sha256") != info["draw_history_sha256"]
            or candidate.get("source_two_verified") is not info["two_source_verified"]
            or candidate.get("research_mode") != info["research_mode"]):
        return False
    authority = candidate.get("authority")
    if (not isinstance(authority, dict)
            or authority.get("scope") != "audited_advisory_queue_only"
            or any(authority.get(k) is not False for k in (
                "automated_model_training", "research_budget_override",
                "retroactive_future_freeze", "registered_oos_modification",
                "production_or_champion_update", "workflows_dispatched"))):
        return False
    evidence = candidate.get("input_evidence_sha256")
    if (not isinstance(evidence, dict)
            or set(evidence) != {"application", "proposals", "bibliography", "source"}
            or any(not isinstance(x, str) or not HEX_SHA.fullmatch(x)
                   for x in evidence.values())):
        return False
    try:
        timestamp = datetime.fromisoformat(candidate["latest_audit_at_jst"])
    except (KeyError, ValueError, TypeError):
        return False
    if (timestamp.tzinfo is None or timestamp.utcoffset() is None
            or not timedelta(hours=1) <= clock - timestamp <= timedelta(days=7)):
        return False
    tasks = candidate.get("tasks")
    if not isinstance(tasks, list) or len(tasks) > 25:
        return False
    seen = set()
    for item in tasks:
        if not isinstance(item, dict):
            return False
        code = item.get("code")
        if not isinstance(code, str) or not SAFE_TASK_CODE.fullmatch(code):
            return False
        identifier = digest((VERSION + "|" + code + "|").encode())[:16]
        if (identifier != item.get("id") or identifier in seen
                or item.get("priority") not in SEVERITY
                or item.get("safe_autonomous_action") != "report_only"
                or item.get("new_optimizer_trials_authorized") is not False
                or item.get("forecast_or_production_change_authorized") is not False):
            return False
        seen.add(identifier)
        cycles = item.get("recurrence_cycles")
        factors = item.get("priority_factors")
        if (type(cycles) is not int or not 1 <= cycles <= 20
                or not isinstance(factors, dict)
                or not {"impact", "verified_backlog", "unresolved_recurrence"} <= set(factors)
                or any(type(n) is not int or n < -5 or n > 100
                       for n in factors.values())
                or item.get("priority_score") != sum(factors.values())):
            return False
    counts = candidate.get("counts")
    return (isinstance(counts, dict)
            and counts == {k: sum(t["priority"] == k for t in tasks) for k in SEVERITY}
            and candidate.get("top_priority") == (tasks[0]["code"] if tasks else None))


def summarize_feedback(tasks: list[dict], previous: dict | None) -> dict:
    old = {item["id"]: item for item in (previous or {}).get("tasks", [])
           if isinstance(item, dict) and isinstance(item.get("id"), str)}
    ids = {item["id"] for item in tasks}
    states = ("new", "improving", "worsening", "unchanged",
              "still_pending_unmeasured")
    return {
        "version": FEEDBACK_VERSION,
        "prior_queue_used": previous is not None,
        "status_counts": {s: sum(x["feedback_state"] == s for x in tasks) for s in states},
        "no_longer_in_queue": sorted({v["code"] for k, v in old.items() if k not in ids}),
        "causal_attribution_established": False,
        "new_training_or_release_authorized": False,
    }

def safe_date(raw: object) -> date:
    if not isinstance(raw, str):
        raise ValueError("missing source draw date")
    return date.fromisoformat(raw)


def build_queue(info: dict, application: dict, raw_source: dict,
                proposal_plan: dict, publications: dict,
                clock: datetime, *, quality: dict | None = None,
                previous: dict | None = None) -> list[dict]:
    clock = clock.astimezone(JST)
    latest = info["latest_round"]
    latest_date = safe_date(raw_source.get("latest", {}).get("date"))
    gap = (clock.date() - latest_date).days
    if gap < 0:
        raise ValueError("source claims future-dated outcome")
    if (application.get("auto_production_release") is not False or
            application.get("automatic_model_training") is not False or
            application.get("future_oos_or_production_changed") is not False or
            application.get("new_experiments_executed") != 0):
        raise ValueError("unapproved automatic training or production authority")
    if (proposal_plan.get("executed_experiments") != 0
            or proposal_plan.get("new_trials_consumed") != 0
            or proposal_plan.get("requires_human_approval") is not True):
        raise ValueError("experiment proposal ledger not advisory")
    if application.get("research_mode") != info["research_mode"]:
        raise ValueError("guard mode not reflected in research application")
    if application.get("input_draw_sha256") != info["draw_history_sha256"]:
        raise ValueError("application based on stale historical draw SHA")
    if (application.get("trusted_result_source") is not info["two_source_verified"]
            or application.get("proposal_count") != len(proposal_plan["proposals"])):
        raise ValueError("application queue disagrees with input evidence")

    pending = []
    if not info["two_source_verified"]:
        pending.append(task(
            "VERIFY_RESULT_SOURCES", "block", "source_integrity", "source_verifier",
            "抽せん結果の独立2ソース照合", "照合済みでない最新結果を採点や新規予測の凍結に利用できません。",
            "既存の結果検証workflowと独立した発表元を照合してください。単一ソースで成功扱いしません。",
            "round=" + str(latest) + ";verification=" + info["source_verification"],
        ))
    if clock >= quality_guard.next_result_deadline(latest_date, raw_source):
        pending.append(task(
            "CHECK_SOURCE_FRESHNESS", "watch", "source_integrity", "source_verifier",
            "最新の抽せんデータ更新を確認",
            "記録された最終抽せん日から " + str(gap) + " 日が経過しています。",
            "公式抽せん日程と検証済み結果を確認し、取得先HTTP 503等の通信障害は既存の再試行手順で調査してください。",
            "latest_recorded=" + str(latest) + "@" + latest_date.isoformat(),
        ))
    if info["research_mode"] != "SEARCH":
        pending.append(task(
            "HOLD_SAME_DATA_SEARCH", "info", "research_governance", "research_governor",
            "同一履歴の新規探索を停止",
            "研究ガードが " + info["research_mode"] + " のため、探索を再開しません。",
            "新しい検証済み結果を待つ間、データ品質監査・文献照合・未承認実験計画の準備だけを続けてください。",
            "guard=" + info["research_mode"] + ";trials=" +
            str(info["same_data_trials"]) + "/" + str(info["max_same_data_trials"]),
        ))
    else:
        pending.append(task(
            "AUDIT_ENABLED_RESEARCH_BUDGET", "watch", "research_governance", "research_governor",
            "探索許可と消費試行数を確認", "新規モデル試行には別の研究計画と予算承認が必要です。",
            "既存のresearch_cycle_guardを確認し、無条件自動探索を開始しないでください。",
            "budget=" + str(info["same_data_trials"]) + "/" + str(info["max_same_data_trials"]),
        ))
    if (info["candidate_future_draws"] == 0 or info["v2_future_draws"] == 0):
        pending.append(task(
            "AWAIT_GENUINE_OOS", "info", "prospective_integrity", "oos_custodian",
            "真正将来検証の標本数を確保",
            "第701回開始の登録済み検証で、精度改善と呼べるだけの実測がありません。",
            "既存の事前登録と凍結手順を守り、抽せん結果が出た後の遡及的な予測作成はしないでください。",
            "v2=" + str(info["v2_future_draws"]) +
            ";candidate=" + str(info["candidate_future_draws"]),
        ))

    verified_records = publications.get("verifications", [])
    counts = {}
    records = {}
    for item in verified_records:
        doi = item.get("doi")
        status = item.get("status")
        if not isinstance(doi, str) or not SAFE_DOI.fullmatch(doi) or doi in records:
            raise ValueError("malformed or duplicate verification in planner")
        if status not in gate.VALID_BIBLIO | {
            "single_provider_only", "conflict_do_not_use", "unavailable", "not_yet_checked"
        }:
            raise ValueError("unknown bibliography verdict")
        counts[status] = counts.get(status, 0) + 1
        records[doi] = item
    if publications.get("automatic_adoption") is not False:
        raise ValueError("unsafe bibliographic auto-adoption flag")
    not_checked = sorted(doi for doi, v in records.items()
                         if v["status"] == "not_yet_checked")
    if not_checked:
        pending.append(task(
            "VERIFY_UNCHECKED_DOIS", "watch", "bibliography", "literature_verifier",
            "未照合の学術文献を一次確認",
            str(len(not_checked)) + " 件の候補DOIがCrossref/OpenAlexによる照合待ちです。",
            "既存の上限付き照合を次の定期サイクルで続けてください。未照合論文を学術的根拠として扱わないでください。",
            "unchecked_count=" + str(len(not_checked)),
        ))
    conflicted = sorted(doi for doi, v in records.items()
                        if v["status"] == "conflict_do_not_use")
    if conflicted:
        pending.append(task(
            "REVIEW_BIBLIO_CONFLICTS", "watch", "bibliography", "literature_verifier",
            "文献書誌情報の不一致を確認",
            str(len(conflicted)) + " 件のDOIで独立サービスの書誌照合結果が不一致です。",
            "元のDOIと著者・タイトルを確認してください。対立するメタデータから研究計画を承認しないでください。",
            "conflict_count=" + str(len(conflicted)),
        ))
    if counts.get("single_provider_only", 0):
        pending.append(task(
            "RETRY_SINGLE_PROVIDER", "info", "bibliography", "literature_verifier",
            "片側の論文登録サービスを再確認",
            "片側のみ検証された論文が " + str(counts["single_provider_only"]) + " 件あります。",
            "既存workflowの接続復旧・上限付き再試行で確認してください。2ソース照合済みと偽りません。",
            "single_count=" + str(counts["single_provider_only"]),
        ))

    if quality is not None:
        if (quality.get("version") != quality_guard.VERSION
                or quality.get("draw_csv_sha256") != info["draw_history_sha256"]
                or quality.get("source_csv_modified") is not False
                or quality.get("source_attestation_modified") is not False
                or quality.get("production_or_oos_modified") is not False):
            raise ValueError("stale or unsafe data quality audit")
        issues = quality.get("issues")
        if (quality.get("status") not in {"pass", "watch", "block"}
                or not isinstance(issues, list)
                or any(not isinstance(x, dict)
                       or x.get("severity") not in {"block", "watch"}
                       or not isinstance(x.get("code"), str) for x in issues)):
            raise ValueError("invalid data quality evidence")
        level = "block" if any(x["severity"] == "block" for x in issues) else (
            "watch" if issues else "pass")
        if quality["status"] != level:
            raise ValueError("data quality severity mismatch")
        if issues:
            pending.append(task(
                "REVIEW_DATA_QUALITY", level, "source_integrity", "source_verifier",
                "データ品質の失敗原因を確認",
                str(len(issues)) + " 件のデータ品質問題があります。未検証結果は使用しません。",
                "既存の検証workflowと原本を調査してください。派生レポート以外は自動変更しません。",
                "quality_codes=" + ",".join(sorted({x["code"] for x in issues})),
            ))

    queue = application.get("application_queue", [])
    if not isinstance(queue, list) or len(queue) != proposal_plan.get("count"):
        raise ValueError("application methodological review queue is incomplete")
    for draft, item in zip(proposal_plan["proposals"], queue):
        if (draft.get("topic") != item.get("topic") or
                draft.get("proposal_id") != item.get("proposal_id") or
                item.get("experiment_execution_allowed") is not False or
                item.get("production_adoption_allowed") is not False or
                item.get("requires_human_approval") is not True):
            raise ValueError("untrusted action in research application queue")
        # One specific review action per methodology; stable ID and bounded N.
        if len(pending) >= 20:
            break
        next_step = item.get("next_step")
        if not isinstance(next_step, str) or not 1 <= len(next_step) <= 240:
            raise ValueError("malformed methodology review action")
        if item["status"] not in {
            "bibliography_needs_verification", "awaiting_full_text_and_methodology_review"
        }:
            raise ValueError("unsupported experiment review status")
        pending.append(task(
            "REVIEW_METHOD:" + str(draft["topic"]), "watch",
            "experiment_review", "methodology_reviewer",
            "研究計画レビュー：" + str(draft["topic"]),
            "候補論文は手法の有効性・公平な抽せんへの適合性を証明していません。",
            next_step + " 人の明示的な承認がない限り研究試行も本番採用も行いません。",
            "proposal_id=" + str(draft["proposal_id"]),
        ))
    # Severity is a hard barrier; counts and recurrence only sort within it.
    impact = {
        "VERIFY_RESULT_SOURCES": 95, "REVIEW_DATA_QUALITY": 90,
        "CHECK_SOURCE_FRESHNESS": 75, "REVIEW_BIBLIO_CONFLICTS": 65,
        "VERIFY_UNCHECKED_DOIS": 55, "RETRY_SINGLE_PROVIDER": 35,
        "AUDIT_ENABLED_RESEARCH_BUDGET": 25, "AWAIT_GENUINE_OOS": 15,
        "HOLD_SAME_DATA_SEARCH": 10,
    }
    old_tasks = {p["id"]: p for p in (previous or {}).get("tasks", [])
                 if isinstance(p, dict) and isinstance(p.get("id"), str)
                 and p.get("safe_autonomous_action") == "report_only"}
    for item in pending:
        count = measured_backlog(item)
        prior = old_tasks.get(item["id"])
        before = measured_backlog(prior)
        if prior is None:
            state = "new"
        elif count is None or before is None:
            state = "still_pending_unmeasured"
        elif count < before:
            state = "improving"
        elif count > before:
            state = "worsening"
        else:
            state = "unchanged"
        trend = {"improving": -5, "worsening": 5}.get(state, 0)
        cycles = prior.get("recurrence_cycles", 0) if prior is not None else 0
        cycles = cycles if type(cycles) is int and 0 <= cycles <= 20 else 0
        recurrence = min(20, cycles + 1) if previous is not None else 1
        item["recurrence_cycles"] = recurrence
        item["feedback_state"] = state
        item["backlog_observed"] = count
        item["backlog_prior"] = before
        item["backlog_delta"] = count - before if count is not None and before is not None else None
        item["priority_factors"] = {
            "impact": impact.get(item["code"], 20),
            "verified_backlog": min(10, count) if count is not None else 0,
            "unresolved_recurrence": min(10, recurrence - 1),
            "observed_trend": trend,
        }
        item["priority_score"] = sum(item["priority_factors"].values())
    pending.sort(key=lambda t: (SEVERITY[t["priority"]],
                                -t["priority_score"], t["code"]))
    if len({item["id"] for item in pending}) != len(pending):
        raise ValueError("duplicate plan item IDs")
    return pending


def run(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    clock = (now or datetime.now(JST)).astimezone(JST)
    info, plans, sandbox, _, papers = gate.verify_inputs(root)
    gate.check_synthetic_null(sandbox)
    source = discovery.read_json(out / discovery.FILES["source"])
    readiness_path = out / gate.STATUS_FILE
    review_path = out / literature.DESIGN_FILE
    publication_path = out / verification.EVIDENCE
    readiness = gate.load(readiness_path)
    publication = gate.load(publication_path)
    if (readiness.get("version") != gate.VERSION or
            readiness.get("reviewed_publication_count") != len(papers) or
            readiness.get("synthetic_control", {}).get("status") != "synthetic_controls_passed" or
            readiness.get("read_only_science") is not True):
        raise ValueError("research application readiness stale or failed safety audit")
    quality_path = out / quality_guard.JSON_REPORT
    quality = gate.load(quality_path) if quality_path.is_file() else None
    if quality is not None:
        fresh_quality = quality_guard.audit(root, now=clock)
        for key in ("version", "draw_csv_sha256", "source_sha256",
                    "latest_round", "rows_checked", "status", "issues",
                    "source_csv_modified", "source_attestation_modified",
                    "production_or_oos_modified"):
            if quality.get(key) != fresh_quality[key]:
                raise ValueError("stale or altered data quality evidence: " + key)
    previous = None
    queue_path = out / QUEUE
    if queue_path.is_file():
        try:
            candidate = gate.load(queue_path)
            if previous_queue_is_eligible(candidate, info=info, clock=clock):
                previous = candidate
        except (ValueError, TypeError, KeyError):
            # Untrusted derived evidence cannot affect priority calculations.
            pass
    tasks = build_queue(info, readiness, source, plans, publication, clock,
                        quality=quality, previous=previous)
    output = {
        "version": VERSION,
        "latest_audit_at_jst": clock.isoformat(timespec="seconds"),
        "latest_source_round": info["latest_round"],
        "source_two_verified": info["two_source_verified"],
        "research_mode": info["research_mode"],
        "draw_history_sha256": info["draw_history_sha256"],
        "input_evidence_sha256": {
            "application": digest(readiness_path.read_bytes()),
            "proposals": digest(review_path.read_bytes()),
            "bibliography": digest(publication_path.read_bytes()),
            "source": digest((out / discovery.FILES["source"]).read_bytes()),
        },
        "counts": {key: sum(t["priority"] == key for t in tasks)
                   for key in ("block", "watch", "info")},
        "top_priority": tasks[0]["code"] if tasks else None,
        "tasks": tasks,
        "action_feedback": summarize_feedback(tasks, previous),
        "authority": {
            "scope": "audited_advisory_queue_only",
            "automated_model_training": False,
            "research_budget_override": False,
            "retroactive_future_freeze": False,
            "registered_oos_modification": False,
            "production_or_champion_update": False,
            "workflows_dispatched": False,
        },
        "evaluation_limit": "No improvement in lottery forecast accuracy has been established.",
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / QUEUE).write_text(json.dumps(output, indent=2, ensure_ascii=False,
                                       allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# Autonomous Research Priority Queue", "",
        "- Generated: " + output["latest_audit_at_jst"],
        "- Guard: **" + info["research_mode"] + "**; verified draw source: **" +
        str(info["two_source_verified"]) + "**",
        "- Priorities: " + ", ".join(key + "=" + str(count)
                                   for key, count in output["counts"].items()),
        "- Read-only; does not launch workflows, change Production or create future grades.",
        "- Observed backlog changes are NOT causal evidence of agent effectiveness.",
        "- Feedback: " + ", ".join(k + "=" + str(v) for k, v in
                                 output["action_feedback"]["status_counts"].items()),
        "",
    ]
    for n, item in enumerate(tasks[:16], start=1):
        lines.extend([
            str(n) + ". **[" + item["priority"] + "] " + item["title"] + "**",
            "   - Assigned: " + item["owner"] + " / " + item["lane"],
            "   - Observed: " + item["feedback_state"] +
            "; backlog=" + str(item["backlog_observed"]) +
            "; delta=" + str(item["backlog_delta"]),
            "   - Reason: " + item["reason"],
            "   - Next: " + item["next_step"],
        ])
    lines.extend(["", "No longer in current queue (not proof of action success): " +
                  ", ".join(output["action_feedback"]["no_longer_in_queue"]),
                  "", "Historical research alone is not evidence of lottery prediction ability."])
    (out / REPORT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe priority ordering for existing research agents")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.repo_root)
    print(json.dumps({"top_priority": result["top_priority"],
                      "counts": result["counts"],
                      "mode": result["research_mode"],
                      "actions_dispatched": result["authority"]["workflows_dispatched"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
