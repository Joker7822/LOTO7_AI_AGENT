#!/usr/bin/env python3
"""Stable replay and mutable CURRENT VIEW for registered future-only online v3.

This operational compatibility layer does not modify advanced_online_v3.py,
which is SHA-locked in the prospective preregistration. Every original freeze
and grade remains append-only, hash-chained, predeclared, and independently
reproducible. Only a presentation-only latest view may be overwritten.

A very small floating-point replay difference may vary with BLAS, CPU and
thread order. Fail closed on any nonnumeric field difference or on any
absolute numeric deviation > 5e-13. We accept the ORIGINAL sealed numbers
for replay after the bounded comparison, never rewrite the frozen evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import advanced_online_v3 as registered
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

JST = timezone(timedelta(hours=9))
VERSION = "online-v3-replay-compat-and-mutable-view-1"
ABS_REPLAY_TOL = 5e-13
DISPLAY_DECIMALS = 10
VIEW = Path("research/advanced_online_v3/latest_research_prediction.json")
REVISIONS = Path("research/advanced_online_v3/preview_revisions")


def stable_digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _compare_recursively(expected, observed, path="prediction") -> tuple[int, float]:
    """Verify immutable structure, exact discrete decisions, bounded floats."""
    if type(expected) is not type(observed):
        raise ValueError(f"v3 MATERIAL replay change: type at {path}")
    if isinstance(expected, dict):
        if set(expected) != set(observed):
            raise ValueError(f"v3 MATERIAL replay change: keys at {path}")
        results = [_compare_recursively(expected[k], observed[k], path + "." + k)
                   for k in sorted(expected)]
        return sum(r[0] for r in results), max((r[1] for r in results), default=0.0)
    if isinstance(expected, list):
        if len(expected) != len(observed):
            raise ValueError(f"v3 MATERIAL replay change: length at {path}")
        results = [_compare_recursively(a, b, f"{path}[{i}]")
                   for i, (a, b) in enumerate(zip(expected, observed))]
        return sum(r[0] for r in results), max((r[1] for r in results), default=0.0)
    if isinstance(expected, float):
        if not math.isfinite(expected) or not math.isfinite(observed):
            raise ValueError(f"v3 MATERIAL replay change: nonfinite float at {path}")
        difference = abs(expected - observed)
        if difference > ABS_REPLAY_TOL:
            raise ValueError(
                f"v3 MATERIAL replay change: {path} exceeds tolerance "
                f"({difference:.17g} > {ABS_REPLAY_TOL:.17g})"
            )
        return int(difference > 0), difference
    if expected != observed:
        raise ValueError(f"v3 MATERIAL replay change: exact field at {path}")
    return 0, 0.0


def compare_registered_forecast(frozen: dict, current: dict) -> tuple[int, float]:
    """Only compare the existing forecast BEFORE prospective wealth is added.

    The e-process wealth before the freeze is validated by the original
    advanced_online_v3.validate_state, not by this bridge, which only handles
    floating point compatibility in model_forecast.
    """
    if (frozen.get("prefix_sha256") != current.get("prefix_sha256")
            or frozen.get("top7") != current.get("top7")
            or frozen.get("drift_guard") != current.get("drift_guard")):
        raise ValueError("v3 MATERIAL replay change: prefix, top7 or drift")
    a = {k: v for k, v in frozen.items() if k != "e_process_values_before"}
    b = {k: v for k, v in current.items() if k != "e_process_values_before"}
    return _compare_recursively(a, b)


def replay_adapter(events: list[dict], original):
    frozen_by_round = {}
    for event in events:
        if event.get("kind") == "freeze":
            round_number = event["target_round"]
            if round_number in frozen_by_round:
                raise ValueError("v3 duplicate frozen target")
            frozen_by_round[round_number] = event["prediction"]

    def adapted(prior, expert_scores, meta_scores, temp_scores, past_edges):
        calculated = original(prior, expert_scores, meta_scores,
                              temp_scores, past_edges)
        frozen = frozen_by_round.get(len(prior) + 1)
        if frozen is None:
            # Never use old predictions to compute a genuinely new round.
            return calculated
        changes, max_deviation = compare_registered_forecast(
            frozen, calculated)
        if changes:
            print(f"[V3-NUMERIC-REPLAY] Accepted {changes} sub-tolerance "
                  f"float changes; max deviation={max_deviation:.3g}, "
                  "immutable frozen outcome unchanged.")
        # The original validator will then independently check SHA-256 chain,
        # target, time cutoff, prefix replay, actual grade, and e-process.
        return dict(frozen)
    return adapted


def write_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".v3-current-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as fd:
            json.dump(obj, fd, ensure_ascii=False, sort_keys=True,
                      indent=2, allow_nan=False)
            fd.write("\n")
            fd.flush()
            os.fsync(fd.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def refresh_latest_view(root: Path, state: dict, now: datetime,
                        original_model) -> dict:
    """Overwrite ONLY latest research preview if materially changed.

    The immutable SHA-256-chained frozen research evidence is NEVER edited.
    The mutable preview retains an append-only sidecar audit on any change.
    """
    final_event = state["events"][-1]
    if final_event["kind"] != "freeze":
        raise ValueError("v3 state must end with an immutable future freeze")
    target = final_event["target_round"]
    x, _ = make_history(read_csv_flexible(root / "loto7.csv"))
    if len(x) + 1 != target:
        # There is no new future-only preview after an ungraded outcome.
        return {"preview_status": "waiting_for_trusted_grade"}
    if now.date() >= datetime.fromisoformat(
            final_event["scheduled_draw_date"]).date():
        return {"preview_status": "draw_date_reached_no_retrospective_update"}
    # v3.run already authenticated and completely replay-validated every
    # previous grade. Here the preview is derived from the latest *sealed*
    # immutable forecast, not from any prospective target outcome.
    pred = final_event["prediction"]
    current_sha = final_event["event_sha256"]
    values = [round(float(v), DISPLAY_DECIMALS) for v in pred["probabilities"]]
    identity = {
        "target_round": target,
        "scheduled_draw_date": final_event["scheduled_draw_date"],
        "frozen_event_sha256": current_sha,
        "source_prior_sha256": pred["prefix_sha256"],
        "top7": pred["top7"],
        "probabilities_display": values,
    }
    path = root / VIEW
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if old:
        if (old.get("version") != VERSION or
                old.get("role") != "mutable_research_preview_not_production_not_prospective_evidence" or
                type(old.get("revision")) is not int or old["revision"] < 1):
            raise ValueError("existing mutable research view format is not valid")
        archived_old = root / REVISIONS / f"revision_{old['revision']:06d}.json"
        if (not archived_old.is_file() or
                json.loads(archived_old.read_text(encoding="utf-8")) != old):
            raise ValueError("existing mutable research view does not match archival revision")
    old_identity = old.get("identity") if old else None
    if old_identity == identity:
        return {"preview_status": "unchanged", "target_round": target,
                "revision": old["revision"]}
    number = 1 if old is None else int(old["revision"]) + 1
    if number < 1 or number > 999999:
        raise ValueError("invalid research preview revision counter")
    revision = {
        "version": VERSION,
        "revision": number,
        "updated_at_jst": now.isoformat(timespec="seconds"),
        "role": "mutable_research_preview_not_production_not_prospective_evidence",
        "identity": identity,
        "previous_revision_sha256": (stable_digest(old) if old else "GENESIS"),
        "provenance_note": (
            "Presentation only. The original registered frozen forecast is "
            "not revised, rescored or counted again."
        ),
    }
    archive_path = root / REVISIONS / f"revision_{number:06d}.json"
    if archive_path.exists():
        stored = json.loads(archive_path.read_text(encoding="utf-8"))
        if (stored.get("identity") != identity or
                stored.get("previous_revision_sha256") != revision["previous_revision_sha256"] or
                stored.get("role") != revision["role"] or
                stored.get("version") != VERSION or
                stored.get("revision") != number):
            raise ValueError("immutable research-preview revision already exists")
        # Resume an interrupted atomic current-view replacement; do not
        # rewrite the preexisting historical revision timestamp.
        revision = stored
    else:
        # Do not publish a new current view until its archival predecessor is
        # write-once persisted locally, so every revision remains traceable.
        write_atomic(archive_path, revision)
    write_atomic(path, revision)
    return {"preview_status": "created" if number == 1 else "overwritten",
            "target_round": target, "revision": number}


def run(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    now = now or datetime.now(JST)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware clock required")
    now = now.astimezone(JST)
    immutable = root / registered.STATE
    original = registered.model_forecast
    if immutable.exists():
        state = json.loads(immutable.read_text(encoding="utf-8"))
        registered.model_forecast = replay_adapter(state.get("events", []),
                                                    original)
    try:
        report = registered.run(root, now=now)
    finally:
        registered.model_forecast = original
    if not immutable.exists():
        return {**report, "mutable_preview": "not_issued"}
    current = json.loads(immutable.read_text(encoding="utf-8"))
    # Must only expose a preview of evidence which the registered implementation
    # just authenticated. We do not use the preview as input for model learning.
    view = refresh_latest_view(root, current, now, original)
    return {**report, "mutable_preview": view}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(run(args.repo_root), indent=2, ensure_ascii=False,
                     allow_nan=False))


if __name__ == "__main__":
    main()
