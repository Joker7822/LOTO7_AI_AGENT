#!/usr/bin/env python3
"""Open-ended evolutionary model-program search, independent of Production.

Research generations, mutations and repeated historical search have NO fixed
lifetime ceiling. Infrastructure runs are time-sliced and resume from a signed
checkpoint. This does not confer real-world lottery forecasting skill.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path

import numpy as np

from loto7_evolving_agent import N_NUMBERS, PICKS, fingerprint_file, make_history, read_csv_flexible
from loto7_v4_runner import parse_round
from joint_set_v2_signal_oos_guard import validate_trusted_source

VERSION = "open-ended-evolution-v1"
STATE = "open_ended_evolution_state.json"
LEDGER = "open_ended_evolution_journal.jsonl"
REPORT = "open_ended_evolution_report.md"
PROGRAM = "open_ended_evolution_candidate.py"
GENESIS = "GENESIS"
EXPECTED = PICKS / N_NUMBERS
MIN_TRAIN = 100
BACKTEST = 48
FEATURES = ("uniform", "frequency", "decay", "gap", "pair")
COMPOSITES = ("blend", "power")


def encoded(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def journal(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records, previous = [], GENESIS
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            raise ValueError("blank evolutionary audit record")
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError("invalid evolutionary audit object")
        plain = {k: v for k, v in record.items()
                 if k not in ("record_sha256", "snapshot")}
        snapshot = record.get("snapshot")
        if (not isinstance(snapshot, dict)
                or record.get("snapshot_sha256") != sha(encoded({
                    k: v for k, v in snapshot.items() if k != "last_record_sha256"
                }).encode("utf-8"))
                or snapshot.get("last_record_sha256") != record.get("record_sha256")
                or record.get("sequence") != len(records) + 1
                or record.get("previous_record_sha256") != previous
                or record.get("record_sha256") != sha(encoded(plain).encode("utf-8"))):
            raise ValueError("evolutionary audit hash chain corrupted")
        records.append(record)
        previous = record["record_sha256"]
    return records


def history(root: Path) -> tuple[np.ndarray, dict]:
    path = root / "loto7.csv"
    matrix, cleaned = make_history(read_csv_flexible(path))
    if len(matrix) < MIN_TRAIN + BACKTEST + 1:
        raise ValueError("insufficient historical rounds for open-ended research")
    if parse_round(cleaned["回別"].iloc[-1]) != len(matrix):
        raise ValueError("CSV round index does not match chronological rows")
    verification = "not_available"
    source_file = root / "loto7_agent_output/source_validation.json"
    independently_verified = False
    if source_file.exists():
        source = json.loads(source_file.read_text(encoding="utf-8"))
        verification = str(source.get("verification", "unknown"))
        latest = source.get("latest")
        if not isinstance(latest, dict) or latest.get("round") != len(matrix):
            raise ValueError("source snapshot and CSV disagree on latest round")
        expected_date = cleaned["抽せん日"].iloc[-1].date().isoformat()
        expected_main = sorted(int(i) + 1 for i in np.flatnonzero(matrix[-1]))
        expected_bonus = sorted(int(x) for x in str(cleaned["ボーナス数字"].iloc[-1]).split())
        if (latest.get("date") != expected_date
                or latest.get("main") != expected_main
                or latest.get("bonus") != expected_bonus):
            raise ValueError("source snapshot and CSV disagree on latest numbers/date")
        if verification == "verified_two_result_sources":
            if source.get("status") != "ok":
                raise ValueError("claimed independent source verification has a non-ok status")
            # A string flag alone is not evidence of an independent source.
            verified = validate_trusted_source(path, source_file)
            if not verified.get("trusted") or not verified.get("secondary"):
                raise ValueError("independent source evidence could not be validated")
            independently_verified = True
        elif source.get("status") == "ok":
            raise ValueError("source claims ok status without independent verification")
    # Historical exploratory model search may proceed using the known prefix;
    # unverified outcomes are excluded from *all* candidate evaluation.
    exclusion = not independently_verified
    training = matrix[:-1] if exclusion else matrix
    return training, {
        "data_sha256": fingerprint_file(path), "recorded_rounds": len(matrix),
        "evaluation_rounds": len(training), "latest_verification": verification,
        "last_unverified_row_excluded": exclusion,
        "independent_source_verified": independently_verified,
    }


def leaf(op: str, rng: np.random.Generator) -> dict:
    if op == "frequency":
        return {"op": op, "window": int(rng.integers(12, 260)),
                "prior": round(float(np.exp(rng.uniform(np.log(5), np.log(600)))), 5)}
    if op == "decay":
        return {"op": op, "half_life": round(float(rng.uniform(3, 200)), 5)}
    if op == "gap":
        return {"op": op, "scale": round(float(rng.uniform(2, 70)), 5)}
    if op == "pair":
        return {"op": op, "window": int(rng.integers(30, 300)),
                "prior": round(float(rng.uniform(5, 300)), 5)}
    return {"op": "uniform"}


def random_program(rng: np.random.Generator, depth: int = 0) -> dict:
    if depth >= 4 or rng.random() < 0.42:
        return leaf(str(rng.choice(FEATURES)), rng)
    if rng.random() < 0.7:
        return {
            "op": "blend", "alpha": round(float(rng.uniform(0.02, 0.98)), 5),
            "left": random_program(rng, depth + 1),
            "right": random_program(rng, depth + 1),
        }
    return {
        "op": "power", "exponent": round(float(rng.uniform(0.3, 2.5)), 5),
        "child": random_program(rng, depth + 1),
    }


def mutate(program: dict, rng: np.random.Generator) -> dict:
    """Mutate structure, parameters, subtrees or crossover; no finite catalog."""
    op = program["op"]
    choice = int(rng.integers(0, 5))
    if choice == 0:
        return random_program(rng)
    if choice == 1:
        return {"op": "blend", "alpha": round(float(rng.uniform(.1, .9)), 5),
                "left": copy.deepcopy(program), "right": random_program(rng, 2)}
    if choice == 2 and op in COMPOSITES:
        return copy.deepcopy(program["left" if op == "blend" and rng.random() < .5
                                    else "right" if op == "blend" else "child"])
    if choice == 3 and op == "blend":
        new = copy.deepcopy(program)
        new["alpha"] = round(float(np.clip(new["alpha"] + rng.normal(0, .16), .01, .99)), 5)
        new["left" if rng.random() < .5 else "right"] = random_program(rng, 2)
        return new
    if choice == 4 and op == "power":
        new = copy.deepcopy(program)
        new["exponent"] = round(float(np.clip(new["exponent"] + rng.normal(0, .3), .25, 3.0)), 5)
        return new
    return leaf(op, rng) if op in FEATURES else random_program(rng)


def scores(prefix: np.ndarray, program: dict, depth: int = 0) -> np.ndarray:
    """Interpret a typed mathematical program, never execute generated text."""
    if depth > 9:
        raise ValueError("evolved program depth exceeded")
    if prefix.ndim != 2 or prefix.shape[1] != N_NUMBERS or len(prefix) < MIN_TRAIN:
        raise ValueError("invalid prior draw matrix")
    op = program.get("op")
    if op == "uniform":
        raw = np.ones(N_NUMBERS)
    elif op == "frequency":
        n = min(int(program["window"]), len(prefix))
        prior = float(program["prior"])
        if not 3 <= n <= len(prefix) or not 0 < prior <= 10000:
            raise ValueError("invalid frequency parameter")
        raw = (prefix[-n:].astype(np.float64).sum(axis=0) + prior * EXPECTED) / (n + prior)
    elif op == "decay":
        half_life = float(program["half_life"])
        if not 0.1 <= half_life <= 1000:
            raise ValueError("invalid decay parameter")
        n = min(len(prefix), int(math.ceil(12 * half_life)))
        weights = np.exp2(-np.arange(n - 1, -1, -1) / half_life)
        raw = (weights @ prefix[-n:].astype(np.float64) + EXPECTED) / (weights.sum() + 1)
    elif op == "gap":
        scale = float(program["scale"])
        if not 0.1 <= scale <= 1000:
            raise ValueError("invalid gap parameter")
        indices = np.arange(len(prefix), dtype=np.int64)
        positions = np.where(prefix.astype(bool), indices[:, None], -1).max(axis=0)
        distances = len(prefix) - 1 - positions
        raw = .03 + 1.0 / (1.0 + distances / scale)
    elif op == "pair":
        window = min(int(program["window"]), len(prefix) - 1)
        prior = float(program["prior"])
        if not 3 <= window < len(prefix) or not 0 < prior <= 10000:
            raise ValueError("invalid pair parameter")
        prev = prefix[-window - 1:-1].astype(np.int64, copy=False)
        nxt = prefix[-window:].astype(np.int64, copy=False)
        last = prefix[-1].astype(np.int64, copy=False)
        # Explicit int64 to avoid legacy int8 co-occurrence overflow.
        context_weight = (prev @ last) / PICKS
        raw = (context_weight @ nxt + prior * EXPECTED) / (context_weight.sum() + prior)
    elif op == "blend":
        alpha = float(program["alpha"])
        if not 0 <= alpha <= 1:
            raise ValueError("invalid blend parameter")
        a = scores(prefix, program["left"], depth + 1)
        b = scores(prefix, program["right"], depth + 1)
        raw = alpha * a / a.mean() + (1 - alpha) * b / b.mean()
    elif op == "power":
        exponent = float(program["exponent"])
        if not .1 <= exponent <= 4:
            raise ValueError("invalid power parameter")
        a = scores(prefix, program["child"], depth + 1)
        raw = np.power(a / a.mean(), exponent)
    else:
        raise ValueError("unknown evolved program instruction")
    if raw.shape != (N_NUMBERS,) or not np.all(np.isfinite(raw)) or np.any(raw < 0):
        raise ValueError("invalid evolved model output")
    return np.maximum(raw, 1e-12)


def inclusion(prefix: np.ndarray, program: dict) -> np.ndarray:
    """Produce a valid seven-of-37 marginal vector from a dynamic program."""
    raw = scores(prefix, program)
    scaled = .35 + .65 * raw / raw.mean()
    lo, hi = 0., 50.
    for _ in range(58):
        mid = (lo + hi) / 2
        q = np.clip(scaled * mid, 1e-8, 1 - 1e-8)
        if q.sum() > PICKS:
            hi = mid
        else:
            lo = mid
    q = np.clip(scaled * ((lo + hi) / 2), 1e-8, 1 - 1e-8)
    if not math.isclose(float(q.sum()), PICKS, abs_tol=1e-8):
        raise ValueError("invalid evolved inclusion vector")
    return q


def assess(x: np.ndarray, program: dict) -> dict:
    """Research-only prequential backtest; model selection reuses these draws."""
    deltas, hits = [], []
    for i in range(len(x) - BACKTEST, len(x)):
        q = inclusion(x[:i], program)
        actual = x[i].astype(np.float64)
        value = actual * np.log(q / EXPECTED) + (1 - actual) * np.log((1 - q) / (1 - EXPECTED))
        deltas.append(float(value.mean()))
        hits.append(int(actual[np.argsort(-q, kind="stable")[:PICKS]].sum()))
    blocks = [float(np.mean(deltas[i:i+16])) for i in (0, 16, 32)]
    return {
        "mean_log_edge": float(np.mean(deltas)),
        "mean_top7_hits": float(np.mean(hits)),
        "block_edges": blocks,
        "fitness": float(np.mean(deltas) - 0.15 * np.std(blocks)),
        "historical_selection_only": True,
        "prospective_edge_confirmed": False,
    }


def program_text(genome: dict, generation: int) -> str:
    """Research code is regenerated on every accepted genome, not executed."""
    data = encoded(genome)
    return (
        '"""AUTO-GENERATED RESEARCH MODEL. NOT PRODUCTION. DO NOT IMPORT IN OOS."""\n'
        'import json\n'
        'from open_ended_evolution_agent import inclusion\n'
        f'GENERATION = {generation}\n'
        f'GENOME = json.loads({data!r})\n'
        'def predict_inclusion_probability(prior_history):\n'
        '    return inclusion(prior_history, GENOME)\n'
    )


def restore_state(out: Path) -> tuple[dict | None, list[dict]]:
    records = journal(out / LEDGER)
    path = out / STATE
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if records:
        latest = records[-1]
        snapshot = latest["snapshot"]
        if snapshot["last_record_sha256"] != latest["record_sha256"]:
            raise ValueError("checkpoint and journal digest mismatch")
        if state is not None and encoded(state) != encoded(snapshot):
            # A crash between the atomic journal and state replacements may
            # leave exactly the previous verified checkpoint on disk.
            previous = records[-2]["snapshot"] if len(records) > 1 else None
            if previous is not None and encoded(state) == encoded(previous):
                state = None
            else:
                # In particular, an edited state with an unchanged record hash
                # must NOT be trusted: hash equality alone is insufficient.
                raise ValueError("evolutionary state differs from authenticated journal")
        if state is None:
            state = snapshot
    elif state is not None:
        raise ValueError("evolutionary state exists without audit journal")
    return state, records


def elite_pool(candidates: list[dict], size: int = 8) -> list[dict]:
    """Keep unique program structures; lifetime generations are unrestricted."""
    seen, pool = set(), []
    for candidate in sorted(
        candidates, key=lambda item: (-item["assessment"]["fitness"], item["generation"])
    ):
        key = encoded(candidate["genome"])
        if key not in seen:
            seen.add(key)
            pool.append(candidate)
        if len(pool) >= size:
            break
    return pool


def cycle(root: Path, *, steps: int | None = None, seconds: float = 45.0) -> dict:
    """Run until a per-run deadline, checkpoint; next run resumes indefinitely."""
    if steps is not None and steps < 0:
        raise ValueError("steps must not be negative")
    if seconds < 0:
        raise ValueError("negative deadline")
    root = root.resolve()
    out = root / "loto7_agent_output"
    x, meta = history(root)
    state, chain = restore_state(out)
    start_gen = int(state["generations_total"]) if state else 0
    champion = copy.deepcopy(state["research_champion"]) if state else None
    hall = elite_pool(copy.deepcopy(state.get("hall_of_fame", []))) if state else []
    if champion and state.get("evaluated_history_sha256") != meta["data_sha256"]:
        champion["assessment"] = assess(x, champion["genome"])
        champion["research_data_sha256"] = meta["data_sha256"]
        hall = [champion]
    completed = 0
    begin = time.monotonic()
    trace = []
    while ((steps is None or completed < steps)
           and (steps is not None or time.monotonic() - begin < seconds)):
        generation = start_gen + completed + 1
        # Deterministic by input data SHA and absolute generation number.
        # Splitting 100 generations into hourly jobs must not alter outcomes.
        seed = int(sha((meta["data_sha256"] + "|" + str(generation)).encode())[:16], 16)
        rng = np.random.default_rng(seed)
        if champion is None:
            genome = {"op": "frequency", "window": 60, "prior": 100.}
        elif rng.random() < .18:
            genome = random_program(rng)
        else:
            parent = champion if not hall or rng.random() < .65 else hall[int(rng.integers(len(hall)))]
            genome = mutate(parent["genome"], rng)
        # Mutation and crossover may make increasingly deep programs. Bound
        # one model's computational complexity, not the lifetime search size.
        def program_shape(node):
            children = ([node[k] for k in ("left", "right")] if node["op"] == "blend"
                        else [node["child"]] if node["op"] == "power" else [])
            shapes = [program_shape(child) for child in children]
            return (1 + sum(item[0] for item in shapes),
                    1 + max((item[1] for item in shapes), default=0))
        nodes, depth = program_shape(genome)
        if nodes > 120 or depth > 8:
            genome = random_program(rng)
        result = assess(x, genome)
        candidate = {
            "generation": generation, "genome": genome, "assessment": result,
            "research_data_sha256": meta["data_sha256"],
        }
        if (champion is None
                or result["fitness"] > champion["assessment"]["fitness"]):
            champion = candidate
        # Bounded distinct working population, not a global generation cap.
        # Duplicate genomes cannot crowd out all genetic diversity.
        hall = elite_pool([*hall, candidate])
        trace.append({"generation": generation,
                      "fitness": result["fitness"],
                      "genome_sha256": sha(encoded(genome).encode())})
        completed += 1
    generation = start_gen + completed
    if not completed and state is not None and state.get("evaluated_history_sha256") == meta["data_sha256"]:
        return state
    if champion is None:
        raise ValueError("initial cycle must evaluate a candidate")
    # One chained audit checkpoint per execution rather than a Git commit
    # for each generation; trajectory hash still commits the full run summary.
    event = {
        "sequence": len(chain) + 1,
        "previous_record_sha256": chain[-1]["record_sha256"] if chain else GENESIS,
        "first_generation": start_gen + 1 if completed else start_gen,
        "last_generation": generation,
        "candidates_evaluated": completed,
        "evaluation_data_sha256": meta["data_sha256"],
        "trajectory_sha256": sha(encoded(trace).encode()),
        "best_historical_fitness": champion["assessment"]["fitness"],
        "genome_sha256": sha(encoded(champion["genome"]).encode()),
    }
    # Sign the checkpoint content without a circular record-SHA reference.
    result = {
        "version": VERSION, "generations_total": generation,
        "evaluated_history_sha256": meta["data_sha256"],
        "recorded_rounds": meta["recorded_rounds"],
        "evaluation_rounds": meta["evaluation_rounds"],
        "latest_verification": meta["latest_verification"],
        "last_unverified_row_excluded": meta["last_unverified_row_excluded"],
        "independent_source_verified": meta["independent_source_verified"],
        "research_champion": champion, "hall_of_fame": hall,
        "execution_limits": {"global_generation_cap": None, "global_trial_cap": None,
                             "needs_new_draw_to_continue": False},
        "scope": "indefinite_historical_model_program_evolution_not_production",
        "claim": "Selection on reused historical data cannot establish predictive advantage.",
    }
    event["snapshot_sha256"] = sha(encoded(result).encode("utf-8"))
    record_hash = sha(encoded(event).encode("utf-8"))
    result["last_record_sha256"] = record_hash
    event["record_sha256"] = record_hash
    event["snapshot"] = result
    if chain:
        content = (out / LEDGER).read_text(encoding="utf-8")
    else:
        content = ""
    atomic(out / LEDGER, content + encoded(event) + "\n")
    atomic(out / STATE, json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    atomic(out / PROGRAM, program_text(champion["genome"], champion["generation"]))
    report = (
        "# Open-ended Autonomous Evolution\n\n"
        f"- Total research generations: **{generation}** (no predefined global cap)\n"
        f"- Latest execution: **{completed}** candidate evaluations\n"
        f"- Data SHA256: {meta['data_sha256']}\n"
        f"- Source verification: {meta['latest_verification']}\n"
        f"- Latest unverified draw excluded: {meta['last_unverified_row_excluded']}\n"
        f"- Historical diagnostic fitness: **{champion['assessment']['fitness']:+.8f}**\n"
        f"- Champion research gene from generation: {champion['generation']}\n\n"
        "**Not a Production champion.** Unbounded repeated historical tuning "
        "creates selection bias and provides no proof of future predictive edge.\n"
    )
    atomic(out / REPORT, report)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Open-ended autonomous research evolution")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--seconds", type=float, default=45)
    parser.add_argument("--steps", type=int, default=None,
                        help="Optional single-run limit for repeatable CI/tests, not global research cap")
    args = parser.parse_args()
    state = cycle(args.repo_root, steps=args.steps, seconds=args.seconds)
    print(encoded({
        "generation": state["generations_total"],
        "historical_fitness": state["research_champion"]["assessment"]["fitness"],
        "source_verification": state["latest_verification"],
        "global_generation_cap": None,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
