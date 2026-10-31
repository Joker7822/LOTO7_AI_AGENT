#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

import strict_oos_governance as strict


def load_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def comparator_summary(
    draws: int,
    sum_delta: float,
    wins: int,
    e_value: float,
    policy: Dict[str, object],
) -> Dict[str, object]:
    draws = int(draws)
    mean_delta = float(sum_delta) / draws if draws else 0.0
    win_rate = float(wins) / draws if draws else 0.0
    min_delta = float(policy.get("minimum_mean_score_delta", 0.05))
    min_win = float(policy.get("minimum_win_rate", 0.55))
    min_e = float(policy.get("minimum_e_value", 20.0))
    return {
        "trusted_draws": draws,
        "mean_score_delta": mean_delta,
        "win_rate": win_rate,
        "e_value": float(e_value),
        "passes_mean_delta": mean_delta >= min_delta,
        "passes_win_rate": win_rate >= min_win,
        "passes_e_value": float(e_value) >= min_e,
        "passes_all": (
            draws > 0
            and mean_delta >= min_delta
            and win_rate >= min_win
            and float(e_value) >= min_e
        ),
    }


def build_report(state: Dict[str, object]) -> Tuple[Dict[str, object], bool]:
    policy = state.get("confirmation_policy")
    policy = policy if isinstance(policy, dict) else {}
    horizon = int(state.get("horizon_trusted_draws", 0) or 0)
    trusted = int(state.get("trusted_draws", 0) or 0)
    matched_trusted = int(state.get("matched_ensemble_trusted_draws", 0) or 0)

    stored_lock = str(state.get("protocol_lock_sha256", "") or "")
    observed_lock = strict.holdout_lock_sha256(state) if state else ""
    lock_ok = bool(stored_lock) and stored_lock == observed_lock

    random = comparator_summary(
        trusted,
        float(state.get("sum_delta_vs_random", 0.0) or 0.0),
        int(state.get("wins_vs_random", 0) or 0),
        float(state.get("random_e_value", 1.0) or 1.0),
        policy,
    )
    matched = comparator_summary(
        matched_trusted,
        float(state.get("sum_delta_vs_matched_ensemble", 0.0) or 0.0),
        int(state.get("wins_vs_matched_ensemble", 0) or 0),
        float(state.get("matched_ensemble_e_value", 1.0) or 1.0),
        policy,
    )

    registration_draws = state.get("confirmation_policy_registered_at_trusted_draws")
    registration_known = type(registration_draws) is int and registration_draws >= 0
    registration_pre_outcome = registration_known and registration_draws == 0

    full_horizon = (
        horizon > 0
        and trusted >= horizon
        and matched_trusted >= horizon
        and int(state.get("all_draws", -1)) == len(state.get("graded_rounds", []) or [])
        and int(state.get("all_draws", -1)) == len(state.get("matched_ensemble_graded_rounds", []) or [])
        and trusted <= int(state.get("all_draws", -1))
        and matched_trusted <= int(state.get("all_draws", -1))
    )

    if not lock_ok:
        claim_status = "invalid_protocol_lock"
        confirmed = False
    elif not full_horizon:
        claim_status = "not_confirmed_holdout_incomplete"
        confirmed = False
    elif not registration_pre_outcome:
        # Preserve the original locked holdout and every graded result.
        # A confirmation rule recorded after outcomes were seen can be
        # reported diagnostically, but cannot become a preregistered claim.
        claim_status = "not_confirmed_policy_registration_not_pre_outcome"
        confirmed = False
    elif random["passes_all"] and matched["passes_all"]:
        claim_status = "confirmed_operational_future_oos_edge"
        confirmed = True
    else:
        claim_status = "not_confirmed_criteria_not_met"
        confirmed = False

    report = {
        "version": "future-holdout-evidence-report-v1",
        "claim_status": claim_status,
        "confirmed": confirmed,
        "locked_candidate_version": state.get("locked_candidate_version", ""),
        "holdout_status": state.get("status", ""),
        "progress": {
            "trusted_draws": trusted,
            "matched_ensemble_trusted_draws": matched_trusted,
            "horizon_trusted_draws": horizon,
            "full_horizon_complete": full_horizon,
            "graded_rounds": state.get("graded_rounds", []),
            "matched_ensemble_graded_rounds": state.get("matched_ensemble_graded_rounds", []),
        },
        "protocol_lock": {
            "version": state.get("protocol_lock_version", ""),
            "stored_sha256": stored_lock,
            "observed_sha256": observed_lock,
            "verified": lock_ok,
        },
        "confirmation_policy": policy,
        "confirmation_policy_registered_at_trusted_draws": registration_draws,
        "confirmation_policy_timing": {
            "registration_recorded": registration_known,
            "registered_before_first_trusted_draw": registration_pre_outcome,
            "eligible_for_confirmatory_claim": registration_pre_outcome,
            "note": (
                "Registration of the final confirmation policy after the first "
                "trusted outcome does not constitute strict preregistration. "
                "The original 26-draw evidence remains diagnostic and is never reset."
            ),
        },
        "comparators": {
            "uniform_random": random,
            "matched_ensemble32": matched,
        },
        "claim_rule": (
            "No confirmation before the full fixed holdout horizon. At completion, both "
            "Uniform Random and the prefrozen 32-member geometry-matched ensemble must "
            "meet every inherited Production threshold. A confirmatory claim also "
            "requires the confirmation policy to have been locked before the first "
            "trusted outcome."
        ),
        "statistical_scope": (
            "This is an operational prospective confirmation rule. It does not by itself "
            "constitute a mathematical proof that the portfolio e-process is valid under "
            "every possible null model."
        ),
    }
    return report, lock_ok


def render_markdown(report: Dict[str, object]) -> str:
    p = report["progress"]
    comps = report["comparators"]
    rnd = comps["uniform_random"]
    mat = comps["matched_ensemble32"]
    lines = [
        "# Fixed Future OOS Evidence",
        "",
        f"- Claim status: **{report['claim_status']}**",
        f"- Candidate: **{report['locked_candidate_version']}**",
        (
            "- Holdout progress: "
            f"**{p['trusted_draws']}/{p['horizon_trusted_draws']} trusted** "
            f"(Matched Ensemble {p['matched_ensemble_trusted_draws']}/{p['horizon_trusted_draws']})"
        ),
        f"- Protocol lock verified: **{report['protocol_lock']['verified']}**",
        (
            "- Confirmation policy registered before first trusted draw: "
            f"**{report['confirmation_policy_timing']['registered_before_first_trusted_draw']}** "
            f"(at trusted draw count {report['confirmation_policy_registered_at_trusted_draws']})"
        ),
        "",
        "## Uniform Random",
        f"- Mean score delta: **{rnd['mean_score_delta']:+.6f}**",
        f"- Win rate: **{rnd['win_rate']:.2%}**",
        f"- e-value telemetry: **{rnd['e_value']:.6f}**",
        f"- Passes all locked thresholds: **{rnd['passes_all']}**",
        "",
        "## Matched Ensemble (32)",
        f"- Mean score delta: **{mat['mean_score_delta']:+.6f}**",
        f"- Win rate: **{mat['win_rate']:.2%}**",
        f"- e-value telemetry: **{mat['e_value']:.6f}**",
        f"- Passes all locked thresholds: **{mat['passes_all']}**",
        "",
        "## Claim rule",
        report["claim_rule"],
        "",
        "## Statistical scope",
        report["statistical_scope"],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize fixed Future OOS evidence without early claiming.")
    ap.add_argument(
        "--state",
        type=Path,
        default=Path("loto7_agent_output/future_holdout_state.json"),
    )
    ap.add_argument(
        "--json-output",
        type=Path,
        default=Path("loto7_agent_output/future_holdout_evidence.json"),
    )
    ap.add_argument(
        "--md-output",
        type=Path,
        default=Path("loto7_agent_output/future_holdout_evidence.md"),
    )
    ap.add_argument(
        "--status",
        type=Path,
        help="Optional STATUS.md to append a compact evidence-claim section to.",
    )
    args = ap.parse_args()

    state = load_json(args.state)
    if not state:
        raise SystemExit("future holdout state is missing")

    report, lock_ok = build_report(state)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    if args.status:
        progress = report["progress"]
        random = report["comparators"]["uniform_random"]
        matched = report["comparators"]["matched_ensemble32"]
        with args.status.open("a", encoding="utf-8") as fh:
            fh.write("\n## Fixed Future OOS Evidence Claim\n\n")
            fh.write(f"- Claim status: **{report['claim_status']}**\n")
            fh.write(
                f"- 進捗: **{progress['trusted_draws']}/{progress['horizon_trusted_draws']} trusted** "
                f"/ Matched **{progress['matched_ensemble_trusted_draws']}/{progress['horizon_trusted_draws']}**\n"
            )
            fh.write(f"- Protocol lock verified: **{report['protocol_lock']['verified']}**\n")
            fh.write(
                "- Confirmation policy preregistered before first outcome: "
                f"**{report['confirmation_policy_timing']['registered_before_first_trusted_draw']}**\n"
            )
            fh.write(
                f"- vs Random: mean delta **{random['mean_score_delta']:+.4f}** / "
                f"win **{random['win_rate']:.1%}** / e **{random['e_value']:.4f}**\n"
            )
            fh.write(
                f"- vs Matched Ensemble(32): mean delta **{matched['mean_score_delta']:+.4f}** / "
                f"win **{matched['win_rate']:.1%}** / e **{matched['e_value']:.4f}**\n"
            )
            fh.write("- 26/26完了前は confirmed を出さない。\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if lock_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
