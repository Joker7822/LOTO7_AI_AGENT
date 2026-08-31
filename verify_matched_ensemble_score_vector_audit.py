#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

import matched_ensemble_score_vector_audit as audit


def _read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def verify_row(row: Dict[str, str], kind: str) -> Dict[str, object]:
    errors: List[str] = []
    try:
        scores_text = row["null_score_vector_json"]
        scores_obj = json.loads(scores_text)
        if not isinstance(scores_obj, list):
            raise ValueError("score vector is not a list")
        size = int(row["ensemble_size"])
        if len(scores_obj) != size:
            errors.append("ensemble_size_mismatch")
        scores = [float(x) for x in scores_obj]
        expected_vector_sha = audit._sha256_text(scores_text)
        if expected_vector_sha != row.get("null_score_vector_sha256", ""):
            errors.append("score_vector_sha256_mismatch")

        if kind == "formal":
            subject_version = row.get("candidate_version", "")
            subject_score_text = row.get("candidate_score_canonical", "")
        elif kind == "holdout":
            subject_version = row.get("holdout_version", "")
            subject_score_text = row.get("holdout_score_canonical", "")
        else:
            raise ValueError(f"unknown kind: {kind}")
        subject_score = float(subject_score_text)
        replay = audit._replay_metrics(subject_score, scores)
        expected_record_sha = audit._audit_record_sha256(
            round_no=int(row["round"]),
            subject_version=subject_version,
            subject_score=subject_score_text,
            vector_sha=row.get("null_score_vector_sha256", ""),
            reference_sha=row.get("matched_ensemble_reference_sha256", ""),
            frozen_at=row.get("matched_ensemble_frozen_at_jst", ""),
        )
        if expected_record_sha != row.get("audit_record_sha256", ""):
            errors.append("audit_record_sha256_mismatch")
        if abs(float(row["ensemble_mean_score_recomputed"]) - replay["mean_score"]) > 1e-12:
            errors.append("ensemble_mean_replay_mismatch")
        if abs(float(row["percentile_midrank_recomputed"]) - replay["percentile_midrank"]) > 1e-9:
            errors.append("percentile_replay_mismatch")
        if abs(float(row["permutation_p_upper_recomputed"]) - replay["permutation_p_upper"]) > 1e-9:
            errors.append("permutation_p_replay_mismatch")
        if row.get("audit_version") != audit.VERSION:
            errors.append("audit_version_mismatch")
    except Exception as exc:
        errors.append(f"parse_or_replay_error:{type(exc).__name__}:{exc}")
    return {
        "round": row.get("round"),
        "kind": kind,
        "subject_version": row.get("candidate_version") or row.get("holdout_version"),
        "ok": not errors,
        "errors": errors,
    }


def verify_file(path: Path, kind: str) -> Dict[str, object]:
    rows = _read_rows(path)
    results = [verify_row(row, kind) for row in rows]
    failures = [r for r in results if not r["ok"]]
    return {
        "path": str(path),
        "kind": kind,
        "rows": len(rows),
        "failures": len(failures),
        "ok": not failures,
        "failure_details": failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--formal",
        type=Path,
        default=Path("loto7_agent_output/matched_ensemble_score_vector_audit.csv"),
    )
    ap.add_argument(
        "--holdout",
        type=Path,
        default=Path("loto7_agent_output/future_holdout_matched_ensemble_score_vector_audit.csv"),
    )
    args = ap.parse_args()
    formal = verify_file(args.formal, "formal")
    holdout = verify_file(args.holdout, "holdout")
    result = {
        "audit_version": audit.VERSION,
        "hash_algorithm": audit.HASH_ALGORITHM,
        "canonical_float": audit.CANONICAL_FLOAT_FORMAT,
        "formal": formal,
        "holdout": holdout,
        "ok": bool(formal["ok"] and holdout["ok"]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
