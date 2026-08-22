#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import loto7_v2_runner as v2


def load_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def config_for_version(evaluation: Dict[str, object], version: str) -> Optional[Dict[str, object]]:
    for item in evaluation.get("evaluations", []) or []:
        if isinstance(item, dict) and str(item.get("version", "")) == version:
            cfg = item.get("config")
            if isinstance(cfg, dict):
                return dict(cfg)
    return None


def bootstrap(evaluation: Dict[str, object], champion_path: Path) -> Dict[str, object]:
    parent_version = str(evaluation.get("research_parent", ""))
    parent_config = config_for_version(evaluation, parent_version) if parent_version else None
    if parent_config is None:
        champion = v2.load_champion(champion_path)
        parent_version = champion.version()
        parent_config = dict(champion.__dict__)
    return {
        "report_version": "research-feedback-v1",
        "accepted_parent_version": parent_version,
        "accepted_parent_config": parent_config,
        "last_candidate_version": "",
        "data_sha256": "",
        "replay_count": 0,
        "accept_count": 0,
        "bootstrap_source": "v4_research_evaluation.research_parent",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply formal OOS challenger governance, seed replay state, and run research optimization")
    ap.add_argument("--evaluation", type=Path, default=Path("loto7_agent_output/v4_research_evaluation.json"))
    ap.add_argument("--champion-file", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    args = ap.parse_args()

    # This hook runs immediately after loto7_v4_runner.py. Reduce the newly frozen
    # shadow registry to exactly one promotion-eligible Formal Challenger before
    # the next draw can be graded. Research-only shadow candidates are archived.
    from formal_challenger import enforce

    formal = enforce(args.feedback_state.parent)
    if formal.get("enforced"):
        print(
            f"[FORMAL-HOOK] challenger={formal.get('formal_challenger_version')} "
            f"trusted={formal.get('trusted_draws')}/{formal.get('minimum_trusted_draws')}"
        )

    old = load_json(args.feedback_state)
    if isinstance(old.get("accepted_parent_config"), dict):
        print(f"[REPLAY-BOOTSTRAP] existing parent retained: {old.get('accepted_parent_version','')}")
    else:
        evaluation = load_json(args.evaluation)
        if not evaluation:
            raise SystemExit("v4_research_evaluation.json is missing or invalid")
        state = bootstrap(evaluation, args.champion_file)
        args.feedback_state.parent.mkdir(parents=True, exist_ok=True)
        args.feedback_state.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REPLAY-BOOTSTRAP] seeded parent={state['accepted_parent_version']}")

    from feedback_optimizer import optimize_once

    optimize_once(
        evaluation_path=args.evaluation,
        feedback_state_path=args.feedback_state,
        out_dir=args.feedback_state.parent,
        research_state_path=args.feedback_state.parent / "v4_research_state.json",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
