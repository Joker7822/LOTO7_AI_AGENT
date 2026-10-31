#!/usr/bin/env python3
"""Read-only lottery bias audit + append-only prospective FIRST-prize comparison.

Research-only. Never generates a Production ticket or promotes an AI model.
New frozen matched controls start at round 702; prior rounds cannot be backfilled.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from production_disjoint35_policy import MIN_TARGET_ROUND, VERSION as TICKET_POLICY, validate_issued_rows

VERSION = "first-prize-prospective-v1"
TRUST = "verified_two_result_sources"
JST = timezone(timedelta(hours=9))
ROOT = Path("research/first_prize_oos")
DENOMINATOR = math.comb(37, 7)
PROSPECTIVE_FIRST_PRIZE_PROB = 5 / DENOMINATOR


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_object(value: object) -> str:
    return sha_bytes(canonical(value))


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"not a JSON object: {path}")
    return value


def rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def round_no(raw: object) -> int:
    token = str(raw).removeprefix("第").removesuffix("回")
    if not token.isdecimal() or int(token) < 1:
        raise ValueError("invalid draw round")
    return int(token)


def numbers(raw: object, size: int) -> list[int]:
    if not isinstance(raw, str):
        raise ValueError("lottery number string missing")
    parts = raw.split()
    if len(parts) != size or any(not part.isdecimal() for part in parts):
        raise ValueError("wrong number count")
    result = [int(part) for part in parts]
    if result != sorted(set(result)) or any(not 1 <= number <= 37 for number in result):
        raise ValueError("invalid, repeated or unsorted lottery numbers")
    return result


def historical_rows(csv_path: Path) -> list[dict]:
    history = rows(csv_path)
    if not history:
        raise ValueError("missing lottery history")
    for i, record in enumerate(history, 1):
        if round_no(record["回別"]) != i:
            raise ValueError("lottery history must be a sequential source prefix")
        main, bonus = numbers(record["本数字"], 7), numbers(record["ボーナス数字"], 2)
        if set(main) & set(bonus):
            raise ValueError("main and bonus balls overlap")
        date.fromisoformat(record["抽せん日"])
    return history


def checked_source(csv_path: Path, source_path: Path) -> tuple[list[dict], dict, str]:
    history = historical_rows(csv_path)
    source = load_json(source_path)
    digest = sha_bytes(csv_path.read_bytes())
    latest = source.get("latest") or {}
    provenance = source.get("verification_provenance") or {}
    last = history[-1]
    if not (
        source.get("status") == "ok" and source.get("verification") == TRUST
        and provenance.get("draw_csv_sha256") == digest
        and latest.get("round") == round_no(last["回別"])
        and latest.get("date") == last["抽せん日"]
        and latest.get("main") == numbers(last["本数字"], 7)
        and latest.get("bonus") == numbers(last["ボーナス数字"], 2)
    ):
        raise ValueError("not an independently verified and hash-matched draw prefix")
    return history, source, digest


def probability_audit(csv_path: Path, source_path: Path, simulations: int = 2048) -> dict:
    """Global max-deviation randomization test under independent fair 7-of-37 draws.

    This controls 37-label multiplicity within ONE snapshot only. Repeat
    weekly inspection is exploratory, NOT a sequentially valid discovery.
    """
    if not 128 <= simulations <= 20000:
        raise ValueError("simulations must be in [128, 20000]")
    history, source, csv_sha = checked_source(csv_path, source_path)
    n = len(history)
    counts = [0] * 37
    for record in history:
        for number in numbers(record["本数字"], 7):
            counts[number - 1] += 1
    p = 7 / 37
    expected = n * p
    sigma = math.sqrt(n * p * (1 - p))
    observed = max(abs(count - expected) / sigma for count in counts)

    # Fixed public seed, independent of observed balls, and +1 calibration.
    rng = random.Random(0xF157A2026)
    exceeded = 0
    for _ in range(simulations):
        simulated = [0] * 37
        for _draw in range(n):
            for ball in rng.sample(range(37), 7):
                simulated[ball] += 1
        if max(abs(count - expected) / sigma for count in simulated) >= observed - 1e-12:
            exceeded += 1
    ranked = sorted(
        ({"number": number + 1, "observed": count, "expected": round(expected, 4),
          "standardized_deviation": round((count - expected) / sigma, 5)}
         for number, count in enumerate(counts)),
        key=lambda item: (-abs(item["standardized_deviation"]), item["number"]),
    )
    return {
        "version": VERSION,
        "analysis": "exploratory_37_ball_global_max_deviation_per_snapshot",
        "source_latest_round": round_no(history[-1]["回別"]),
        "source_csv_sha256": csv_sha,
        "trusted_source": TRUST,
        "draw_count": n,
        "null_probability_per_number_per_draw": p,
        "observed_max_abs_z": round(observed, 6),
        "monte_carlo_replicates": simulations,
        "max_37_familywise_p_estimate": (exceeded + 1) / (simulations + 1),
        "most_deviating_numbers": ranked[:5],
        "all_number_counts": {str(i + 1): count for i, count in enumerate(counts)},
        "valid_for_single_snapshot_only": True,
        "repeat_inspection_not_time_adjusted": True,
        "not_evidence_of_predictive_advantage": True,
        "production_changed": False,
        "source_verification_checked_at_jst": source.get("checked_at_jst"),
    }


def freeze_file(root: Path, target: int) -> Path:
    return root / f"freeze_{target:04d}.json"


def grade_file(root: Path, target: int) -> Path:
    return root / f"grade_{target:04d}.json"


def ticket_rows(out: Path, target: int) -> list[dict]:
    correction_file = out / "prediction_corrections.csv"
    invalid = {row["prediction_id"] for row in rows(correction_file)
               if row.get("action") == "invalidate" and row.get("prediction_id")}
    active = [row for row in rows(out / "predictions.csv")
              if round_no(row["target_round"]) == target
              and row["prediction_id"] not in invalid]
    if target >= MIN_TARGET_ROUND:
        validate_issued_rows(active, target)
    return sorted(active, key=lambda row: int(row["ticket"]))


def ticket_identity(issued: list[dict]) -> list[dict]:
    return [{field: row[field] for field in (
        "prediction_id", "prediction_created_at_jst", "base_round",
        "target_round", "target_draw_date_estimate", "ticket",
        "predicted_numbers", "model_version", "data_sha256")}
        for row in issued]


def baseline_tickets(target: int, data_sha: str) -> list[list[int]]:
    """A fair matched 35-number control; no actual draw or later data input."""
    seed = int(sha_bytes(f"{VERSION}|control|{target}|{data_sha}".encode()), 16)
    chosen = random.Random(seed).sample(range(1, 38), 35)
    return [sorted(chosen[7 * i:7 * (i + 1)]) for i in range(5)]


def validate_archive(root: Path, out: Path) -> dict[int, dict]:
    """Recompute stored hashes and confirm the issued ledger still matches.

    Never edit existing records. Missing files / tampering fail closed.
    """
    found: dict[int, dict] = {}
    if not root.exists():
        return found
    for path in sorted(root.glob("*.json")):
        if not (path.name.startswith("freeze_") or path.name.startswith("grade_")):
            raise ValueError("unexpected prospective archive JSON")
        entry = load_json(path)
        target = entry.get("target_round")
        if type(target) is not int or target < MIN_TARGET_ROUND:
            raise ValueError("invalid prospective target")
        if path.name.startswith("freeze_"):
            if path != freeze_file(root, target) or target in found:
                raise ValueError("unexpected/duplicate freeze file")
            if entry.get("version") != VERSION or entry.get("policy") != TICKET_POLICY:
                raise ValueError("changed prospective protocol")
            if (entry.get("base_round") != target - 1 or
                    entry.get("target_draw_date") is None or
                    entry.get("first_prize_probability_per_portfolio_under_fair_draw")
                    != PROSPECTIVE_FIRST_PRIZE_PROB or
                    entry.get("control_selected_before_outcome") is not True or
                    entry.get("research_only_no_production_or_promotion") is not True):
                raise ValueError("altered prospective freeze metadata or baseline")
            published = datetime.fromisoformat(entry["published_at_jst"])
            if published.tzinfo is None:
                raise ValueError("pre-draw freeze publication timestamp has no timezone")
            frozen_now(published, entry["target_draw_date"])
            issued = ticket_rows(out, target)
            identity = ticket_identity(issued)
            if entry.get("prediction_rows_sha256") != sha_object(identity):
                raise ValueError("issued prediction ledger changed since pre-draw freeze")
            if (entry.get("prediction_ids") != [row["prediction_id"] for row in issued]
                    or entry.get("target_draw_date") != issued[0]["target_draw_date_estimate"]
                    or entry.get("production_model") != issued[0]["model_version"]
                    or entry.get("base_csv_sha256") != issued[0]["data_sha256"]):
                raise ValueError("altered prospective freeze or source provenance")
            if entry.get("production_tickets") != [numbers(row["predicted_numbers"], 7) for row in issued]:
                raise ValueError("changed issued Production numbers")
            if entry.get("random_control_tickets") != baseline_tickets(target, entry["base_csv_sha256"]):
                raise ValueError("changed deterministic control tickets")
            validate_issued_rows(issued, target)
            found[target] = entry
        else:
            if path != grade_file(root, target):
                raise ValueError("misnamed grading record")
    for path in sorted(root.glob("grade_*.json")):
        record = load_json(path)
        target = record["target_round"]
        if target not in found or record.get("version") != VERSION:
            raise ValueError("grading a never-frozen target")
        if record.get("freeze_sha256") != sha_object(found[target]):
            raise ValueError("grading references a modified freeze")
        if (record.get("source_verification") != TRUST
                or record.get("draw_date") != found[target]["target_draw_date"]
                or record.get("research_only_no_production_or_promotion") is not True):
            raise ValueError("changed graded source evidence or research role")
        numbers(" ".join(map(str, record.get("actual_main", []))), 7)
        for key, source in (("production", "production_tickets"), ("random_control", "random_control_tickets")):
            record_hits = record.get(key + "_main_hits")
            if record_hits != [len(set(ticket) & set(record.get("actual_main", [])))
                              for ticket in found[target][source]]:
                raise ValueError("tampered prospective score")
            if record.get(key + "_first_prize_count") != sum(h == 7 for h in record_hits):
                raise ValueError("tampered prospective first-prize grade")
    return found


def frozen_now(now: datetime, draw_date: str) -> None:
    local = now.astimezone(JST)
    cutoff = datetime.combine(date.fromisoformat(draw_date), time(18, 0), JST)
    if local >= cutoff:
        raise ValueError("cannot retrospectively freeze at/after 18:00 JST on draw day")


def freeze(csv_path: Path, source_path: Path, out: Path, root: Path,
           *, now: datetime | None = None) -> dict:
    now = now or datetime.now(JST)
    state = load_json(out / "weekly_production_prediction_state.json")
    target = round_no(state.get("target_round"))
    if target < MIN_TARGET_ROUND:
        return {"status": "historical_no_backfill", "target_round": target}
    existing = validate_archive(root, out)
    if target in existing:
        return {"status": "already_prefrozen", "target_round": target}
    if state.get("reason") != "frozen_to_canonical_prediction_ledger":
        raise ValueError("cannot prefreeze republished or non-original prediction")
    if state.get("published") is not True or state.get("ticket_policy") != TICKET_POLICY:
        raise ValueError("canonical Production not yet published under disjoint35")
    issued = ticket_rows(out, target)
    if len({row["prediction_created_at_jst"] for row in issued}) != 1:
        raise ValueError("issued tickets have inconsistent creation timestamps")
    identity = ticket_identity(issued)
    if len({row["target_draw_date_estimate"] for row in issued}) != 1:
        raise ValueError("issued tickets have mismatched draw dates")
    draw_date = issued[0]["target_draw_date_estimate"]
    if not draw_date:
        raise ValueError("missing next draw date")
    frozen_now(now, draw_date)
    history, source, base_sha = checked_source(csv_path, source_path)
    if (target != round_no(history[-1]["回別"]) + 1
            or base_sha != state.get("data_sha256")):
        raise ValueError("cannot freeze against post-outcome or stale source")
    if any(row["data_sha256"] != base_sha or row["model_version"] != state.get("model_version")
           for row in issued):
        raise ValueError("issued ledger does not match source and model state")
    last_date = date.fromisoformat(history[-1]["抽せん日"])
    if date.fromisoformat(draw_date) != last_date + timedelta(days=7):
        raise ValueError("target draw date does not follow official source prefix")

    published = datetime.fromisoformat(state["published_at_jst"])
    made = datetime.fromisoformat(issued[0]["prediction_created_at_jst"])
    if (published.tzinfo is None or made.tzinfo is None or published > now
            or made > published + timedelta(minutes=1)):
        raise ValueError("invalid pre-draw publication clock")
    frozen_now(published, draw_date)
    frozen_now(made, draw_date)

    record = {
        "version": VERSION, "policy": TICKET_POLICY,
        "target_round": target, "target_draw_date": draw_date,
        "base_round": target - 1, "base_csv_sha256": base_sha,
        "verified_source_report_sha256": sha_bytes(source_path.read_bytes()),
        "source_verified": TRUST, "published_at_jst": state["published_at_jst"],
        "prediction_created_at_jst": issued[0]["prediction_created_at_jst"],
        "prediction_rows_sha256": sha_object(identity),
        "prediction_ids": [row["prediction_id"] for row in issued],
        "production_model": state["model_version"],
        "production_tickets": [numbers(row["predicted_numbers"], 7) for row in issued],
        "random_control_tickets": baseline_tickets(target, base_sha),
        "first_prize_probability_per_portfolio_under_fair_draw": PROSPECTIVE_FIRST_PRIZE_PROB,
        "control_selected_before_outcome": True,
        "research_only_no_production_or_promotion": True,
    }
    # Strict CREATE only: cannot replace a historical freeze even if content differs.
    root.mkdir(parents=True, exist_ok=True)
    path = freeze_file(root, target)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    return {"status": "prefrozen", "target_round": target,
            "control_tickets": 5, "distinct_control_numbers": 35}


def grade(csv_path: Path, source_path: Path, out: Path, root: Path) -> dict:
    found = validate_archive(root, out)
    if not found:
        return {"status": "no_prospective_freezes"}
    history, source, csv_sha = checked_source(csv_path, source_path)
    latest = round_no(history[-1]["回別"])
    pending = [target for target in sorted(found)
               if not grade_file(root, target).exists()]
    if not pending:
        return {"status": "all_frozen_targets_graded", "graded_count": len(found)}
    # Never backfill an old draw, but also never let ONE missed historical
    # verification window block new valid future OOS comparisons forever.
    missed = [target for target in pending if target < latest]
    if latest in pending:
        target = latest
    else:
        upcoming = [target for target in pending if target > latest]
        if upcoming:
            return {"status": "awaiting_verified_result",
                    "target_round": upcoming[0], "missed_past_targets": missed}
        return {"status": "missed_verification_window_no_backfill",
                "missed_past_targets": missed}
    freeze_obj = found[target]
    if history[-1]["抽せん日"] != freeze_obj["target_draw_date"]:
        raise ValueError("result draw date disagrees with prospective freeze")
    actual = numbers(history[-1]["本数字"], 7)
    scored = {}
    for label, field in (("production", "production_tickets"), ("random_control", "random_control_tickets")):
        hits = [len(set(ticket) & set(actual)) for ticket in freeze_obj[field]]
        scored[f"{label}_main_hits"] = hits
        scored[f"{label}_first_prize_count"] = sum(hit == 7 for hit in hits)
        scored[f"{label}_max_main_hits"] = max(hits)
    record = {
        "version": VERSION, "target_round": target, "actual_main": actual,
        "draw_date": history[-1]["抽せん日"], "freeze_sha256": sha_object(freeze_obj),
        "graded_csv_sha256": csv_sha, "source_validation_sha256": sha_bytes(source_path.read_bytes()),
        "source_verification": TRUST, **scored,
        "research_only_no_production_or_promotion": True,
    }
    path = grade_file(root, target)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    return {"status": "new_verified_grade", "target_round": target,
            "missed_past_targets": missed,
            "production_first_prizes": scored["production_first_prize_count"],
            "random_control_first_prizes": scored["random_control_first_prize_count"]}


def summary(root: Path, out: Path) -> dict:
    found = validate_archive(root, out)
    grades = [load_json(grade_file(root, target)) for target in found
              if grade_file(root, target).is_file()]
    return {
        "version": VERSION, "frozen_targets": len(found), "graded_targets": len(grades),
        "first_target": min(found) if found else None,
        "production_first_prize_count": sum(x["production_first_prize_count"] for x in grades),
        "random_control_first_prize_count": sum(x["random_control_first_prize_count"] for x in grades),
        "fair_first_prize_probability_per_five_unique_tickets": PROSPECTIVE_FIRST_PRIZE_PROB,
        "proof_of_predictive_advantage": False,
        "production_changed": False,
        "promotion_authorized": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("freeze", "grade", "verify", "analyze"), required=True)
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--source", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--out", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--simulations", type=int, default=2048)
    ap.add_argument("--json-output", type=Path)
    args = ap.parse_args()
    if args.mode == "freeze":
        result = freeze(args.csv, args.source, args.out, args.root)
    elif args.mode == "grade":
        result = grade(args.csv, args.source, args.out, args.root)
    elif args.mode == "verify":
        result = summary(args.root, args.out)
    else:
        result = probability_audit(args.csv, args.source, args.simulations)
    content = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
    if args.json_output:
        args.json_output.write_text(content + "\n", encoding="utf-8")
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
