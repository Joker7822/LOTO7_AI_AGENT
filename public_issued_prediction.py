#!/usr/bin/env python3
"""Public *already-issued* Production prediction preview for GitHub Pages.

Read-only projection from the canonical append-only Production ledger.
Never publishes research tickets, unissued entries, correction-invalidated
tickets or an unverified draw as a graded result.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from loto7_evolving_agent import fingerprint_file
import production_ticket_geometry35 as geometry35

JST = timezone(timedelta(hours=9))
TRUST = "verified_two_result_sources"
VERSION = "issued-production-forecast-public-v1"


def parse_round(value: Any) -> int | None:
    if not isinstance(value, str) or not value.startswith("第") or not value.endswith("回"):
        return None
    token = value[1:-1]
    return int(token) if token.isdecimal() and 1 <= int(token) <= 100000 else None


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError("issued prediction ledger missing: " + path.name)
    with path.open(encoding="utf-8-sig", newline="") as file:
        records = list(csv.DictReader(file))
    if not records:
        raise ValueError("issued prediction ledger empty: " + path.name)
    return records


def checked_numbers(raw: Any, size: int) -> list[int]:
    if not isinstance(raw, str):
        raise ValueError("invalid lottery number format")
    tokens = raw.strip().split()
    if len(tokens) != size or any(not s.isdecimal() or not 1 <= int(s) <= 37 for s in tokens):
        raise ValueError("invalid draw/forecast numbers")
    nums = [int(s) for s in tokens]
    if nums != sorted(set(nums)):
        raise ValueError("duplicate or unsorted forecast numbers")
    return nums


def draw_clock(text: str) -> datetime:
    return datetime.fromisoformat(text + "T20:00:00+09:00")


def forecast_group(rows: list[dict], target: int, *, required: bool = False) -> list[dict]:
    found = [r for r in rows if parse_round(r.get("target_round")) == target]
    if not found:
        if required:
            raise ValueError("issued Production ticket ledger has no active target rows")
        return []
    if len(found) != 5:
        raise ValueError("issued Production ticket count is not five")
    try:
        found.sort(key=lambda x: int(x.get("ticket", "")))
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid ticket position") from exc
    if [int(x["ticket"]) for x in found] != [1, 2, 3, 4, 5]:
        raise ValueError("five Production ticket positions incomplete")
    if len({r.get("prediction_id") for r in found}) != 5:
        raise ValueError("duplicate Production ledger event identity")
    for row in found:
        base = parse_round(row.get("base_round"))
        if base != target - 1:
            raise ValueError("forecast not tied to previous source round")
        made = datetime.fromisoformat(row["prediction_created_at_jst"])
        if made.tzinfo is None:
            raise ValueError("Production timestamp lacks timezone")
        try:
            deadline = draw_clock(row["target_draw_date_estimate"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Production draw date missing") from exc
        if made >= deadline:
            raise ValueError("Production forecast was not recorded before draw")
        checked_numbers(row.get("predicted_numbers"), 7)
    if target >= geometry35.MIN_TARGET_ROUND:
        geometry35.validate_issued_rows(found, target)
    return found


def trusted_draws(out: Path) -> dict[int, dict]:
    path = out / "actual_results.csv"
    if not path.is_file():
        return {}
    actual: dict[int, dict] = {}
    for row in read_csv(path):
        if row.get("source_status") != "ok" or row.get("source_verification") != TRUST:
            continue
        rnd = parse_round(row.get("round"))
        if rnd is None or rnd in actual:
            raise ValueError("trusted official draw duplicated or malformed")
        date = str(row.get("draw_date", ""))
        try:
            draw_clock(date)
            main = checked_numbers(row.get("main_numbers"), 7)
            bonus = checked_numbers(row.get("bonus_numbers"), 2)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid trusted official result") from exc
        if set(main) & set(bonus):
            raise ValueError("draw main and bonus overlap")
        actual[rnd] = {"round": rnd, "date": date, "main": main, "bonus": bonus}
    return actual


def grade(tickets: list[dict], actual: dict) -> list[dict]:
    output = []
    main, bonus = set(actual["main"]), set(actual["bonus"])
    for r in tickets:
        nums = checked_numbers(r["predicted_numbers"], 7)
        mh, bh = len(set(nums) & main), len(set(nums) & bonus)
        prize = ("1等" if mh == 7 else "2等" if mh == 6 and bh >= 1
                 else "3等" if mh == 6 else "4等" if mh == 5
                 else "5等" if mh == 4 else "6等" if mh == 3 and bh >= 1
                 else "はずれ")
        output.append({"ticket": int(r["ticket"]), "main_hits": mh,
                       "bonus_hits": bh, "grade": prize})
    return output


def preview(root: Path, source: dict, published: dict) -> tuple[dict, dict[str, str]]:
    """Never read candidate_tickets, shadow registries or unconstrained JSON."""
    out = root / "loto7_agent_output"
    state = {"version": VERSION, "status": "not_published", "tickets": [],
             "result_status": "not_available", "latest_verified": None}
    if published.get("published") is not True:
        return state, {}
    target = parse_round(published.get("target_round"))
    if target is None or not isinstance(published.get("published_at_jst"), str):
        raise ValueError("published Production state lacks valid target/time")
    published_at = datetime.fromisoformat(published["published_at_jst"])
    if published_at.tzinfo is None:
        raise ValueError("issued Production publication has no timezone")
    source_round = source.get("latest", {}).get("round")
    if not isinstance(source_round, int) or isinstance(source_round, bool):
        raise ValueError("cannot establish latest public draw prefix")
    # A previously issued target may remain the latest publication after
    # its draw is verified, until the next Production publication occurs.
    if target > source_round + 1:
        raise ValueError("published target is ahead of known source prefix")
    corrections = read_csv(out / "prediction_corrections.csv")
    invalidated = {
        r["prediction_id"] for r in corrections
        if r.get("action") == "invalidate" and r.get("prediction_id")
    }
    active = [r for r in read_csv(out / "predictions.csv")
              if r.get("prediction_id") not in invalidated]
    tickets = forecast_group(active, target, required=True)
    if (target >= geometry35.MIN_TARGET_ROUND
            and published.get("ticket_policy") != geometry35.VERSION):
        raise ValueError("published disjoint35 Production state has wrong ticket policy")
    if any(r["model_version"] != published.get("model_version") for r in tickets):
        raise ValueError("model version mismatch in issued prediction ledger")
    if len({r["prediction_created_at_jst"] for r in tickets}) != 1:
        raise ValueError("issued five tickets have inconsistent creation timestamps")
    made = datetime.fromisoformat(tickets[0]["prediction_created_at_jst"])
    if made > published_at + timedelta(minutes=1):
        raise ValueError("forecast generated after its publication")
    if any(r["data_sha256"] != published["data_sha256"] for r in tickets):
        raise ValueError("Production rows belong to another source snapshot")
    if any(parse_round(r["base_round"]) != target - 1 for r in tickets):
        raise ValueError("Production ticket not based on preceding source draw")
    if target == source_round + 1 and published["data_sha256"] != fingerprint_file(root / "loto7.csv"):
        raise ValueError("issued future ticket source hash does not match current historical data")

    draws = trusted_draws(out)
    latest_previous = draws.get(target - 1)
    historical = None
    if latest_previous:
        prev_tickets = forecast_group(active, target - 1)
        if prev_tickets:
            historical = {
                "round": target - 1, "date": latest_previous["date"],
                "main": latest_previous["main"],
                "bonus": latest_previous["bonus"],
                "tickets": grade(prev_tickets, latest_previous),
                "source_verification": TRUST,
            }
    # The current target must not be assumed graded just because its scheduled
    # date has passed; actuals are accepted ONLY from an independently verified
    # result event. Cross-check result and source report when they refer to it.
    actual = draws.get(target)
    trusted = source.get("status") == "ok" and source.get("verification") == TRUST
    if actual and source_round == target:
        if not trusted:
            # Trust remains degraded until the currently observed result is
            # independently corroborated; no false win grade.
            actual = None
        elif actual["main"] != source["latest"].get("main") or actual["bonus"] != source["latest"].get("bonus"):
            raise ValueError("official verified result disagrees with current source")
    if source_round >= target and actual is None:
        result_status = "awaiting_independently_verified_draw"
    elif actual:
        result_status = "independently_verified"
    else:
        result_status = "awaiting_independently_verified_draw"
    return {
        "version": VERSION,
        "status": "published",
        "target_round": target,
        "draw_date": tickets[0]["target_draw_date_estimate"],
        "published_at_jst": published["published_at_jst"],
        "model": published.get("model_version"),
        "source_base_round": target - 1,
        "tickets": [
            {"ticket": int(r["ticket"]), "numbers": checked_numbers(r["predicted_numbers"], 7)}
            for r in tickets
        ],
        "result_status": result_status,
        "current_result": {"round": target, "date": actual["date"],
                           "main": actual["main"], "bonus": actual["bonus"],
                           "tickets": grade(tickets, actual)} if actual else None,
        "latest_verified": historical,
        "exposure": "publicly_issued_production_only",
        "no_future_oos_vectors": True,
        "accuracy_claim": False,
    }, {
        "prediction_ledger": _hash_file(out / "predictions.csv"),
        "prediction_corrections": _hash_file(out / "prediction_corrections.csv"),
        "production_actuals": _hash_file(out / "actual_results.csv")
    }


def _hash_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()
