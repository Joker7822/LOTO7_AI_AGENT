#!/usr/bin/env python3
"""Read-only LOTO7 agent operating council: evidence-driven next-action plans.

This coordinator combines the *already validated* browser telemetry snapshot,
not the untrusted prediction ticket data. It does not execute any actions,
trigger workflow reruns, grade results, freeze vectors or promote models.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

VERSION = "agent-operations-command-center-v1"
START_V2_ROUND = 701
LEVEL = {"block": 0, "watch": 1, "info": 2}
WORKFLOW_PLAYBOOKS = {
    "continuous_loto7_v4.yml": ("研究復旧エージェント", "研究CIの直近ログを確認し、修正後の実行を別途検証してください。"),
    "continuous_learning_agent.yml": ("継続学習エージェント", "継続学習の事前凍結・採点状態を照合してください。"),
    "agent_role_council.yml": ("監査エージェント", "監査結果と入力データの整合性を確認してください。"),
    "joint_set_v2_signal_oos.yml": ("将来検証エージェント", "SHA固定されたv2台帳を確認し、未凍結予測の事後復元は行わないでください。"),
    "weekly_production_publisher.yml": ("本番運用エージェント", "公開期限と既存のProduction運用手順を人が確認してください。事後発行は禁止です。"),
    "friday_result_check_watchdog.yml": ("抽せん確認エージェント", "抽せん結果を独立した2ソースで再確認してください。未確認結果で採点しないでください。"),
    "browser_dashboard_ci.yml": ("表示品質エージェント", "表示画面のテストと監視レポートの形式を確認してください。"),
}
ROLE_MAP = {
    "data_steward": "データ管理エージェント",
    "prospective_signal_custodian": "将来検証エージェント",
    "oos_risk_officer": "統計・リスクエージェント",
    "research_skeptic": "研究評価エージェント",
    "release_operations": "本番運用エージェント",
}
WATCH_CODES = {
    "NO_EARLY_PORTFOLIO_CLAIM": "5口の26回将来検証はまだ途中です。精度改善を確定扱いしないでください。",
    "RESEARCH_TRIAL_LIMIT_APPROACHING": "同じ抽せん履歴での探索予算が上限に近づいています。",
    "SOURCE_REFRESH_OVERDUE": "2ソース照合の更新が予定より遅れています。",
    "RESULT_NOT_TWO_SOURCE_VERIFIED": "最新の抽せん結果の2ソース照合が完了していません。",
    "PAIR_CONTEXT_INT8_OVERFLOW": "旧pair_context計算で整数オーバーフローが検出されました。モデルの別バージョンで修正・検証が必要です。",
    "FREEZE_701_NOW": "第700回の検証済み結果で第701回の予測を抽せん前に凍結してください。",
}


def _item(priority: str, code: str, owner: str, title: str, detail: str,
          action: str, evidence: str = "", link: str | None = None) -> dict:
    if priority not in LEVEL:
        raise ValueError("unsupported task priority")
    fingerprint = f"{code}|{evidence}"
    stable_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return {
        "id": stable_id, "priority": priority, "code": code,
        "owner": owner, "title": title, "detail": detail[:300],
        "evidence": evidence[:150], "recommended_action": action,
        "requires_existing_workflow_or_human_review": True,
        "autonomous_mutation_allowed": False,
        "url": link,
    }


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
        return number if number >= 0 else None
    except (TypeError, ValueError):
        return None


def _workflow_url(ref: object) -> str | None:
    if not isinstance(ref, str):
        return None
    prefix = "https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/"
    suffix = ref.removeprefix(prefix)
    return ref if ref.startswith(prefix) and suffix.isdecimal() else None


def build_plan(snapshot: Mapping[str, Any], now: datetime | None = None) -> dict:
    if snapshot.get("version") != "loto7-ops-snapshot-v1":
        raise ValueError("requires validated browser snapshot v1")
    sources = snapshot.get("sources")
    series = snapshot.get("series")
    workflows = snapshot.get("workflows")
    if not isinstance(sources, dict) or not isinstance(series, dict) or not isinstance(workflows, list):
        raise ValueError("missing input integrity fields")
    if len(workflows) != len(WORKFLOW_PLAYBOOKS):
        raise ValueError("workflow count mismatch")
    if [x.get("file") for x in workflows] != list(WORKFLOW_PLAYBOOKS):
        raise ValueError("workflow list/order mismatch")
    if not all(isinstance(series.get(k), list) for k in ("portfolio", "v2", "adaptive")):
        raise ValueError("future series missing")
    for kind, status_key in (("portfolio", "holdout"), ("v2", "signal"), ("adaptive", "learning")):
        n = _int(sources.get(status_key, {}).get("trusted_draws"))
        if n is None or n != len(series[kind]):
            raise ValueError(f"{kind} future OOS state mismatch; do not plan on inconsistent results")
    council = sources.get("council") or {}
    if council.get("overall") not in {"ok", "watch", "block"}:
        raise ValueError("agent council state missing or invalid")
    latest = _int(sources.get("source", {}).get("latest", {}).get("round"))
    if latest is None:
        raise ValueError("latest source round missing")

    tasks = []
    for w in workflows:
        filename = w["file"]
        owner, playbook = WORKFLOW_PLAYBOOKS[filename]
        health = w.get("health")
        label = str(w.get("label", filename))[:60]
        if health not in ("ok", "running", "warning", "block", "unknown"):
            raise ValueError("unknown workflow health")
        link = _workflow_url(w.get("url"))
        if health == "block":
            tasks.append(_item(
                "block", f"WORKFLOW_FAILED:{filename}", owner,
                f"{label}：最新実行が失敗", "直近の実行が失敗しています。過去の修正だけで復旧済みとは判定しません。",
                playbook, str(w.get("run_id") or ""), link,
            ))
        elif health == "unknown":
            tasks.append(_item(
                "watch", f"WORKFLOW_UNVERIFIED:{filename}", owner,
                f"{label}：稼働状況が不明", "GitHub Actionsの状態を取得できていません。",
                "GitHub Actionsの実行一覧を確認してください。状態不明のまま成功と判断しません。",
                filename, link,
            ))
        elif health == "warning":
            tasks.append(_item(
                "watch", f"WORKFLOW_WARNING:{filename}", owner,
                f"{label}：スキップ・キャンセルなどを確認", "最新の実行が正常終了として記録されていません。",
                playbook, str(w.get("run_id") or ""), link,
            ))

    source = sources["source"]
    verified = source.get("status") == "ok" and source.get("verification") == "verified_two_result_sources"
    if not verified:
        tasks.append(_item(
            "block", "UNTRUSTED_SOURCE", "データ管理エージェント",
            "最新抽せんの2ソース検証待ち", "未確認の結果で採点や次回予測の凍結を進めないでください。",
            "既存の検証workflowの結果を確認してください。", str(latest),
        ))

    # Human-readable research governance handoffs are advisory and never
    # allowed to change the locked experiment or Champion.
    seen = set()
    for h in council.get("handoff_tasks", []):
        code = str(h.get("issue_code", ""))[:80]
        owner = ROLE_MAP.get(h.get("owner"), "役割監査エージェント")
        if not code or code in seen:
            continue
        seen.add(code)
        priority = "block" if h.get("priority") == "block" else "watch"
        # An uncompleted 26-draw holdout is expected, NOT a broken system.
        # Keep the council's factual governance WATCH untouched, but show
        # routine waiting as INFO only when source 700 is corroborated and
        # both prospectively registered target-701 freezes already exist.
        # Never claim 26/26 before it is actually reached.
        if code == "NO_EARLY_PORTFOLIO_CLAIM":
            n = _int(sources.get("holdout", {}).get("trusted_draws"))
            hmax = _int(sources.get("holdout", {}).get("horizon_trusted_draws"))
            signal_target = _int(sources.get("signal", {}).get("current_target_round"))
            learning_target = _int(sources.get("learning", {}).get("current_prefrozen_target"))
            if (verified and latest >= 700 and n is not None
                    and hmax == 26 and n < hmax
                    and signal_target is not None and signal_target > latest
                    and learning_target is not None and learning_target > latest):
                priority = "info"
        tasks.append(_item(
            priority, f"COUNCIL:{code}", owner,
            WATCH_CODES.get(code, "監査で要確認事項を検出しました。"),
            "監査の判定と元の公表記録を照合してください。",
            "既存の監査レポートを確認し、権限を持つ既存workflowまたは人が対処してください。",
            code,
            "https://github.com/Joker7822/LOTO7_AI_AGENT/blob/main/loto7_agent_output/agent_role_council_report.md",
        ))

    # Future predictions can only start after the eligible trusted prefix.
    if latest < 700:
        for key, title in (("signal", "v2信号"), ("learning", "継続学習")):
            if _int(sources.get(key, {}).get("trusted_draws")) == 0:
                tasks.append(_item(
                    "info", f"WAIT_REGISTERED_PREFIX:{key}", "将来検証エージェント",
                    f"{title}：第700回の確認待ち", "第701回を事後的に凍結してはいけません。",
                    "検証済みの第700回が到着するまで既存の固定手順で待機してください。",
                    "699→700→701",
                ))
    elif verified:
        for key, label, target_key in (
            ("signal", "v2信号", "current_target_round"),
            ("learning", "継続学習", "current_prefrozen_target"),
        ):
            rec = sources.get(key) or {}
            frozen = _int(rec.get(target_key))
            if latest == 700 and frozen is None:
                tasks.append(_item(
                    "watch", f"FIRST_FREEZE_REQUIRED:{key}", "将来検証エージェント",
                    f"{label}：第701回を事前凍結する段階",
                    "検証済みの第700回が利用可能です。第701回の結果より先に凍結してください。",
                    "既存の登録済み将来検証workflowを確認してください。研究コードを変更しないでください。",
                    "700/701",
                ))
            if latest >= 701 and (frozen is None or frozen < latest):
                tasks.append(_item(
                    "block", f"MISSING_PREFREEZE:{key}", "将来検証エージェント",
                    f"{label}：事前凍結の連続性を確認できません",
                    "既に抽せん済みの回を後出しで凍結してはいけません。",
                    "元の固定台帳を監査し、事後復元や遡及採点を行わず停止してください。",
                    str(latest),
                ))

    # Only warn on negative forward proper score after enough *real* new
    # targets to avoid suggesting an ordinary 1–2-draw fluctuation is drift.
    if len(series["adaptive"]) >= 12:
        latest_adaptive = series["adaptive"][-1]
        edge = latest_adaptive.get("mean_log_edge")
        if isinstance(edge, (float, int)) and edge < 0:
            tasks.append(_item(
                "watch", "ADAPTIVE_PROSPECTIVE_SCORE_BELOW_UNIFORM", "研究評価エージェント",
                "継続学習の将来log-scoreが一様基準を下回っています",
                "事前凍結された未来の結果のみで計測。途中経過でのモデル選定は禁止です。",
                "研究レポートを確認してください。再チューニングやProduction昇格には別の事前登録が必要です。",
                f"{len(series['adaptive'])} draws",
            ))

    # The 26-draw fixed comparator's incompleteness is *informational* and
    # is already represented by a council WATCH if appropriate.
    n = len(series["portfolio"])
    checkpoints = {
        "portfolio": {"trusted_draws": n, "fixed_horizon": _int(sources["holdout"].get("horizon_trusted_draws")) or 26},
        "v2_signal": {"trusted_draws": len(series["v2"]), "fixed_horizon": 26},
        "adaptive": {"trusted_draws": len(series["adaptive"]), "descriptive_open_ended": True},
    }
    tasks.sort(key=lambda t: (LEVEL[t["priority"]], t["code"]))
    if len({t["id"] for t in tasks}) != len(tasks):
        raise ValueError("incident ids must remain unique across separate causes")
    blockers = sum(t["priority"] == "block" for t in tasks)
    watchers = sum(t["priority"] == "watch" for t in tasks)
    return {
        "version": VERSION,
        "source_commit": snapshot.get("source_commit"),
        "snapshot_generated_at_jst": snapshot.get("generated_at_jst"),
        "computed_at_jst": (now or datetime.now(timezone.utc)).astimezone(
            timezone.utc).isoformat(timespec="seconds"),
        "overall": "block" if blockers else "watch" if watchers else "ok",
        "counts": {"block": blockers, "watch": watchers, "info": len(tasks) - blockers - watchers},
        "checkpoints": checkpoints,
        "tasks": tasks,
        "authority": {
            "model_promotions": False,
            "forecast_overwrites": False,
            "retroactive_freezes": False,
            "workflow_retries": False,
            "production_publication": False,
            "scope": "deterministic_read_only_operational_plan",
        },
        "claim": "Operational suggestions only. Lottery prediction skill has not been established.",
    }
