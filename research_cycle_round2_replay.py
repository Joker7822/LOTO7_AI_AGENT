#!/usr/bin/env python3
"""Research-only replay after each recursive model checkpoint (rounds 2..N).

This script does NOT rewrite issued predictions, Champion or prospective OOS.
The expression was selected after seeing historical outcomes, so this entire
replay is exploratory even though each individual forecast uses prior rows only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible
from loto7_v4_runner import parse_round
from recursive_self_evolution_agent import (
    MIN_TRAIN, NUMBERS, PICKS, VERSION as EVOLUTION_VERSION,
    parse_expression, predict_inclusion_probability, reload_checkpoint,
)

VERSION = "verified-research-round2-evolution-replay-v1"
UNIFORM = PICKS / NUMBERS
SEED = 20261103
MAX_TICKETS = 5


def sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_candidate(root: Path, data_sha: str, draws: int) -> dict:
    """Fail closed unless the model is identical to its SHA-chained checkpoint."""
    state, chain = reload_checkpoint(root / "loto7_agent_output")
    if not state or not chain or state.get("version") != EVOLUTION_VERSION:
        raise ValueError("verified recursive evolution checkpoint missing")
    if (state.get("evaluation_data_sha256") != data_sha
            or state.get("recorded_rounds") != draws
            or state.get("independent_source_verified") is not True
            or state.get("latest_verification") != "verified_two_result_sources"):
        raise ValueError("evolution checkpoint does not match current verified draws")
    if (state.get("last_record_sha256") != chain[-1]["record_sha256"]
            or state.get("authority", {}).get("production_predictions") is not False
            or state.get("authority", {}).get("retrospective_oos_freezes") is not False):
        raise ValueError("evolution provenance/authority mismatch")
    champion = state.get("research_champion")
    if not isinstance(champion, dict):
        raise ValueError("missing selected research candidate")
    expr = champion.get("expression")
    parse_expression(expr)
    assessment = champion.get("assessment", {})
    if (champion.get("research_data_sha256") != data_sha
            or assessment.get("historical_selection_only") is not True
            or assessment.get("prospective_improvement_proven") is not False):
        raise ValueError("research model has an invalid evidence claim")
    return {
        "expression": expr,
        "expression_sha256": hashlib.sha256(expr.encode("utf-8")).hexdigest(),
        "generation": champion["generation"],
        "generations_total": state["generations_total"],
        "checkpoint_sha256": sha(state),
        "checkpoint_record_sha256": state["last_record_sha256"],
        "checkpoint_scope": "historically_selected_research_only",
    }


def bibliography_audit(root: Path) -> dict:
    """Bibliographic provenance is informative, never executable model authority."""
    path = root / "loto7_agent_output/research_verified_publications.json"
    if not path.is_file():
        return {"status": "not_available", "verified_works": 0,
                "new_executable_methods_authorized": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("verifications")
    if not isinstance(items, list):
        raise ValueError("invalid verified bibliography")
    statuses = Counter(
        item.get("status") for item in items if isinstance(item, dict)
    )
    if sum(statuses.values()) != len(items):
        raise ValueError("malformed verified bibliography")
    return {
        "status": "metadata_only",
        "snapshot_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "publication_status_counts": dict(statuses),
        "verified_works": sum(statuses.get(k, 0) for k in
                              ("two_provider_bibliography_matched",
                               "previously_verified_not_refreshed")),
        "full_text_method_reproduction": False,
        "new_executable_methods_authorized": False,
        "note": "Two-provider DOI identity checks are not experimental replication.",
    }


def top_seven(p: np.ndarray, seed: int) -> list[int]:
    # Independent seeded tie-break, required for uniform and cold-start runs.
    rng = np.random.default_rng(seed)
    ix = np.lexsort((rng.random(NUMBERS), -p))[:PICKS]
    return sorted((ix + 1).tolist())


def five_tickets(p: np.ndarray, seed: int) -> list[list[int]]:
    """Deterministic exploratory five-ticket set; not a published purchase."""
    rng = np.random.default_rng(seed)
    tickets: set[tuple[int, ...]] = set()
    for _ in range(200):
        ix = rng.choice(NUMBERS, size=PICKS, replace=False, p=p / p.sum())
        tickets.add(tuple(sorted((ix + 1).tolist())))
        if len(tickets) == MAX_TICKETS:
            break
    if len(tickets) != MAX_TICKETS:
        raise ValueError("unable to construct five different research tickets")
    return [list(t) for t in sorted(tickets)]


def score(p: np.ndarray, actual: np.ndarray) -> dict:
    y = actual.astype(float)
    baseline = np.full(NUMBERS, UNIFORM)
    return {
        "log_edge_vs_uniform": float(np.mean(
            y * np.log(p / baseline)
            + (1.0 - y) * np.log((1.0 - p) / (1.0 - baseline))
        )),
        "brier_edge_vs_uniform": float(np.mean(
            (y - baseline) ** 2 - (y - p) ** 2
        )),
    }


def phases(rows: list[dict]) -> dict:
    intervals = {
        "all_2_onward": rows,
        "cold_start_2_to_100": [r for r in rows if r["round"] <= MIN_TRAIN],
        "evolved_101_onward": [r for r in rows if r["round"] > MIN_TRAIN],
        "last_60": rows[-60:],
    }
    out = {}
    for name, subset in intervals.items():
        if not subset:
            continue
        out[name] = {
            "count": len(subset),
            "from_round": subset[0]["round"],
            "through_round": subset[-1]["round"],
            "mean_top7_hits": float(np.mean([r["research_top7_hits"] for r in subset])),
            "mean_uniform_top7_hits": float(np.mean([r["uniform_top7_hits"] for r in subset])),
            "mean_max_five_ticket_hits": float(np.mean([r["research_five_max_hits"] for r in subset])),
            "mean_uniform_five_max_hits": float(np.mean([r["uniform_five_max_hits"] for r in subset])),
            "mean_log_edge_vs_uniform": float(np.mean([
                r["proper_scores"]["log_edge_vs_uniform"] for r in subset
            ])),
            "mean_brier_edge_vs_uniform": float(np.mean([
                r["proper_scores"]["brier_edge_vs_uniform"] for r in subset
            ])),
        }
    return out


def replay(x: np.ndarray, expression: str, *, dates: list[str] | None = None,
           seed: int = SEED) -> dict:
    """Reconstruct predictions for every target, never feeding x[t] into its forecast."""
    x = np.asarray(x)
    if (x.ndim != 2 or x.shape[1] != NUMBERS or len(x) < MIN_TRAIN + 1
            or not np.issubdtype(x.dtype, np.integer)
            or not np.all((x == 0) | (x == 1))
            or not np.all(x.sum(axis=1, dtype=np.int64) == PICKS)):
        raise ValueError("requires consecutive valid 7/37 history, at least 101 draws")
    if dates is not None and len(dates) != len(x):
        raise ValueError("draw dates do not match history")
    parse_expression(expression)
    rows = []
    uniform = np.full(NUMBERS, UNIFORM)
    for t in range(1, len(x)):
        number = t + 1
        # An already-selected expression may contain hindsight information.
        # Its *evaluation* is retrospective, regardless of this prior-only call.
        p = (uniform.copy() if t < MIN_TRAIN else
             predict_inclusion_probability(x[:t], expression))
        if (p.shape != (NUMBERS,) or not np.all(np.isfinite(p))
                or np.any(p <= 0) or np.any(p >= 1)
                or not np.isclose(p.sum(), PICKS, rtol=0, atol=1e-7)):
            raise ValueError("invalid research model inclusion probabilities")
        research_top = top_seven(p, seed + number * 1009)
        baseline_top = top_seven(uniform, seed + number * 1009)
        research_tickets = five_tickets(p, seed + number * 2003)
        baseline_tickets = five_tickets(uniform, seed + number * 2003)
        frozen = {
            "round": number, "prior_draws": t,
            "research_top7": research_top, "uniform_top7": baseline_top,
            "research_tickets": research_tickets, "uniform_tickets": baseline_tickets,
            "research_inclusion_probabilities": [float(v) for v in p],
        }
        digest = sha(frozen)  # Frozen before touching outcome at x[t].
        actual_array = x[t]
        actual = set((np.flatnonzero(actual_array) + 1).tolist())
        def max_hits(tickets: list[list[int]]) -> int:
            return max(len(actual.intersection(ticket)) for ticket in tickets)
        rows.append({
            **frozen,
            "forecast_sha256": digest,
            "date": dates[t] if dates else None,
            "regime": "uniform_cold_start" if t < MIN_TRAIN else "evolved_research",
            "actual_numbers": sorted(actual),
            "research_top7_hits": len(set(research_top) & actual),
            "uniform_top7_hits": len(set(baseline_top) & actual),
            "research_five_max_hits": max_hits(research_tickets),
            "uniform_five_max_hits": max_hits(baseline_tickets),
            "proper_scores": score(p, actual_array),
        })
    return {
        "version": VERSION, "first_target_round": 2,
        "last_target_round": len(x), "evaluated_rounds": len(rows),
        "initial_uniform_through_round": MIN_TRAIN,
        "evolved_from_round": MIN_TRAIN + 1,
        "predictor_uses_prior_draws_only": True,
        "expression_selected_with_hindsight": True,
        "independent_prospective_evidence": False,
        "production_or_champion_modified": False,
        "historical_issued_predictions_replaced": False,
        "promotion_authorized": False,
        "methodology": {
            "chronology": "fixed expression -> per-target prior only -> digest -> outcome",
            "baseline": "uniform inclusion probability 7/37",
            "research_five_ticket_rule": "weighted_without_replacement_sampling",
            "validation": "prequential descriptive scores; no future-claim inference",
            "multiplicity": "repeated research candidate selection means reused-history bias",
        },
        "summary": phases(rows), "rounds": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path(
        "research_output/verified_research_round2_reforecast.json"))
    args = parser.parse_args()
    root = args.repo_root.resolve()
    csv_path = root / "loto7.csv"
    trusted = validate_trusted_source(
        csv_path, root / "loto7_agent_output/source_validation.json")
    if trusted.get("trusted") is not True:
        raise ValueError("draw data lacks independent-source attestation")
    x, frame = make_history(read_csv_flexible(csv_path))
    round_ids = [parse_round(v) for v in frame["回別"]]
    if round_ids != list(range(1, len(x) + 1)):
        raise ValueError("missing or nonconsecutive official round IDs")
    data_sha = fingerprint_file(csv_path)
    candidate = load_candidate(root, data_sha, len(x))
    dates = [d.date().isoformat() for d in frame["抽せん日"]]
    result = replay(x, candidate["expression"], dates=dates)
    result["data_sha256"] = data_sha
    result["candidate"] = candidate
    result["bibliography"] = bibliography_audit(root)
    result["source_attestation"] = trusted
    result["replay_implementation_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes()).hexdigest()
    destination = args.out if args.out.is_absolute() else root / args.out
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                      allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "from": 2, "through": len(x), "generation": candidate["generation"],
        "total_generations": candidate["generations_total"],
        "mean_evolved_log_edge": result["summary"]["evolved_101_onward"][
            "mean_log_edge_vs_uniform"],
        "research_only": True, "saved_to": str(destination),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
