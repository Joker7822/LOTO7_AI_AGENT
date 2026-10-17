#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def state_identity(state: Mapping[str, object]) -> Dict[str, object]:
    return {str(k): v for k, v in state.items() if k != "worlds"}


def assigned_world_indices(
    target_worlds: int,
    completed_worlds: Iterable[int],
    shard_index: int,
    shard_count: int,
) -> List[int]:
    if shard_count <= 0:
        raise ValueError("shard_count must be positive")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must satisfy 0 <= shard_index < shard_count")
    completed = {int(x) for x in completed_worlds}
    return [
        i for i in range(1, int(target_worlds) + 1)
        if i not in completed and (i - 1) % int(shard_count) == int(shard_index)
    ]


def merge_world_records(
    existing: Sequence[Mapping[str, object]],
    fragments: Sequence[Sequence[Mapping[str, object]]],
    target_worlds: int,
) -> List[Dict[str, object]]:
    by_world: Dict[int, Dict[str, object]] = {}
    for record in list(existing) + [r for fragment in fragments for r in fragment]:
        world = int(record["world"])
        if world < 1 or world > int(target_worlds):
            raise ValueError(f"world index out of range: {world}")
        normalized = dict(record)
        prior = by_world.get(world)
        if prior is not None and prior != normalized:
            raise ValueError(f"conflicting results for world {world}")
        by_world[world] = normalized
    return [by_world[i] for i in sorted(by_world)]


def _model_context(model: str):
    if model == "v1":
        import joint_set_null_calibration as nullmod
        import joint_set_research as jsr
        from joint_set_model import candidate_configs
        return nullmod, jsr, candidate_configs
    if model == "v2":
        import joint_set_v2_null_calibration as nullmod
        import joint_set_v2_research as jsr
        from joint_set_v2_model import candidate_configs
        return nullmod, jsr, candidate_configs
    raise ValueError(f"unknown model: {model}")


def _load_compatible_state(
    model: str,
    csv_path: Path,
    out_dir: Path,
    metadata_path: Path,
    min_train: int,
    last_n: int,
    selection_window: int,
    validation_scenarios: int,
    validation_candidates: int,
    target_worlds: int,
    cutoff_hour_jst: int,
):
    import precision_random_baseline as prb
    from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

    nullmod, jsr, candidate_configs = _model_context(model)
    df = read_csv_flexible(csv_path)
    x_real, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    if model == "v1":
        metadata_design, _, _ = jsr.prepare_metadata(clean, metadata_path, cutoff_hour_jst)
        metadata_sha = jsr.file_sha(metadata_path)
        state_path = out_dir / "joint_set_null_calibration_state.json"
        state = read_json(state_path)
        compatible = nullmod.compatible_state(
            state, data_sha, metadata_sha, min_train, last_n, selection_window,
            validation_scenarios, validation_candidates, target_worlds,
        )
    else:
        metadata_design = None
        metadata_sha = None
        state_path = out_dir / "joint_set_v2_null_calibration_state.json"
        state = read_json(state_path)
        compatible = nullmod.compatible_state(
            state, data_sha, min_train, last_n, selection_window,
            validation_scenarios, validation_candidates, target_worlds,
        )
    if not compatible:
        raise RuntimeError(
            f"{model} null state is not compatible with current data/config; run prepare first"
        )
    random_summary = prb.ensure(csv_path, out_dir, min_train=min_train, reps=4096)
    random_score = float(random_summary["windows"]["full"]["random_score"])
    if int(state.get("predeclared_config_count", -1)) != len(candidate_configs()):
        raise RuntimeError(f"{model} config family changed after state preparation")
    return nullmod, x_real, metadata_design, random_score, state, state_path, data_sha, metadata_sha


def run_worker(
    model: str,
    csv_path: Path,
    out_dir: Path,
    metadata_path: Path,
    min_train: int,
    last_n: int,
    selection_window: int,
    validation_scenarios: int,
    validation_candidates: int,
    target_worlds: int,
    cutoff_hour_jst: int,
    shard_index: int,
    shard_count: int,
    output: Path,
) -> Dict[str, object]:
    nullmod, x_real, metadata_design, random_score, state, _, data_sha, metadata_sha = _load_compatible_state(
        model, csv_path, out_dir, metadata_path, min_train, last_n, selection_window,
        validation_scenarios, validation_candidates, target_worlds, cutoff_hour_jst,
    )
    completed = [int(w["world"]) for w in state.get("worlds", []) if isinstance(w, dict)]
    indices = assigned_world_indices(target_worlds, completed, shard_index, shard_count)
    worlds: List[Dict[str, object]] = []
    for world_index in indices:
        seed = nullmod.world_seed(data_sha, world_index)
        x_null = nullmod.synthetic_fair_world(len(x_real), seed)
        if model == "v1":
            result = nullmod.run_world(
                x_null, metadata_design, min_train, last_n, selection_window,
                validation_scenarios, validation_candidates, random_score, seed,
            )
        else:
            result = nullmod.run_world(
                x_null, min_train, last_n, selection_window,
                validation_scenarios, validation_candidates, random_score, seed,
            )
        worlds.append({"world": world_index, "seed": seed, **result})
    fragment: Dict[str, object] = {
        "model": model,
        "state_identity": state_identity(state),
        "data_sha256": data_sha,
        "metadata_sha256": metadata_sha,
        "shard_index": int(shard_index),
        "shard_count": int(shard_count),
        "worlds": worlds,
    }
    write_json(output, fragment)
    return fragment


def merge_fragments(
    model: str,
    out_dir: Path,
    fragments_dir: Path,
) -> Dict[str, object]:
    nullmod, _, _ = _model_context(model)
    if model == "v1":
        state_path = out_dir / "joint_set_null_calibration_state.json"
        observed_path = out_dir / "joint_set_true_nested_summary.json"
        summary_path = out_dir / "joint_set_null_calibration_summary.json"
        report_path = out_dir / "joint_set_null_calibration_report.md"
    else:
        state_path = out_dir / "joint_set_v2_null_calibration_state.json"
        observed_path = out_dir / "joint_set_v2_true_nested_summary.json"
        summary_path = out_dir / "joint_set_v2_null_calibration_summary.json"
        report_path = out_dir / "joint_set_v2_null_calibration_report.md"

    state = read_json(state_path)
    identity = state_identity(state)
    fragment_files = sorted(fragments_dir.glob(f"{model}-*.json"))
    if not fragment_files:
        raise RuntimeError(f"no fragments found for {model} in {fragments_dir}")
    fragment_worlds: List[Sequence[Mapping[str, object]]] = []
    for path in fragment_files:
        fragment = read_json(path)
        if fragment.get("model") != model:
            raise RuntimeError(f"wrong model in fragment: {path}")
        if fragment.get("state_identity") != identity:
            raise RuntimeError(f"state identity mismatch: {path}")
        records = fragment.get("worlds", [])
        if not isinstance(records, list):
            raise RuntimeError(f"invalid worlds payload: {path}")
        for record in records:
            world = int(record["world"])
            expected_seed = nullmod.world_seed(str(state["data_sha256"]), world)
            if int(record["seed"]) != int(expected_seed):
                raise RuntimeError(f"seed mismatch for {model} world {world}")
        fragment_worlds.append(records)

    merged = merge_world_records(
        [w for w in state.get("worlds", []) if isinstance(w, dict)],
        fragment_worlds,
        int(state["target_worlds"]),
    )
    state["worlds"] = merged
    write_json(state_path, state)

    observed = read_json(observed_path)
    observed_delta = float(observed["portfolio"]["score_delta_vs_random"]["mean"])
    summary = nullmod.summarize(state, observed_delta)
    write_json(summary_path, summary)
    report_path.write_text(nullmod.render_report(summary), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic sharded null-calibration worker/merger")
    sub = ap.add_subparsers(dest="command", required=True)

    worker = sub.add_parser("worker")
    worker.add_argument("--model", choices=["v1", "v2"], required=True)
    worker.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    worker.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    worker.add_argument("--metadata", type=Path, default=Path("loto7_agent_output/research_external_metadata.csv"))
    worker.add_argument("--min-train", type=int, default=100)
    worker.add_argument("--last-n", type=int, default=60)
    worker.add_argument("--selection-window", type=int, default=120)
    worker.add_argument("--validation-scenarios", type=int, default=256)
    worker.add_argument("--validation-candidates", type=int, default=64)
    worker.add_argument("--target-worlds", type=int, default=64)
    worker.add_argument("--cutoff-hour-jst", type=int, default=18)
    worker.add_argument("--shard-index", type=int, required=True)
    worker.add_argument("--shard-count", type=int, required=True)
    worker.add_argument("--output", type=Path, required=True)

    merger = sub.add_parser("merge")
    merger.add_argument("--model", choices=["v1", "v2"], required=True)
    merger.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    merger.add_argument("--fragments-dir", type=Path, required=True)

    args = ap.parse_args()
    if args.command == "worker":
        result = run_worker(
            args.model, args.csv, args.out_dir, args.metadata, args.min_train, args.last_n,
            args.selection_window, args.validation_scenarios, args.validation_candidates,
            args.target_worlds, args.cutoff_hour_jst, args.shard_index, args.shard_count,
            args.output,
        )
    else:
        result = merge_fragments(args.model, args.out_dir, args.fragments_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
