#!/usr/bin/env python3
"""Recursive research-only evolution of executable mathematical source expressions.

Unlike parameter-only evolution, this agent modifies the syntax tree of the
model formula and learns which *mutation operators* succeed. It continues
across executions without a lifetime generation or trial cap. Every candidate
is tested on prior-only historical features, not future unseen outcomes.

This is NOT an unrestricted system process, Production predictor, or evidence
of predictive skill. Source generation uses a constrained mathematical AST.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path

import numpy as np

from open_ended_evolution_agent import atomic, encoded, history, journal

VERSION = "recursive-code-meta-evolution-v1"
STATE = "recursive_self_evolution_state.json"
LEDGER = "recursive_self_evolution_journal.jsonl"
PROGRAM = "recursive_self_evolution_candidate.py"
REPORT = "recursive_self_evolution_report.md"
GENESIS = "GENESIS"
NUMBERS = 37
PICKS = 7
EXPECTED = PICKS / NUMBERS
MIN_TRAIN = 100
EVALUATION_ROUNDS = 24
FEATURE_NAMES = ("uniform", "hot20", "hot80", "cold20", "decay", "gap", "pair")
FUNCTIONS = {
    "abs": np.abs, "sqrt": np.sqrt, "tanh": np.tanh, "log1p": np.log1p,
}
MOVES = ("restart", "splice", "tune", "wrap", "crossover")


def digest(value: object) -> str:
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def feature_vectors(prior: np.ndarray) -> dict[str, np.ndarray]:
    """All features depend solely on already-observed draws."""
    x = np.asarray(prior)
    if (x.ndim != 2 or x.shape[1] != NUMBERS or len(x) < MIN_TRAIN
            or not np.issubdtype(x.dtype, np.integer)
            or not np.all((x == 0) | (x == 1))
            or not np.all(x.sum(axis=1, dtype=np.int64) == PICKS)):
        raise ValueError("invalid prior seven-of-37 history")
    wide = x.astype(np.int64, copy=False)
    def norm(values):
        a = np.asarray(values, dtype=np.float64)
        if a.shape != (NUMBERS,) or not np.all(np.isfinite(a)) or np.any(a < 0):
            raise ValueError("invalid historical signal feature")
        return (a + 0.05) / (float(a.mean()) + 0.05)
    f20 = wide[-20:].mean(axis=0)
    f80 = wide[-80:].mean(axis=0)
    n = min(len(x), 160)
    weights = np.exp2(-np.arange(n - 1, -1, -1, dtype=float) / 30.0)
    decay = weights @ wide[-n:] / weights.sum()
    last_seen = np.where(wide != 0, np.arange(len(x))[:, None], -1).max(axis=0)
    gap = len(x) - 1 - last_seen
    co = wide.T @ wide  # int64 BEFORE multiply; no legacy int8 wrap
    last = np.flatnonzero(wide[-1])
    den = np.maximum(wide.sum(axis=0, dtype=np.int64)[last], 1)
    pair = (co[:, last] / den).mean(axis=1)
    return {
        "uniform": np.ones(NUMBERS, dtype=np.float64),
        "hot20": norm(f20),
        "hot80": norm(f80),
        "cold20": norm(1.0 - f20),
        "decay": norm(decay),
        "gap": norm(1.0 / (1.0 + gap / 15.0)),
        "pair": norm(pair),
    }


def parse_expression(source: str) -> ast.Expression:
    """Allow executable math expressions, reject statements and Python escape hatches."""
    if not isinstance(source, str) or not source or len(source) > 2000:
        raise ValueError("invalid evolved expression length")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError("invalid mathematical expression") from exc

    def check(node, depth=0):
        if depth > 12:
            raise ValueError("mathematical expression depth exceeded")
        if isinstance(node, ast.Expression):
            check(node.body, depth + 1)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            check(node.left, depth + 1)
            check(node.right, depth + 1)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            check(node.operand, depth + 1)
        elif isinstance(node, ast.Name) and node.id in FEATURE_NAMES:
            return
        elif isinstance(node, ast.Constant) and type(node.value) in (float, int) and (
                math.isfinite(float(node.value)) and abs(float(node.value)) <= 10):
            return
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in FUNCTIONS and len(node.args) == 1
              and not node.keywords):
            check(node.args[0], depth + 1)
        else:
            raise ValueError("unsupported instruction in evolved mathematical code")
    check(tree)
    if sum(1 for _ in ast.walk(tree)) > 100:
        raise ValueError("mathematical expression size exceeded")
    return tree


def expression_inclusion(feats: dict[str, np.ndarray], expression: str) -> np.ndarray:
    tree = parse_expression(expression)
    env = {**FUNCTIONS, **feats}
    with np.errstate(all="ignore"):
        raw = eval(compile(tree, "<evolved-math-expression>", "eval"),
                   {"__builtins__": {}}, env)
    if np.isscalar(raw):
        a = np.full(NUMBERS, raw, dtype=np.float64)
    else:
        a = np.asarray(raw, dtype=np.float64)
    if a.shape != (NUMBERS,) or not np.all(np.isfinite(a)) or np.max(np.abs(a)) > 1e8:
        raise ValueError("evolved expression produced invalid scores")
    normalized = np.clip((a - a.mean()) / (1.0 + a.std()), -5.0, 5.0)
    odds = np.exp(normalized)
    lo, hi = 0.0, 50.0
    for _ in range(58):
        mid = (lo + hi) / 2
        q = np.clip(odds * mid, 1e-9, 1 - 1e-9)
        if q.sum() > PICKS:
            hi = mid
        else:
            lo = mid
    q = np.clip(odds * ((lo + hi) / 2), 1e-9, 1 - 1e-9)
    if not np.isclose(q.sum(), PICKS, rtol=0, atol=1e-8):
        raise ValueError("not a calibrated inclusion vector")
    return q


def predict_inclusion_probability(prior: np.ndarray, expression: str) -> np.ndarray:
    return expression_inclusion(feature_vectors(prior), expression)


def random_expr(rng: np.random.Generator, depth: int = 0) -> str:
    if depth >= 3 or rng.random() < .4:
        return str(rng.choice(FEATURE_NAMES)) if rng.random() < .78 else str(round(float(rng.uniform(.1, 3)), 4))
    a = random_expr(rng, depth + 1)
    b = random_expr(rng, depth + 1)
    kind = int(rng.integers(0, 5))
    if kind == 0:
        return f"({a} + {b})"
    if kind == 1:
        return f"({a} * {b})"
    if kind == 2:
        return f"({a} - {b})"
    if kind == 3:
        return f"tanh({a} + {b})"
    return f"sqrt(abs({a} - {b}) + 0.1)"


def adapt_probabilities(policy: dict) -> np.ndarray:
    # Nonzero exploration remains available after arbitrarily many runs.
    scores = np.array([
        .1 + (policy[m]["wins"] + 1) / (policy[m]["trials"] + 2)
        + .35 / math.sqrt(policy[m]["trials"] + 1)
        for m in MOVES
    ], dtype=np.float64)
    return scores / scores.sum()


def alter(parent: str, peer: str, move: str, rng: np.random.Generator) -> str:
    if move == "restart":
        proposal = random_expr(rng)
    elif move == "wrap":
        proposal = f"tanh(({parent}) + ({random_expr(rng, 2)}))"
    elif move == "crossover":
        proposal = f"(({parent}) + ({peer}))"
    else:
        tree = copy.deepcopy(parse_expression(parent))
        if move == "splice":
            names = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in FEATURE_NAMES]
            if not names:
                return random_expr(rng)
            names[int(rng.integers(0, len(names)))].id = str(rng.choice(FEATURE_NAMES))
        elif move == "tune":
            values = [n for n in ast.walk(tree) if isinstance(n, ast.Constant)
                      and type(n.value) in (float, int)]
            if not values:
                return f"(({parent}) + ({round(float(rng.uniform(.1, .7)), 4)} * hot20))"
            item = values[int(rng.integers(len(values)))]
            item.value = round(float(np.clip(float(item.value) * np.exp(rng.normal(0, .3)), .01, 9.0)), 5)
        else:
            raise ValueError("unknown self-evolution mutation strategy")
        proposal = ast.unparse(tree)
    try:
        parse_expression(proposal)
        return proposal
    except ValueError:
        return random_expr(rng)


def assessment(features: list[dict[str, np.ndarray]], outcomes: np.ndarray,
               expression: str) -> dict:
    parse_expression(expression)
    log_edges, hits = [], []
    if len(features) != EVALUATION_ROUNDS or len(outcomes) != len(features):
        raise ValueError("invalid historical evaluation interval")
    for f, result in zip(features, outcomes):
        q = expression_inclusion(f, expression)
        y = result.astype(np.float64)
        edge = y * np.log(q / EXPECTED) + (1.0 - y) * np.log((1.0 - q) / (1.0 - EXPECTED))
        log_edges.append(float(edge.mean()))
        hits.append(int(y[np.argsort(-q, kind="stable")[:PICKS]].sum()))
    blocks = [float(np.mean(log_edges[i:i + 8])) for i in (0, 8, 16)]
    return {
        "fitness": float(np.mean(log_edges) - .12 * np.std(blocks) - 0.0000001 * len(expression)),
        "mean_log_edge_vs_uniform": float(np.mean(log_edges)),
        "mean_top7_hits": float(np.mean(hits)),
        "historical_selection_only": True,
        "prospective_improvement_proven": False,
    }


def evaluation_cache(x: np.ndarray) -> tuple[list[dict[str, np.ndarray]], np.ndarray]:
    if len(x) < MIN_TRAIN + EVALUATION_ROUNDS:
        raise ValueError("too few historical rounds")
    return ([feature_vectors(x[:i]) for i in range(len(x) - EVALUATION_ROUNDS, len(x))],
            x[-EVALUATION_ROUNDS:])


def reload_checkpoint(out: Path) -> tuple[dict | None, list[dict]]:
    chain = journal(out / LEDGER)
    p = out / STATE
    state = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    if chain:
        wanted = chain[-1]["snapshot"]
        if state is not None and encoded(state) != encoded(wanted):
            previous = chain[-2]["snapshot"] if len(chain) > 1 else None
            if previous is None or encoded(state) != encoded(previous):
                raise ValueError("recursive self-evolution state differs from journal")
            state = None
        state = wanted if state is None else state
    elif state is not None:
        raise ValueError("recursive state exists without audit journal")
    return state, chain


def elites(items: list[dict], count: int = 10) -> list[dict]:
    result, used = [], set()
    for item in sorted(items, key=lambda c: (-c["assessment"]["fitness"], c["generation"])):
        expr = item["expression"]
        if expr not in used:
            result.append(item)
            used.add(expr)
        if len(result) >= count:
            break
    return result


def generated_source(expression: str, generation: int) -> str:
    parse_expression(expression)
    return (
        '"""AUTOGENERATED MATHEMATICAL RESEARCH CODE; NOT PRODUCTION."""\n'
        'from recursive_self_evolution_agent import predict_inclusion_probability as _predict\n'
        f"GENERATION = {generation}\n"
        f"EXPRESSION = {expression!r}\n"
        "def predict_inclusion_probability(prior_history):\n"
        "    return _predict(prior_history, EXPRESSION)\n"
    )


def cycle(root: Path, *, steps: int | None = None, seconds: float = 25.0) -> dict:
    """Meta-evolve a program and its mutation operator policy indefinitely."""
    if steps is not None and steps < 0 or seconds < 0:
        raise ValueError("negative execution budget")
    root = root.resolve()
    x, source = history(root)
    f, outcomes = evaluation_cache(x)
    out = root / "loto7_agent_output"
    state, chain = reload_checkpoint(out)
    generation_start = state["generations_total"] if state else 0
    champion = copy.deepcopy(state["research_champion"]) if state else None
    archive = copy.deepcopy(state["hall_of_fame"]) if state else []
    policy = copy.deepcopy(state["mutation_policy"]) if state else {
        move: {"trials": 0, "wins": 0} for move in MOVES
    }
    if state and state.get("evaluation_data_sha256") != source["data_sha256"]:
        # Historical scores are never compared across distinct data revisions.
        rescored = []
        for old in elites([*archive, champion]):
            fresh = copy.deepcopy(old)
            fresh["assessment"] = assessment(f, outcomes, fresh["expression"])
            fresh["research_data_sha256"] = source["data_sha256"]
            rescored.append(fresh)
        archive = elites(rescored)
        champion = archive[0] if archive else None
        policy = {move: {"trials": 0, "wins": 0} for move in MOVES}
    traces = []
    start = time.monotonic()
    completed = 0
    while (steps is None or completed < steps) and (
        steps is not None or time.monotonic() - start < seconds
    ):
        generation = generation_start + completed + 1
        seed = int(hashlib.sha256(
            (source["data_sha256"] + "|recursive|" + str(generation)).encode()
        ).hexdigest()[:16], 16)
        rng = np.random.default_rng(seed)
        move = str(rng.choice(MOVES, p=adapt_probabilities(policy)))
        parent = champion if not archive or rng.random() < .6 else archive[int(rng.integers(len(archive)))]
        parent_expr = parent["expression"] if parent else "uniform"
        peer = archive[int(rng.integers(len(archive)))]["expression"] if archive else "hot20"
        expr = "uniform" if champion is None else alter(parent_expr, peer, move, rng)
        try:
            result = assessment(f, outcomes, expr)
        except (ValueError, ArithmeticError, OverflowError, TypeError):
            expr = "uniform"
            result = assessment(f, outcomes, expr)
        cand = {"generation": generation, "expression": expr, "assessment": result,
                "research_data_sha256": source["data_sha256"]}
        # Success is against current best, not a claim of out-of-sample skill.
        improvement = champion is None or result["fitness"] > champion["assessment"]["fitness"] + 1e-13
        policy[move]["trials"] += 1
        if improvement:
            policy[move]["wins"] += 1
            champion = cand
        archive = elites([*archive, cand])
        traces.append({"generation": generation, "move": move,
                       "fitness": result["fitness"], "expression_sha256": digest(expr)})
        completed += 1
    generation = generation_start + completed
    if completed == 0 and state is not None and state.get("evaluation_data_sha256") == source["data_sha256"]:
        return state
    if champion is None:
        raise ValueError("no initial research genome")
    result = {
        "version": VERSION, "generations_total": generation,
        "evaluation_data_sha256": source["data_sha256"],
        "latest_verification": source["latest_verification"],
        "independent_source_verified": source["independent_source_verified"],
        "recorded_rounds": source["recorded_rounds"],
        "evaluation_rounds": EVALUATION_ROUNDS,
        "research_champion": champion,
        "hall_of_fame": archive,
        "mutation_policy": policy,
        "mutation_probabilities": dict(zip(MOVES, [float(v) for v in adapt_probabilities(policy)])),
        "execution_limits": {
            "global_generations": None, "global_trials": None,
            "requires_new_draw": False, "per_run_wall_seconds": seconds,
        },
        "authority": {
            "production_predictions": False,
            "retrospective_oos_freezes": False,
            "edit_existing_registered_models": False,
            "autonomous_main_code_changes": False,
        },
        "scope": "autonomous_recursive_mathematical_program_and_meta_policy_evolution_research_only",
        "claim": "Repeated historical optimization cannot establish future lottery advantage.",
    }
    event = {
        "sequence": len(chain) + 1,
        "previous_record_sha256": chain[-1]["record_sha256"] if chain else GENESIS,
        "first_generation": generation_start + 1 if completed else generation_start,
        "last_generation": generation,
        "candidates_evaluated": completed,
        "evaluation_data_sha256": source["data_sha256"],
        "trajectory_sha256": digest(traces),
        "best_historical_fitness": champion["assessment"]["fitness"],
        "expression_sha256": digest(champion["expression"]),
    }
    event["snapshot_sha256"] = digest(result)
    recordhash = digest(event)
    result["last_record_sha256"] = recordhash
    event["record_sha256"] = recordhash
    event["snapshot"] = result
    old_journal = (out / LEDGER).read_text(encoding="utf-8") if chain else ""
    atomic(out / LEDGER, old_journal + encoded(event) + "\n")
    atomic(out / STATE, json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    atomic(out / PROGRAM, generated_source(champion["expression"], champion["generation"]))
    report = (
        "# Recursive self-evolution (research-only)\n\n"
        f"- Total evolving program generations: **{generation}** (no global cap)\n"
        f"- Last-run generations: **{completed}**\n"
        f"- Mutation policy learned: **{dict((k, round(v, 3)) for k, v in result['mutation_probabilities'].items())}**\n"
        f"- Historical selection fitness: **{champion['assessment']['fitness']:+.8f}**\n"
        f"- Independent draw-source verified: **{source['independent_source_verified']}**\n"
        f"- Draw history SHA256: {source['data_sha256']}\n\n"
        "**Research only.** It mutates executable mathematical expressions "
        "and mutation choices, not its Production privileges or safety evidence. "
        "No future lottery prediction improvement is proven.\n"
    )
    atomic(out / REPORT, report)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--seconds", type=float, default=25.0)
    parser.add_argument("--steps", type=int, default=None)
    args = parser.parse_args()
    result = cycle(args.repo_root, steps=args.steps, seconds=args.seconds)
    print(encoded({
        "generations": result["generations_total"],
        "fitness": result["research_champion"]["assessment"]["fitness"],
        "policy": result["mutation_probabilities"],
        "global_generation_limit": None,
        "production_change": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
