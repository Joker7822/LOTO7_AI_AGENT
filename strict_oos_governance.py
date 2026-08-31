#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

VERSION = "strict-oos-governance-v1"
FAMILY_ALPHA = 0.05
HOLDOUT_TRUSTED_DRAWS = 26

PAIRED_FIELDS = [
    "round", "draw_date", "candidate_version", "champion_version", "formal_block_index",
    "candidate_score", "champion_score", "random_score",
    "delta_vs_champion", "delta_vs_random",
    "candidate_max_hits", "champion_max_hits", "random_max_hits",
    "champion_e_value_raw", "random_e_value_raw", "family_weight",
    "family_adjusted_e_value", "required_raw_e_value",
    "trusted_for_promotion", "source_verification", "random_reference_frozen_at_jst",
]

HOLDOUT_FIELDS = [
    "round", "draw_date", "holdout_version", "champion_version",
    "holdout_score", "champion_score", "random_score",
    "delta_vs_champion", "delta_vs_random",
    "holdout_max_hits", "champion_max_hits", "random_max_hits",
    "trusted", "source_verification", "frozen_at_jst",
]


def load_json(path: Path, default: Dict[str, object]) -> Dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else dict(default)
    except Exception:
        return dict(default)


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def append_csv(path: Path, rows: Iterable[Dict[str, object]], fields: Sequence[str]) -> None:
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields))
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def block_weight(block_index: int) -> float:
    """Alpha/e-capital weight. Sum_{i>=1} 1/(i(i+1)) = 1."""
    i = max(1, int(block_index))
    return 1.0 / (i * (i + 1))


def required_raw_e_value(block_index: int, family_alpha: float = FAMILY_ALPHA) -> float:
    return 1.0 / (max(1e-12, float(family_alpha)) * block_weight(block_index))


def e_value_from_components(components: object, lambdas: Sequence[float]) -> float:
    if not isinstance(components, dict):
        return 1.0
    vals = [float(components.get(str(lam), 1.0)) for lam in lambdas]
    return float(np.mean(vals)) if vals else 1.0


def update_e_components(components: object, normalized_delta: float,
                        lambdas: Sequence[float]) -> Dict[str, float]:
    old = components if isinstance(components, dict) else {}
    out: Dict[str, float] = {}
    for lam in lambdas:
        prev = float(old.get(str(lam), 1.0))
        factor = max(1e-12, 1.0 + float(lam) * float(normalized_delta))
        out[str(lam)] = prev * factor
    return out


def archived_block_count(path: Path) -> int:
    if not path.exists():
        return 0
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        block_id = str(rec.get("block_id", ""))
        if block_id:
            seen.add(block_id)
    return len(seen)


def current_block_index(out_dir: Path) -> int:
    # Archived blocks are immutable; the active block is always the next family member.
    return archived_block_count(out_dir / "formal_challenger_history.jsonl") + 1


def sync_formal_metadata(out_dir: Path) -> Dict[str, object]:
    registry_path = out_dir / "shadow_registry.json"
    state_path = out_dir / "formal_challenger_state.json"
    registry = load_json(registry_path, {})
    state = load_json(state_path, {})
    if not registry or not state or not state.get("candidate_version"):
        return {"synced": False}

    block_index = current_block_index(out_dir)
    weight = block_weight(block_index)
    threshold = required_raw_e_value(block_index)
    metadata = {
        "formal_block_index": block_index,
        "family_alpha": FAMILY_ALPHA,
        "family_weight": weight,
        "required_raw_e_value": threshold,
        "multiplicity_policy": "sequential_e_capital_1_over_i_i_plus_1",
    }
    registry.update(metadata)
    state.update(metadata)
    write_json(registry_path, registry)
    write_json(state_path, state)

    oos_path = out_dir / "oos_candidate_state.json"
    oos = load_json(oos_path, {})
    oos["strict_governance_version"] = VERSION
    oos["promotion_family_blocks_started"] = max(
        int(oos.get("promotion_family_blocks_started", 0) or 0), block_index
    )
    oos["promotion_family_alpha"] = FAMILY_ALPHA
    write_json(oos_path, oos)
    return {"synced": True, **metadata}


def deterministic_random_tickets(v4, target_round: int) -> List[List[int]]:
    rng = np.random.default_rng(12_000_000 + int(target_round) * 1009)
    tickets = v4.v2._random_portfolio(rng)
    return [[int(n) for n in ticket] for ticket in tickets]


def ensure_random_reference(v4, registry_path: Path, latest_round: Optional[int] = None) -> bool:
    registry = load_json(registry_path, {})
    if not registry:
        return False
    target_round = int(registry.get("target_round", -1))
    # Never manufacture a "pre-frozen" null after its result is already in the CSV.
    if latest_round is not None and target_round <= int(latest_round):
        return bool(registry.get("random_reference_tickets"))
    if registry.get("random_reference_tickets"):
        return True
    if target_round < 1:
        return False
    registry["random_reference_tickets"] = deterministic_random_tickets(v4, target_round)
    registry["random_reference_method"] = "deterministic_uniform_5_ticket_portfolio"
    registry["random_reference_seed_policy"] = "12000000 + target_round * 1009"
    registry["random_reference_frozen_at_jst"] = v4.now_jst()
    write_json(registry_path, registry)
    return True


def _update_random_evidence(v4, rec: Dict[str, object], delta: float, trusted: bool) -> None:
    if not trusted:
        return
    rec["random_trusted_draws"] = int(rec.get("random_trusted_draws", 0) or 0) + 1
    rec["random_sum_delta"] = float(rec.get("random_sum_delta", 0.0) or 0.0) + float(delta)
    if delta > 0:
        rec["random_wins"] = int(rec.get("random_wins", 0) or 0) + 1
    normalized = max(-1.0, min(1.0, float(delta) / float(v4.MAX_PORTFOLIO_SCORE)))
    comps = update_e_components(rec.get("random_e_components"), normalized, v4.E_LAMBDAS)
    rec["random_e_components"] = comps
    rec["random_e_value_raw"] = e_value_from_components(comps, v4.E_LAMBDAS)


def _grade_holdout(v4, out_dir: Path, latest_round: int, draw_date: str,
                   actual_set: set[int], verification: str, trusted: bool) -> None:
    registry_path = out_dir / "future_holdout_registry.json"
    state_path = out_dir / "future_holdout_state.json"
    registry = load_json(registry_path, {})
    state = load_json(state_path, {})
    if not registry or not state or int(registry.get("target_round", -1)) != int(latest_round):
        return
    graded = state.setdefault("graded_rounds", [])
    if latest_round in graded:
        return
    holdout_tickets = registry.get("holdout_tickets") or []
    champion_tickets = registry.get("champion_tickets") or []
    random_tickets = registry.get("random_reference_tickets") or []
    if not holdout_tickets or not champion_tickets or not random_tickets:
        state["status"] = "invalid_missing_prefrozen_reference"
        write_json(state_path, state)
        return

    hm = v4.score_tickets(holdout_tickets, actual_set)
    cm = v4.score_tickets(champion_tickets, actual_set)
    rm = v4.score_tickets(random_tickets, actual_set)
    dc = float(hm["score"] - cm["score"])
    dr = float(hm["score"] - rm["score"])
    state["all_draws"] = int(state.get("all_draws", 0) or 0) + 1
    if trusted:
        state["trusted_draws"] = int(state.get("trusted_draws", 0) or 0) + 1
        state["sum_delta_vs_champion"] = float(state.get("sum_delta_vs_champion", 0.0) or 0.0) + dc
        state["sum_delta_vs_random"] = float(state.get("sum_delta_vs_random", 0.0) or 0.0) + dr
        if dc > 0:
            state["wins_vs_champion"] = int(state.get("wins_vs_champion", 0) or 0) + 1
        if dr > 0:
            state["wins_vs_random"] = int(state.get("wins_vs_random", 0) or 0) + 1
        ndc = max(-1.0, min(1.0, dc / float(v4.MAX_PORTFOLIO_SCORE)))
        ndr = max(-1.0, min(1.0, dr / float(v4.MAX_PORTFOLIO_SCORE)))
        ccomp = update_e_components(state.get("champion_e_components"), ndc, v4.E_LAMBDAS)
        rcomp = update_e_components(state.get("random_e_components"), ndr, v4.E_LAMBDAS)
        state["champion_e_components"] = ccomp
        state["random_e_components"] = rcomp
        state["champion_e_value"] = e_value_from_components(ccomp, v4.E_LAMBDAS)
        state["random_e_value"] = e_value_from_components(rcomp, v4.E_LAMBDAS)
    graded.append(latest_round)
    state["last_graded_round"] = latest_round
    if int(state.get("trusted_draws", 0) or 0) >= int(state.get("horizon_trusted_draws", HOLDOUT_TRUSTED_DRAWS)):
        state["status"] = "complete"
    write_json(state_path, state)
    append_csv(out_dir / "future_holdout_results.csv", [{
        "round": latest_round,
        "draw_date": draw_date,
        "holdout_version": state.get("locked_candidate_version", ""),
        "champion_version": registry.get("champion_version", ""),
        "holdout_score": f"{hm['score']:.6f}",
        "champion_score": f"{cm['score']:.6f}",
        "random_score": f"{rm['score']:.6f}",
        "delta_vs_champion": f"{dc:.6f}",
        "delta_vs_random": f"{dr:.6f}",
        "holdout_max_hits": f"{hm['max_hits']:.0f}",
        "champion_max_hits": f"{cm['max_hits']:.0f}",
        "random_max_hits": f"{rm['max_hits']:.0f}",
        "trusted": str(bool(trusted)).lower(),
        "source_verification": verification,
        "frozen_at_jst": registry.get("frozen_at_jst", ""),
    }], HOLDOUT_FIELDS)


def _patched_grade_registry(v4, original, registry: Dict[str, object], latest_round: int,
                            draw_date: str, actual_set: set[int], verification: str,
                            trusted: bool, oos_state: Dict[str, object], result_path: Path) -> bool:
    graded = original(registry, latest_round, draw_date, actual_set, verification,
                      trusted, oos_state, result_path)
    if not graded:
        return False

    out_dir = result_path.parent
    block_index = int(registry.get("formal_block_index", current_block_index(out_dir)) or 1)
    weight = block_weight(block_index)
    required = required_raw_e_value(block_index)
    champion_version = str(registry.get("champion_version", ""))
    champion_tickets = registry.get("champion_tickets") or []
    random_tickets = registry.get("random_reference_tickets") or []
    random_valid = bool(random_tickets) and bool(registry.get("random_reference_frozen_at_jst"))
    champion_metrics = v4.score_tickets(champion_tickets, actual_set) if champion_tickets else None
    random_metrics = v4.score_tickets(random_tickets, actual_set) if random_valid else None
    evidence = oos_state.get("evidence") if isinstance(oos_state.get("evidence"), dict) else {}
    paired_rows: List[Dict[str, object]] = []

    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        candidate_version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        if not candidate_version or not tickets:
            continue
        rec = evidence.get(v4.e_key(candidate_version, champion_version), {}) if isinstance(evidence, dict) else {}
        if not isinstance(rec, dict):
            continue
        candidate_metrics = v4.score_tickets(tickets, actual_set)
        champion_raw = e_value_from_components(rec.get("e_components"), v4.E_LAMBDAS)
        rec["champion_e_value_raw"] = champion_raw
        rec["formal_block_index"] = block_index
        rec["family_alpha"] = FAMILY_ALPHA
        rec["family_weight"] = weight
        rec["required_raw_e_value"] = required
        rec["strict_random_valid"] = bool(random_valid)
        rec["strict_governance_version"] = VERSION

        random_delta = None
        if random_metrics is not None:
            random_delta = float(candidate_metrics["score"] - random_metrics["score"])
            _update_random_evidence(v4, rec, random_delta, trusted)
            random_raw = float(rec.get("random_e_value_raw", 1.0) or 1.0)
            adjusted = min(champion_raw, random_raw) * weight
        else:
            random_raw = 0.0
            adjusted = 0.0
        rec["random_e_value_raw"] = random_raw
        rec["family_adjusted_e_value"] = adjusted
        # v4's existing threshold remains 20; e_value now means globally adjusted,
        # intersection-union evidence against Champion AND pre-frozen Random.
        rec["e_value"] = adjusted
        rec["e_value_semantics"] = "family_adjusted_min_champion_random"
        if isinstance(evidence, dict):
            evidence[v4.e_key(candidate_version, champion_version)] = rec

        paired_rows.append({
            "round": latest_round,
            "draw_date": draw_date,
            "candidate_version": candidate_version,
            "champion_version": champion_version,
            "formal_block_index": block_index,
            "candidate_score": f"{candidate_metrics['score']:.6f}",
            "champion_score": f"{champion_metrics['score']:.6f}" if champion_metrics else "",
            "random_score": f"{random_metrics['score']:.6f}" if random_metrics else "",
            "delta_vs_champion": f"{candidate_metrics['score'] - champion_metrics['score']:.6f}" if champion_metrics else "",
            "delta_vs_random": f"{random_delta:.6f}" if random_delta is not None else "",
            "candidate_max_hits": f"{candidate_metrics['max_hits']:.0f}",
            "champion_max_hits": f"{champion_metrics['max_hits']:.0f}" if champion_metrics else "",
            "random_max_hits": f"{random_metrics['max_hits']:.0f}" if random_metrics else "",
            "champion_e_value_raw": f"{champion_raw:.8f}",
            "random_e_value_raw": f"{random_raw:.8f}",
            "family_weight": f"{weight:.10f}",
            "family_adjusted_e_value": f"{adjusted:.8f}",
            "required_raw_e_value": f"{required:.8f}",
            "trusted_for_promotion": str(bool(trusted)).lower(),
            "source_verification": verification,
            "random_reference_frozen_at_jst": registry.get("random_reference_frozen_at_jst", ""),
        })

    append_csv(out_dir / "paired_oos_results.csv", paired_rows, PAIRED_FIELDS)
    _grade_holdout(v4, out_dir, latest_round, draw_date, actual_set, verification, trusted)
    oos_state["strict_governance_version"] = VERSION
    oos_state["promotion_family_alpha"] = FAMILY_ALPHA
    return True


def strict_promotion_candidates(v4, oos_state: Dict[str, object], champion_version: str):
    evidence = oos_state.get("evidence")
    if not isinstance(evidence, dict):
        return []
    eligible = []
    for rec in evidence.values():
        if not isinstance(rec, dict) or rec.get("champion_version") != champion_version:
            continue
        draws = int(rec.get("trusted_draws", 0) or 0)
        random_draws = int(rec.get("random_trusted_draws", 0) or 0)
        if draws < v4.MIN_TRUSTED_OOS_DRAWS or random_draws < v4.MIN_TRUSTED_OOS_DRAWS:
            continue
        if not rec.get("strict_random_valid"):
            continue
        mean_champion = float(rec.get("sum_delta", 0.0) or 0.0) / max(1, draws)
        mean_random = float(rec.get("random_sum_delta", 0.0) or 0.0) / max(1, random_draws)
        win_champion = float(rec.get("wins", 0) or 0) / max(1, draws)
        win_random = float(rec.get("random_wins", 0) or 0) / max(1, random_draws)
        adjusted_e = float(rec.get("family_adjusted_e_value", rec.get("e_value", 0.0)) or 0.0)
        if (
            adjusted_e >= v4.E_VALUE_THRESHOLD
            and mean_champion >= v4.MIN_MEAN_SCORE_DELTA
            and mean_random >= v4.MIN_MEAN_SCORE_DELTA
            and win_champion >= v4.MIN_OOS_WIN_RATE
            and win_random >= v4.MIN_OOS_WIN_RATE
        ):
            rank = math.log(max(adjusted_e, 1.0)) + min(mean_champion, mean_random) + 0.25 * min(win_champion, win_random)
            eligible.append((rank, rec))
    return sorted(eligible, key=lambda x: x[0], reverse=True)


def _patched_promote_if_eligible(v4, original, *args, **kwargs):
    champion, promotion = original(*args, **kwargs)
    if not promotion:
        return champion, promotion
    # Positional signature: champion, champion_file, oos_state, ...
    champion_file = args[1] if len(args) > 1 else kwargs.get("champion_file")
    oos_state = args[2] if len(args) > 2 else kwargs.get("oos_state", {})
    candidate_version = str(promotion.get("to", ""))
    rec = None
    if isinstance(oos_state, dict):
        for item in (oos_state.get("evidence") or {}).values():
            if isinstance(item, dict) and item.get("candidate_version") == candidate_version:
                rec = item
                break
    if isinstance(rec, dict):
        draws = max(1, int(rec.get("random_trusted_draws", 0) or 0))
        extra = {
            "strict_governance_version": VERSION,
            "formal_block_index": int(rec.get("formal_block_index", 1) or 1),
            "family_alpha": FAMILY_ALPHA,
            "family_weight": float(rec.get("family_weight", 0.0) or 0.0),
            "required_raw_e_value": float(rec.get("required_raw_e_value", 0.0) or 0.0),
            "champion_e_value_raw": float(rec.get("champion_e_value_raw", 0.0) or 0.0),
            "random_e_value_raw": float(rec.get("random_e_value_raw", 0.0) or 0.0),
            "family_adjusted_e_value": float(rec.get("family_adjusted_e_value", 0.0) or 0.0),
            "random_mean_score_delta": float(rec.get("random_sum_delta", 0.0) or 0.0) / draws,
            "random_win_rate": float(rec.get("random_wins", 0) or 0) / draws,
            "random_reference": "pre_frozen_deterministic_uniform_5_ticket_portfolio",
        }
        promotion.update(extra)
        if champion_file:
            path = Path(champion_file)
            obj = load_json(path, {})
            evidence = obj.get("promotion_evidence")
            if isinstance(evidence, dict):
                evidence.update(extra)
                obj["promotion_evidence"] = evidence
                write_json(path, obj)
    return champion, promotion


def install(v4) -> None:
    if getattr(v4, "_strict_oos_governance_installed", False):
        return
    original_grade = v4.grade_registry
    original_freeze = v4.freeze_registry
    original_promote = v4.promote_if_eligible

    def freeze_wrapper(path, target_round, base_data_sha, champion, champion_eval,
                       shadow_configs, eval_by_version, x, min_train, pool_size,
                       source_verification):
        registry = original_freeze(
            path, target_round, base_data_sha, champion, champion_eval,
            shadow_configs, eval_by_version, x, min_train, pool_size,
            source_verification,
        )
        registry["random_reference_tickets"] = deterministic_random_tickets(v4, target_round)
        registry["random_reference_method"] = "deterministic_uniform_5_ticket_portfolio"
        registry["random_reference_seed_policy"] = "12000000 + target_round * 1009"
        registry["random_reference_frozen_at_jst"] = v4.now_jst()
        v4.write_json(path, registry)
        return registry

    def grade_wrapper(registry, latest_round, draw_date, actual_set, verification,
                      trusted, oos_state, result_path):
        return _patched_grade_registry(
            v4, original_grade, registry, latest_round, draw_date, actual_set,
            verification, trusted, oos_state, result_path,
        )

    def promotion_wrapper(oos_state, champion_version):
        return strict_promotion_candidates(v4, oos_state, champion_version)

    def promote_wrapper(*args, **kwargs):
        return _patched_promote_if_eligible(v4, original_promote, *args, **kwargs)

    v4.freeze_registry = freeze_wrapper
    v4.grade_registry = grade_wrapper
    v4.promotion_candidates = promotion_wrapper
    v4.promote_if_eligible = promote_wrapper
    v4._strict_oos_governance_installed = True


def _cli_context(argv: Optional[Sequence[str]] = None):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--shadow-registry", type=Path, default=Path("loto7_agent_output/shadow_registry.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--portfolio-backtest-pool", type=int, default=650)
    args, _ = ap.parse_known_args(list(argv) if argv is not None else sys.argv[1:])
    return args


def _latest_round(v4, csv_path: Path) -> Tuple[int, np.ndarray]:
    df = v4.read_csv_flexible(csv_path)
    x, clean = v4.make_history(df)
    text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else ""
    latest = v4.parse_round(text) or int(len(clean))
    return int(latest), x


def ensure_holdout_for_current_target(v4, args, latest_round: int, x: np.ndarray) -> bool:
    out_dir = args.out_dir
    registry = load_json(args.shadow_registry, {})
    if not registry:
        return False
    target_round = int(registry.get("target_round", -1))
    if target_round <= latest_round:
        return False

    state_path = out_dir / "future_holdout_state.json"
    holdout_registry_path = out_dir / "future_holdout_registry.json"
    state = load_json(state_path, {})
    if not state:
        formal = load_json(out_dir / "formal_challenger_state.json", {})
        cfg_obj = formal.get("candidate_config") if isinstance(formal.get("candidate_config"), dict) else None
        version = str(formal.get("candidate_version", ""))
        if not cfg_obj:
            candidates = [x for x in (registry.get("candidates") or []) if isinstance(x, dict)]
            first = candidates[0] if candidates else {}
            cfg_obj = first.get("config") if isinstance(first.get("config"), dict) else None
            version = str(first.get("version", ""))
        cfg = v4.cfg_from_obj(cfg_obj)
        if cfg is None or not version:
            return False
        state = {
            "version": "future-holdout-v1",
            "status": "active",
            "locked_candidate_version": version,
            "locked_config": cfg_obj,
            "locked_at_jst": v4.now_jst(),
            "start_target_round": target_round,
            "horizon_trusted_draws": HOLDOUT_TRUSTED_DRAWS,
            "all_draws": 0,
            "trusted_draws": 0,
            "sum_delta_vs_champion": 0.0,
            "sum_delta_vs_random": 0.0,
            "wins_vs_champion": 0,
            "wins_vs_random": 0,
            "champion_e_components": {str(l): 1.0 for l in v4.E_LAMBDAS},
            "random_e_components": {str(l): 1.0 for l in v4.E_LAMBDAS},
            "champion_e_value": 1.0,
            "random_e_value": 1.0,
            "graded_rounds": [],
        }
        write_json(state_path, state)

    if state.get("status") != "active":
        return False
    old_registry = load_json(holdout_registry_path, {})
    if int(old_registry.get("target_round", -1)) == target_round:
        return True
    cfg = v4.cfg_from_obj(state.get("locked_config"))
    if cfg is None:
        state["status"] = "invalid_locked_config"
        write_json(state_path, state)
        return False
    ev = v4.v3.evaluate_config(x, cfg, min_train=args.min_train, pool_size=args.portfolio_backtest_pool)
    holdout_tickets = v4.deterministic_tickets(ev, target_round, champion=False)
    random_tickets = registry.get("random_reference_tickets") or deterministic_random_tickets(v4, target_round)
    holdout_registry = {
        "version": "future-holdout-registry-v1",
        "target_round": target_round,
        "base_data_sha": registry.get("base_data_sha", ""),
        "frozen_at_jst": v4.now_jst(),
        "locked_candidate_version": state.get("locked_candidate_version", ""),
        "locked_config": state.get("locked_config", {}),
        "holdout_tickets": holdout_tickets,
        "champion_version": registry.get("champion_version", ""),
        "champion_tickets": registry.get("champion_tickets") or [],
        "random_reference_tickets": random_tickets,
        "random_reference_method": "same_prefrozen_uniform_reference_as_strict_oos",
    }
    write_json(holdout_registry_path, holdout_registry)
    return True


def bootstrap_before_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    args = _cli_context(argv)
    latest_round, x = _latest_round(v4, args.csv)
    sync_formal_metadata(args.out_dir)
    random_ready = ensure_random_reference(v4, args.shadow_registry, latest_round=latest_round)
    holdout_ready = ensure_holdout_for_current_target(v4, args, latest_round, x)
    return {
        "out_dir": args.out_dir,
        "latest_round": latest_round,
        "random_ready": random_ready,
        "holdout_ready": holdout_ready,
    }


def finalize_after_main(v4, formal_challenger_module, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    args = _cli_context(argv)
    formal = formal_challenger_module.enforce(args.out_dir)
    metadata = sync_formal_metadata(args.out_dir)
    latest_round, x = _latest_round(v4, args.csv)
    random_ready = ensure_random_reference(v4, args.shadow_registry, latest_round=latest_round)
    holdout_ready = ensure_holdout_for_current_target(v4, args, latest_round, x)
    return {
        "formal": formal,
        "metadata": metadata,
        "random_ready": random_ready,
        "holdout_ready": holdout_ready,
    }
