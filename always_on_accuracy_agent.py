#!/usr/bin/env python3
"""Hourly bounded research activity, including live scholarly discovery.

Read-only audit + one rotating focus each hour. Searches Crossref public
bibliographic metadata once per six cycles. All papers are UNTRUSTED leads,
never instructions or evidence of predictive edge. No model or Production writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

VERSION = "always-on-accuracy-research-v1"
JST = timezone(timedelta(hours=9))
GENESIS = "GENESIS"
PHASES = (
    ("source_audit", "結果の二重ソース照合と鮮度を点検"),
    ("future_protocol", "事前凍結と真正将来採点の連続性を監査"),
    ("generalization", "過去モデル比較・多重比較を点検"),
    ("calibration", "未来の校正と逐次e値を点検"),
    ("literature_search", "インターネットから最新の研究論文を検索"),
    ("budget_and_plan", "試行予算を守り次の検証を計画"),
)
TOPICS = (
    "online probabilistic forecasting calibration",
    "prequential prediction test then train",
    "betting martingales e values sequential testing",
    "time series conformal prediction drift",
    "multiple comparisons backtest overfitting",
    "ensemble probabilistic forecast verification",
)
FILES = {
    "source": "source_validation.json",
    "budget": "research_cycle_guard.json",
    "portfolio": "future_holdout_state.json",
    "v2": "joint_set_v2_signal_oos_state.json",
    "adaptive": "continuous_learning_agent_state.json",
    "candidate": "accuracy_extension_agent_state.json",
    "science": "advanced_validation_lab_summary.json",
}
LEDGER = "always_on_accuracy_research_journal.jsonl"
STATE = "always_on_accuracy_research_state.json"
REPORT = "always_on_accuracy_research_report.md"
TRUST = "verified_two_result_sources"
TITLE_HINTS = ("forecast", "calibrat", "conformal", "predict", "prequential",
               "martingale", "sequential", "test", "ensemble", "probabil",
               "bayes", "time series", "multiple", "drift", "online", "uncertainty")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def read_json(path: Path) -> dict:
    if not path.exists():
        raise ValueError("required independent evidence missing: " + path.name)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("evidence must be JSON object: " + path.name)
    return doc


def valid_count(doc: dict, key: str) -> int:
    n = doc.get(key)
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("future count invalid: " + key)
    return n


def inspect_evidence(root: Path) -> dict:
    out = root / "loto7_agent_output"
    csv = root / "loto7.csv"
    if not csv.is_file():
        raise ValueError("missing trusted historical draw history")
    csv_hash = sha256(csv.read_bytes())
    items = {name: read_json(out / filename) for name, filename in FILES.items()}
    source = items["source"]
    round_no = source.get("latest", {}).get("round")
    if isinstance(round_no, bool) or not isinstance(round_no, int) or round_no <= 0:
        raise ValueError("latest draw number missing")
    source_trusted = source.get("status") == "ok" and source.get("verification") == TRUST
    budget = items["budget"]
    if budget.get("data_sha256") != csv_hash:
        raise ValueError("research guard belongs to a different draw-history SHA")
    mode = budget.get("mode")
    if mode not in ("SEARCH", "VALIDATION_ONLY", "WAIT_FOR_NEW_DATA"):
        raise ValueError("unknown guarded research mode")
    if (mode == "SEARCH") != (budget.get("search_enabled") is True):
        raise ValueError("research mode and budget permission disagree")
    trials = valid_count(budget, "signal_trials_this_data")
    cap = valid_count(budget, "max_signal_trials_per_data")
    if cap <= 0 or trials > cap:
        raise ValueError("same-data research budget invalid or exceeded")

    portfolio = items["portfolio"]
    n = valid_count(portfolio, "trusted_draws")
    if valid_count(portfolio, "horizon_trusted_draws") != 26 or n > 26 or len(portfolio.get("graded_rounds", [])) != n:
        raise ValueError("registered 26-draw portfolio state inconsistent")
    v2 = items["v2"]
    adaptive = items["adaptive"]
    candidate = items["candidate"]
    for label, d in (("v2", v2), ("adaptive", adaptive), ("candidate", candidate)):
        count = valid_count(d, "trusted_draws")
        if d.get("graded_rounds") != list(range(701, 701 + count)):
            raise ValueError("registered prospective prefix inconsistent: " + label)
        if count and round_no < 700 + count:
            raise ValueError("future outcome is ahead of known history: " + label)
    if valid_count(v2, "horizon_trusted_draws") != 26:
        raise ValueError("v2 fixed horizon protocol mismatch")
    if candidate.get("promotion_role") != "diagnostic_only":
        raise ValueError("research shadow lost no-promotion authority")
    science = items["science"]
    f = science.get("future_e_monitor", {})
    if science.get("version") != "advanced-validation-lab-v1" or science.get("historical_data_sha256") != csv_hash:
        raise ValueError("advanced validation evidence is not for current history")
    if (science.get("automatic_model_selection") is not False or f.get("future_only") is not True
            or valid_count(f, "verified_prefrozen_draws") != candidate["trusted_draws"]
            or f.get("ville_threshold") != 20.0 or f.get("predeclared_alpha") != 0.05
            or not isinstance(f.get("series"), list) or len(f["series"]) != candidate["trusted_draws"]):
        raise ValueError("advanced research inference protocol changed")
    value = f.get("current_e_value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError("invalid actual future e-process")
    if candidate["trusted_draws"] == 0 and value != 1:
        raise ValueError("unseen futures cannot produce evidence")
    return {
        "draw_history_sha256": csv_hash, "latest_round": round_no,
        "two_source_verified": source_trusted,
        "source_verification": str(source.get("verification", "unknown"))[:80],
        "research_mode": mode, "search_enabled": budget["search_enabled"],
        "same_data_trials": trials, "max_same_data_trials": cap,
        "portfolio_future_draws": n, "v2_future_draws": v2["trusted_draws"],
        "adaptive_future_draws": adaptive["trusted_draws"],
        "candidate_future_draws": candidate["trusted_draws"],
        "future_e_value": float(value),
    }


def read_chain(path: Path) -> list[dict]:
    if not path.exists():
        return []
    chain = []
    prev = GENESIS
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            raise ValueError("blank audit-ledger line")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("audit-ledger row not an object")
        record_hash = row.get("record_sha256")
        values = {k: v for k, v in row.items() if k != "record_sha256"}
        if (row.get("previous_record_sha256") != prev or
                row.get("sequence") != len(chain) + 1 or
                sha256(canonical(values).encode()) != record_hash):
            raise ValueError("tampered, truncated, or reordered research audit ledger")
        chain.append(row)
        prev = record_hash
    return chain


def fetch_crossref(topic: str, since: str, timeout: int = 10) -> list[dict]:
    """Fetch only Crossref-owned public metadata; never download executable code."""
    if topic not in TOPICS:
        raise ValueError("unregistered literature search query")
    if not re.fullmatch(r"\d{4}-\d\d-\d\d", since):
        raise ValueError("invalid publication bound")
    qs = urllib.parse.urlencode({
        "query.bibliographic": topic,
        "filter": f"from-pub-date:{since}",
        "rows": "8",
        "select": "DOI,title,published,type",
    })
    url = "https://api.crossref.org/works?" + qs
    request = urllib.request.Request(
        url, headers={"User-Agent": "LOTO7-Research-Discovery/1.0 (+https://github.com/Joker7822/LOTO7_AI_AGENT)",
                      "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise ValueError("Crossref HTTP status not successful")
        body = response.read(700_001)
    if len(body) > 700_000:
        raise ValueError("Crossref response size exceeded research cap")
    payload = json.loads(body)
    works = payload.get("message", {}).get("items", [])
    if not isinstance(works, list):
        raise ValueError("Crossref items malformed")
    output = []
    for item in works:
        doi = str(item.get("DOI", "")).strip().lower()
        name = item.get("title", [])
        title = " ".join(str(x) for x in name[:1]).strip() if isinstance(name, list) else ""
        if not re.fullmatch(r"10\.\d{4,9}/[^\s<>\"']{1,130}", doi) or not title or len(title) > 220:
            continue
        if not any(word in title.lower() for word in TITLE_HINTS):
            continue
        date_parts = item.get("published", {}).get("date-parts", [])
        date = date_parts[0] if date_parts and isinstance(date_parts[0], list) else []
        year = date[0] if date and isinstance(date[0], int) else None
        if year is None or year < int(since[:4]) or year > datetime.now(JST).year:
            continue
        output.append({
            "doi": doi, "title": title[:200], "year": year,
            "url": "https://doi.org/" + urllib.parse.quote(doi, safe="/.-_;():"),
            "source": "Crossref bibliographic metadata", "review_status": "unreviewed",
        })
        if len(output) >= 4:
            break
    return output


def next_focus(seq: int, info: dict, latest_papers: list[dict], discovery_status: str) -> tuple[str, str, list[str]]:
    phase, description = PHASES[seq % len(PHASES)]
    notes = []
    if not info["two_source_verified"]:
        notes.append("独立2ソース未照合。未信頼結果で将来予測を採点しない。")
    if info["research_mode"] != "SEARCH":
        notes.append("探索予算ガードが" + info["research_mode"] + "。既存データの無制限再探索は禁止。")
    if info["v2_future_draws"] == 0 or info["candidate_future_draws"] == 0:
        notes.append("真正Future-OOSの実測がまだ不足。改善を断定しない。")
    if phase == "literature_search":
        notes.append("オンライン論文の検索結果は未査読・未検証の研究候補であり、コードを自動採用しない。")
        notes.append("オンライン検索: " + discovery_status + " / 新規候補 " + str(len(latest_papers)) + "件")
    elif phase == "budget_and_plan":
        notes.append("同一履歴の新規試行予算 " + str(info["same_data_trials"]) + "/" + str(info["max_same_data_trials"]))
    elif phase == "calibration":
        notes.append("検証済み未来データに限るe値: " + format(info["future_e_value"], ".6g"))
    elif phase == "source_audit":
        notes.append("最新信頼ステータス: " + info["source_verification"])
    elif phase == "future_protocol":
        notes.append("26回固定holdout " + str(info["portfolio_future_draws"]) + "/26、新規v2 " + str(info["v2_future_draws"]) + "回")
    else:
        notes.append("過去の4/5モデル比較は探索済み。独立した未来結果なしに選別・昇格しない。")
    return phase, description, notes


def run(root: Path, *, now: datetime | None = None,
        fetcher: Callable[[str, str], list[dict]] = fetch_crossref) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    now = (now or datetime.now(JST)).astimezone(JST)
    info = inspect_evidence(root)
    chain = read_chain(out / LEDGER)
    state = read_json(out / STATE) if (out / STATE).exists() else {}
    if (bool(state) != bool(chain) or
            (state and (state.get("sequence") != len(chain) or
                        state.get("last_record_sha256") != chain[-1]["record_sha256"]))):
        raise ValueError("activity index disagrees with append-only audit chain")
    sequence = len(chain) + 1
    discovered = list(state.get("papers", []))
    new_papers = []
    fetch_status = "not_scheduled"
    if PHASES[(sequence - 1) % len(PHASES)][0] == "literature_search":
        topic = TOPICS[((sequence - 1) // len(PHASES)) % len(TOPICS)]
        since = f"{max(2020, now.year - 2)}-01-01"
        try:
            fresh = fetcher(topic, since)
            if not isinstance(fresh, list) or len(fresh) > 4:
                raise ValueError("online metadata validation failed")
            old_dois = {paper["doi"] for paper in discovered}
            for paper in fresh:
                doi, title, year, url = (paper.get(k) for k in ("doi", "title", "year", "url"))
                if (not isinstance(doi, str) or not re.fullmatch(r"10\.\d{4,9}/[^\s<>\"']{1,130}", doi)
                        or not isinstance(title, str) or not title or len(title) > 200
                        or not isinstance(year, int) or year < 2020
                        or url != "https://doi.org/" + urllib.parse.quote(doi, safe="/.-_;():")
                        or paper.get("review_status") != "unreviewed"):
                    raise ValueError("invalid/untrusted online metadata candidate")
                if doi not in old_dois:
                    new_papers.append({"doi": doi, "title": title, "year": year, "url": url, "review_status": "unreviewed"})
                    old_dois.add(doi)
            discovered = (new_papers + discovered)[:36]
            fetch_status = "searched" if fresh else "no_relevant_metadata"
        except (urllib.error.URLError, TimeoutError, ValueError, OSError, KeyError) as exc:
            fetch_status = "unavailable:" + type(exc).__name__
    phase, task, notes = next_focus(sequence - 1, info, new_papers, fetch_status)
    event = {
        "version": VERSION, "sequence": sequence,
        "at_jst": now.isoformat(timespec="seconds"),
        "phase": phase, "activity": task,
        "evidence_sha256": info["draw_history_sha256"],
        "two_source_verified": info["two_source_verified"],
        "research_mode": info["research_mode"],
        "network_status": fetch_status, "new_papers": new_papers,
        "review_notes": notes, "read_only": True,
        "automatic_model_selection": False,
        "source_data_modified": False,
        "previous_record_sha256": chain[-1]["record_sha256"] if chain else GENESIS,
    }
    event["record_sha256"] = sha256(canonical(event).encode())
    # Only three owned files are writable; do not touch model/forecasts/data.
    out.mkdir(parents=True, exist_ok=True)
    with (out / LEDGER).open("a", encoding="utf-8") as file:
        file.write(canonical(event) + "\n")
    new_state = {
        "version": VERSION, "sequence": sequence,
        "last_record_sha256": event["record_sha256"],
        "last_activity_jst": event["at_jst"],
        "current_phase": phase, "current_activity": task,
        "status": "online_unavailable" if fetch_status.startswith("unavailable:") else "active_bounded_research",
        "research_mode": info["research_mode"],
        "latest_resolved_round": info["latest_round"],
        "two_source_verified": info["two_source_verified"],
        "same_data_trials": info["same_data_trials"],
        "max_same_data_trials": info["max_same_data_trials"],
        "future_verified_counts": {
            "holdout": info["portfolio_future_draws"],
            "v2": info["v2_future_draws"], "adaptive": info["adaptive_future_draws"],
            "fifth_expert": info["candidate_future_draws"],
        },
        "online_search_status": fetch_status,
        "papers": discovered, "new_papers_count": len(new_papers),
        "review_notes": notes, "promotion_authorized": False,
        "read_only_scientific_activity": True,
    }
    (out / STATE).write_text(json.dumps(new_state, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# Always-on Accuracy Research — bounded hourly activities", "",
        f"- Last executed: **{new_state['last_activity_jst']}**",
        f"- Completed audit cycles: **{sequence}**",
        f"- This cycle: **{phase}** / {task}",
        f"- Network discovery: **{fetch_status}**",
        f"- Trusted draw latest: **{info['latest_round']}**, two-source: **{info['two_source_verified']}**",
        f"- Research guard: **{info['research_mode']}**, same-data trials: **{info['same_data_trials']}/{info['max_same_data_trials']}**",
        f"- Future actuals: portfolio {info['portfolio_future_draws']}/26, v2 {info['v2_future_draws']}, fifth-expert {info['candidate_future_draws']}",
        "", "## Completed evidence review",
        *("- " + text for text in notes), "",
        "## Online research leads (unreviewed; do NOT deploy as algorithms)",
    ]
    for item in discovered[:12]:
        lines.append(f"- [{item['title'].replace(']', '')}]({item['url']}) ({item['year']}) — UNREVIEWED")
    lines.extend([
        "", "Every scheduled cycle has a bounded evidence-check activity.",
        "Network errors are visible. An unattended hourly job is not guaranteed to",
        "run at an exact time. More compute or papers do NOT guarantee a lottery edge.",
        "No optimizer, draw data, Production, Champion or preregistered OOS is changed.",
    ])
    (out / REPORT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return new_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded autonomous scientific research cycle")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.repo_root)
    print(json.dumps({k: result[k] for k in ("sequence", "current_phase", "status", "online_search_status", "new_papers_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
