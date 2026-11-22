#!/usr/bin/env python3
"""Production ticket-layout policy for new targets, separate from Champion.

Legacy targets 702-704 use seeded uniform geometry. Unfrozen 705+ targets
use Champion-ranked top35 and the operator-selected ROI-cash v2 model.
This layout does not establish a predictive edge over a fair lottery.
Pre-existing freezes and strict Future-OOS evidence are not modified.

Never call from a research checkpoint or while drawing data is untrusted.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import asdict

import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path

from balanced_uniform_portfolio import disjoint_portfolio, validate_portfolio
from combination_agent35_core import AgentConfig, candidate_from_history
from production_disjoint35_policy import (
    VERSION, RANKED_VERSION, COMBINATION_VERSION, ROI_CASH_VERSION, MIN_TARGET_ROUND,
    RANKED_MIN_TARGET_ROUND, COMBINATION_MIN_TARGET_ROUND, ROI_CASH_MIN_TARGET_ROUND,
    publication_policy_for_target, issued_policy, validate_issued_rows,
)
from loto7_evolving_agent import walk_forward_evolve, final_score
import loto7_v2_runner as v2
from joint_set_v2_signal_oos_guard import validate_trusted_source
import loto7_v4_runner as v4
from loto7_evolving_agent import fingerprint_file

SEED_BASE = 10_000_000
SEED_MULTIPLIER = 1009
JST = timezone(timedelta(hours=9))


def production_window_guard(now: datetime) -> None:
    local = now.astimezone(JST)
    hour_min = local.hour * 100 + local.minute
    if local.weekday() != 4 or not (1300 <= hour_min < 2000):
        raise RuntimeError("refusing disjoint35 Production outside Friday 13:00-19:59 JST")


def verify_source(csv_path: Path, source_path: Path,
                  expected_latest_round: int) -> dict:
    """Require two-source trusted latest draw and exact current CSV SHA."""
    verified = validate_trusted_source(csv_path, source_path)
    if not verified.get("trusted") or verified.get("round") != expected_latest_round:
        raise RuntimeError("refusing geometry35 Production without two-source verification")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    provenance = source.get("verification_provenance") or {}
    canonical_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if provenance.get("draw_csv_sha256") != canonical_sha:
        raise RuntimeError("refusing geometry35 Production with stale CSV fingerprint")
    return verified


def ranked_portfolio_from_scores(scores: np.ndarray) -> tuple[list[tuple[int, ...]], list[int]]:
    """Choose all but the bottom two Champion-ranked numbers; group ranks by sevens.

    Equal scores are resolved by ascending numeric label. No random fallback.
    """
    try:
        q = np.asarray(scores, dtype=float)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("invalid Champion ranking scores") from exc
    if (q.shape != (37,) or not bool(np.all(np.isfinite(q)))
            or bool(np.any(q < 0)) or not math.isclose(float(q.sum()), 1.0,
                                                       rel_tol=0.0, abs_tol=1e-8)):
        raise ValueError("Champion ranking requires 37 finite normalized nonnegative scores")
    ranking = sorted(range(1, 38), key=lambda number: (-float(q[number - 1]), number))
    tickets = [
        tuple(sorted(ranking[start:start + 7]))
        for start in range(0, 35, 7)
    ]
    validate_portfolio(tickets)
    return tickets, ranking


def combination_layout_sha256(*, target_round: int, data_sha: str,
                               champion_version: str, ranking: list[int],
                               tickets: list[tuple[int, ...]], config: AgentConfig) -> str:
    payload = {
        "target_round": target_round, "data_sha256": data_sha,
        "champion_version": champion_version, "policy": COMBINATION_VERSION,
        "ranking": ranking, "tickets": [list(t) for t in tickets],
        "config": asdict(config),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def portfolio_for_target(target_round: int) -> list[tuple[int, ...]]:
    """Legacy seeded-uniform generator only; ranked Production uses another path."""
    if type(target_round) is not int or target_round < MIN_TARGET_ROUND:
        raise ValueError("cannot change an existing/frozen target before round 702")
    tickets = disjoint_portfolio(SEED_BASE + target_round * SEED_MULTIPLIER)
    validate_portfolio(tickets)
    return tickets


def render_ticket_csv(tickets: list[tuple[int, ...]]) -> str:
    validate_portfolio(tickets)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["ticket", "numbers", "sum", "odd_count"])
    for i, ticket in enumerate(tickets, 1):
        writer.writerow([i, " ".join(f"{n:02d}" for n in ticket),
                         sum(ticket), sum(n % 2 for n in ticket)])
    return "\ufeff" + stream.getvalue()


def prepare_new_production_outputs(
    *, csv_path: Path, out_dir: Path, champion_version: str,
    data_sha: str, latest_round: int, target_round: int,
    latest_draw_date: str, git_sha: str,
    source_path: Path, now: datetime | None = None,
    history: np.ndarray | None = None,
    champion_config: v2.ModelConfig | None = None,
    min_train: int = 100,
) -> dict:
    """Prepare only the canonical publisher's NEW 702+ freeze.

    This does not append the immutable Production ledger: its existing
    append_current_predictions and frozen-target check remain authoritative.
    """
    if type(latest_round) is not int or target_round != latest_round + 1:
        raise RuntimeError("invalid Production target sequence")
    if target_round < MIN_TARGET_ROUND:
        raise RuntimeError("round 701 and earlier must use existing publisher unchanged")
    production_window_guard(now or datetime.now(JST))
    if fingerprint_file(csv_path) != data_sha:
        raise RuntimeError("Production source data hash mismatch")
    verify_source(csv_path, source_path, latest_round)

    policy = publication_policy_for_target(target_round)
    ranking: list[int] | None = None
    q: np.ndarray | None = None
    ranked_extras: dict[str, object] = {}
    expert_weights: dict[str, float] = {}
    if policy in (RANKED_VERSION, COMBINATION_VERSION, ROI_CASH_VERSION):
        if (history is None or champion_config is None
                or champion_config.version() != champion_version):
            raise RuntimeError("ranked Production requires the exact approved Champion and history")
        # Learn from draws through latest_round only; the target is unobserved.
        bt = walk_forward_evolve(
            history, min_train=min_train, eta=champion_config.eta,
            decay=champion_config.decay,
            expert_uniform_mix=champion_config.expert_uniform_mix,
        )
        q = final_score(history, bt, uniform_mix=champion_config.final_uniform_mix)
        tickets, ranking = ranked_portfolio_from_scores(q)
        if policy == COMBINATION_VERSION:
            if len(history) != latest_round or len(history) < 100:
                raise RuntimeError("combination Production needs at least 100 contiguous prior draws")
            config = AgentConfig()
            tickets, combo_diag = candidate_from_history(history, ranking, config)
            ranked_extras.update({
                "production_combo_agent_version": COMBINATION_VERSION,
                "production_combo_config": asdict(config),
                "production_combo_training_rows": len(history),
                "production_combo_training_data_sha256": data_sha,
                "production_combo_swaps": combo_diag["swap_count"],
                "production_combo_training_objective_gain": combo_diag["training_objective_gain"],
                "production_combo_layout_sha256": combination_layout_sha256(
                    target_round=target_round, data_sha=data_sha,
                    champion_version=champion_version, ranking=ranking,
                    tickets=tickets, config=config,
                ),
            })
        if policy == ROI_CASH_VERSION:
            from production_roi_cash35_v2 import (
                ALGORITHM_VERSION, SELECTION_AUTHORITY, CashAgentConfig,
                candidate_from_canonical_rows, layout_sha256,
                training_arrays_from_canonical_rows,
            )
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                canonical_rows = list(csv.DictReader(stream))
            canonical_main, _, _ = training_arrays_from_canonical_rows(canonical_rows)
            if (len(history) != latest_round
                    or canonical_main.shape != history.shape
                    or not np.array_equal(canonical_main, history)):
                raise RuntimeError("ROI v2 source history and approved Champion history differ")
            roi_cfg = CashAgentConfig()
            tickets, roi_diag = candidate_from_canonical_rows(
                canonical_rows, ranking, roi_cfg
            )
            ranked_extras.update({
                "production_roi_cash_v2_algorithm_version": ALGORITHM_VERSION,
                "production_roi_cash_v2_config": asdict(roi_cfg),
                "production_roi_cash_v2_training_rows": len(history),
                "production_roi_cash_v2_training_data_sha256": data_sha,
                "production_roi_cash_v2_swaps": roi_diag["swaps"],
                "production_roi_cash_v2_training_cash_objective_gain_yen_per_draw":
                    roi_diag["training_cash_objective_gain_yen_per_draw"],
                "production_roi_cash_v2_layout_sha256": layout_sha256(
                    target_round=target_round, data_sha=data_sha,
                    champion_version=champion_version, ranking=ranking,
                    tickets=tickets, config=roi_cfg,
                ),
                "production_roi_cash_v2_selection_authority": SELECTION_AUTHORITY,
                "production_roi_cash_v2_target_outcome_used": False,
            })
        expert_weights = {
            key: float(bt.final_weights[i]) for i, key in enumerate(bt.keys)
        }
        rank_payload = json.dumps({
            "data_sha256": data_sha,
            "champion_version": champion_version,
            "ranking": ranking,
            "scores_binary64": [format(float(score), ".17g") for score in q],
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ranked_extras.update({
            "production_ranking_method": "approved_champion_walk_forward_final_score_v1",
            "production_rank_order": ranking,
            "production_rank_top35": ranking[:35],
            "production_rank_excluded_numbers": ranking[35:],
            "production_rank_sha256": hashlib.sha256(rank_payload.encode("utf-8")).hexdigest(),
            "production_rank_base_data_sha256": data_sha,
            "production_rank_model_version": champion_version,
        })
    else:
        tickets = portfolio_for_target(target_round)
    text = render_ticket_csv(tickets)
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    model_version = f"{champion_version}+{policy}"
    state = {
        "agent_version": v4.AGENT_VERSION,
        "model_version": model_version,
        "signal_champion_version": champion_version,
        "production_ticket_policy_version": policy,
        "production_ticket_policy_role": (
            "champion_ranked_top35_with_roi_cash_v2_operator_override_no_skill_claim"
            if policy == ROI_CASH_VERSION else
            "champion_ranked_top35_with_pairwise_combination_ai_no_skill_claim"
            if policy == COMBINATION_VERSION else
            "champion_ai_ranked_top35_geometry_not_signal_promotion"
            if policy == RANKED_VERSION else "ticket_geometry_only_not_signal_promotion"
        ),
        "data_sha256": data_sha,
        "latest_round": f"第{latest_round}回",
        "latest_draw_date": latest_draw_date,
        "target_round": f"第{target_round}回",
        "seed": SEED_BASE + target_round * SEED_MULTIPLIER if policy == VERSION else None,
        "git_sha": git_sha,
        "production_promotion_method": (
            "explicit_operator_policy_switch_without_proven_future_roi"
            if policy == ROI_CASH_VERSION else "future_oos_only"
        ),
        "promotion_this_run": None,
        "ticket_count": 5,
        "covered_distinct_numbers": 35,
        "ticket_layout_sha256": text_sha,
        "expert_weights": expert_weights,
        **ranked_extras,
        "no_lottery_signal_skill_claim": True,
        "first_prize_odds_unchanged": True,
        "production_roi_primary_kpi": "public_historical_payout_yen_divided_by_1500_yen_per_round",
        "production_roi_prediction_skill_confirmed": False,
        "production_expected_future_roi": None,
        "production_purchase_automation": False,
        "production_roi_governance": "prospective_oos_required_no_purchase_authorization",
        "production_reference_cost_yen_for_five_tickets": 1500,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    # The generated candidate view is *not* the canonical frozen ledger.
    # weekly_production_prediction.freeze writes that ledger only once.
    (out_dir / "candidate_tickets.csv").write_text(text, encoding="utf-8")
    if ranking is not None and q is not None:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["rank", "number", "relative_score", "score_index_vs_uniform"])
        for i, number in enumerate(ranking, 1):
            score = float(q[number - 1])
            writer.writerow([i, number, format(score, ".17g"),
                             format(score * 37, ".17g")])
        (out_dir / "prediction_ranking.csv").write_text(
            "\ufeff" + stream.getvalue(), encoding="utf-8"
        )
    v4.write_json(out_dir / "agent_state.json", state)
    return state


def verify_canonical_publication(out_dir: Path) -> dict:
    """Check the immutable issued ledger before commit, display or DB sync.

    This command is read-only. Historical 701 and earlier stay exactly as
    issued; every newly issued target from 702 onward must be disjoint35.
    """
    import audit_ledger as ledger  # lazy to keep ledger's write guard importable

    state_path = out_dir / "weekly_production_prediction_state.json"
    if not state_path.is_file():
        raise ValueError("missing canonical Production publication state")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    target = v4.parse_round(state.get("target_round"))
    if state.get("published") is not True or target is None:
        raise ValueError("cannot verify an unpublished Production target")
    active = [
        r for r in ledger.active_prediction_rows(
            out_dir / "predictions.csv",
            out_dir / "prediction_corrections.csv",
        )
        if ledger.rno(r.get("target_round", "")) == target
    ]
    if len(active) != 5:
        raise ValueError("canonical Production must contain exactly five active tickets")
    if target >= MIN_TARGET_ROUND:
        validate_issued_rows(active, target)
        frozen_policy = issued_policy(active, target)
        if state.get("ticket_policy") != frozen_policy:
            raise ValueError("canonical Production ticket policy does not match frozen ledger")
        if len({r.get("model_version") for r in active}) != 1:
            raise ValueError("mixed model policy in canonical Production")
        if active[0]["model_version"] != state.get("model_version"):
            raise ValueError("canonical Production state and rows disagree on policy")
    return {
        "target_round": target,
        "status": "disjoint35_pass" if target >= MIN_TARGET_ROUND else "historical_immutable",
        "covered_distinct_numbers": 35 if target >= MIN_TARGET_ROUND else None,
        "checked_active_tickets": len(active),
        "production_changed": False,
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Read-only canonical Production geometry gate")
    ap.add_argument("--verify-canonical", action="store_true", required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    args = ap.parse_args()
    print(json.dumps(verify_canonical_publication(args.out_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
