#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

import loto7_v4_runner as v4

JST = dt.timezone(dt.timedelta(hours=9))
STATE_VERSION = "formal-challenger-v1"
MIN_BLOCK_TRUSTED_DRAWS = 8


def now_jst() -> str:
    return dt.datetime.now(JST).isoformat(timespec="seconds")


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


def append_jsonl(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def candidate_version(item: object) -> str:
    return str(item.get("version", "")) if isinstance(item, dict) else ""


def candidate_map(registry: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        if version:
            out[version] = copy.deepcopy(item)
    return out


def choose_candidate(registry: Dict[str, object], exclude: Sequence[str] = ()) -> Optional[Dict[str, object]]:
    excluded: Set[str] = set(str(x) for x in exclude)
    candidates: List[Dict[str, object]] = []
    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        if not version or version in excluded or not item.get("tickets"):
            continue
        candidates.append(copy.deepcopy(item))
    if not candidates:
        return None
    candidates.sort(
        key=lambda x: (
            float(x.get("research_score", -1e18)),
            str(x.get("version", "")),
        ),
        reverse=True,
    )
    return candidates[0]


def evidence_for(oos_state: Dict[str, object], candidate: str, champion: str) -> Dict[str, object]:
    evidence = oos_state.get("evidence")
    if not isinstance(evidence, dict):
        return {}
    rec = evidence.get(v4.e_key(candidate, champion), {})
    return copy.deepcopy(rec) if isinstance(rec, dict) else {}


def clear_nonformal_evidence(oos_state: Dict[str, object], candidate: str, champion: str,
                             reset_formal: bool) -> None:
    evidence = oos_state.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    keep_key = v4.e_key(candidate, champion)
    if reset_formal:
        oos_state["evidence"] = {}
    else:
        keep = evidence.get(keep_key)
        oos_state["evidence"] = {keep_key: keep} if isinstance(keep, dict) else {}
    oos_state["formal_challenger_version"] = candidate
    oos_state["formal_champion_version"] = champion
    oos_state["promotion_evidence_policy"] = "single_formal_challenger_only"


def archive_research_registry(registry: Dict[str, object], archive_path: Path) -> None:
    candidates = [x for x in (registry.get("candidates") or []) if isinstance(x, dict)]
    old = load_json(archive_path, {})
    old_target = int(old.get("target_round", -1)) if old else -1
    target = int(registry.get("target_round", -1))
    # Preserve the richer pre-filter set for the current target; a reduced one-item
    # formal registry must not overwrite it on later same-target iterations.
    if len(candidates) <= 1 and old_target == target:
        return
    archived = copy.deepcopy(registry)
    archived["registry_role"] = "research_shadow_archive_only"
    archived["promotion_eligible"] = False
    archived["archived_at_jst"] = now_jst()
    write_json(archive_path, archived)


def block_id(champion: str, candidate: str, start_round: int) -> str:
    raw = f"{champion}|{candidate}|{start_round}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def make_state(champion: str, candidate: Dict[str, object], target_round: int,
               selection_basis: str) -> Dict[str, object]:
    version = str(candidate.get("version", ""))
    return {
        "state_version": STATE_VERSION,
        "active": True,
        "block_id": block_id(champion, version, target_round),
        "champion_version": champion,
        "candidate_version": version,
        "candidate_config": copy.deepcopy(candidate.get("config") or {}),
        "block_start_target_round": int(target_round),
        "minimum_trusted_draws": MIN_BLOCK_TRUSTED_DRAWS,
        "selected_at_jst": now_jst(),
        "selection_basis": selection_basis,
        "trusted_draws_so_far": 0,
        "last_observed_round": None,
        "status": "active",
    }


def archive_block(history_path: Path, state: Dict[str, object], evidence: Dict[str, object],
                  outcome: str, current_target_round: int) -> None:
    if not state:
        return
    record = {
        **copy.deepcopy(state),
        "closed_at_jst": now_jst(),
        "closed_before_target_round": int(current_target_round),
        "outcome": outcome,
        "final_evidence": copy.deepcopy(evidence),
    }
    append_jsonl(history_path, record)


def enforce(out_dir: Path = Path("loto7_agent_output")) -> Dict[str, object]:
    registry_path = out_dir / "shadow_registry.json"
    oos_path = out_dir / "oos_candidate_state.json"
    state_path = out_dir / "formal_challenger_state.json"
    history_path = out_dir / "formal_challenger_history.jsonl"
    research_archive_path = out_dir / "research_shadow_registry.json"
    events_path = out_dir / "run_events.json"

    registry = load_json(registry_path, {})
    if not registry or not registry.get("candidates"):
        return {"enforced": False, "reason": "shadow registry not ready"}
    oos_state = load_json(oos_path, {"agent_version": v4.AGENT_VERSION, "graded_rounds": [], "evidence": {}})
    old_state = load_json(state_path, {})
    archive_research_registry(registry, research_archive_path)

    champion = str(registry.get("champion_version", ""))
    target_round = int(registry.get("target_round", -1))
    if not champion or target_round < 0:
        return {"enforced": False, "reason": "invalid shadow registry"}

    all_candidates = candidate_map(registry)
    changed = False
    rotated = False
    reset_evidence = False
    state = old_state
    selected: Optional[Dict[str, object]] = None

    old_candidate = str(old_state.get("candidate_version", ""))
    old_champion = str(old_state.get("champion_version", ""))
    old_evidence = evidence_for(oos_state, old_candidate, old_champion) if old_candidate and old_champion else {}
    old_trusted = int(old_evidence.get("trusted_draws", old_state.get("trusted_draws_so_far", 0)) or 0)

    if not old_state or not old_candidate:
        selected = choose_candidate(registry)
        if selected is None:
            return {"enforced": False, "reason": "no eligible formal challenger"}
        state = make_state(champion, selected, target_round, "highest_frozen_research_score")
        changed = True
        reset_evidence = True
    elif old_champion != champion:
        archive_block(history_path, old_state, old_evidence, "champion_changed_or_promoted", target_round)
        selected = choose_candidate(registry)
        if selected is None:
            return {"enforced": False, "reason": "no challenger after champion change"}
        state = make_state(champion, selected, target_round, "new_champion_highest_frozen_research_score")
        changed = True
        rotated = True
        reset_evidence = True
    elif old_trusted >= MIN_BLOCK_TRUSTED_DRAWS:
        archive_block(history_path, old_state, old_evidence, "block_completed_without_promotion", target_round)
        selected = choose_candidate(registry, exclude=[old_candidate])
        if selected is None:
            selected = all_candidates.get(old_candidate)
        if selected is None:
            return {"enforced": False, "reason": "completed block but no next challenger"}
        state = make_state(champion, selected, target_round, "next_block_highest_frozen_research_score")
        changed = True
        rotated = str(selected.get("version")) != old_candidate
        reset_evidence = True
    else:
        selected = all_candidates.get(old_candidate)
        if selected is None:
            # v4 is expected to preserve the previous formal version. If it did not,
            # rotate explicitly rather than silently evaluating a different candidate.
            archive_block(history_path, old_state, old_evidence, "candidate_missing_from_new_registry", target_round)
            selected = choose_candidate(registry, exclude=[old_candidate]) or choose_candidate(registry)
            if selected is None:
                return {"enforced": False, "reason": "active challenger missing and no replacement"}
            state = make_state(champion, selected, target_round, "replacement_after_missing_candidate")
            changed = True
            rotated = True
            reset_evidence = True
        else:
            state = copy.deepcopy(old_state)
            state["trusted_draws_so_far"] = old_trusted
            state["last_observed_round"] = old_evidence.get("last_round")
            state["status"] = "active"

    assert selected is not None
    formal_version = str(selected.get("version", ""))
    selected = copy.deepcopy(selected)
    selected["role"] = "formal_challenger"
    selected["promotion_eligible"] = True

    clear_nonformal_evidence(oos_state, formal_version, champion, reset_formal=reset_evidence)
    if not reset_evidence:
        active_evidence = evidence_for(oos_state, formal_version, champion)
        state["trusted_draws_so_far"] = int(active_evidence.get("trusted_draws", 0) or 0)
        state["last_observed_round"] = active_evidence.get("last_round")

    registry["candidates"] = [selected]
    registry["formal_challenger_version"] = formal_version
    registry["formal_block_id"] = state.get("block_id")
    registry["formal_block_start_round"] = state.get("block_start_target_round")
    registry["formal_block_minimum_trusted_draws"] = MIN_BLOCK_TRUSTED_DRAWS
    registry["promotion_candidate_count"] = 1
    registry["research_shadow_archive"] = research_archive_path.name

    write_json(registry_path, registry)
    write_json(oos_path, oos_state)
    write_json(state_path, state)

    if changed:
        events = load_json(events_path, {})
        events["formal_challenger_changed"] = True
        events["formal_challenger_rotated"] = bool(rotated)
        events["formal_challenger_version"] = formal_version
        events["force_checkpoint"] = True
        write_json(events_path, events)

    result = {
        "enforced": True,
        "changed": changed,
        "rotated": rotated,
        "champion_version": champion,
        "formal_challenger_version": formal_version,
        "target_round": target_round,
        "trusted_draws": int(state.get("trusted_draws_so_far", 0) or 0),
        "minimum_trusted_draws": MIN_BLOCK_TRUSTED_DRAWS,
        "promotion_candidate_count": 1,
    }
    print(
        f"[FORMAL-CHALLENGER] target={target_round} candidate={formal_version} "
        f"trusted={result['trusted_draws']}/{MIN_BLOCK_TRUSTED_DRAWS} changed={changed}"
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Keep exactly one formal Future-OOS challenger locked for a trusted-draw block")
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    args = ap.parse_args()
    enforce(args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
