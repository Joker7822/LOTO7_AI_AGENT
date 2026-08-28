#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

JST = dt.timezone(dt.timedelta(hours=9))
REPORT_VERSION = "research-metadata-v1-leakage-safe"
TRUSTED_VERIFICATIONS = {"verified", "trusted", "verified_pre_draw", "official_pre_draw"}
FIELDS = ["effective_round", "available_at_jst", "feature", "value", "source", "verification"]


@dataclass(frozen=True)
class MetadataRecord:
    effective_round: int
    available_at_jst: dt.datetime
    feature: str
    value: str
    source: str
    verification: str


def parse_round(value: object) -> int | None:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def parse_datetime(value: str) -> dt.datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("available_at_jst is required")
    obj = dt.datetime.fromisoformat(text)
    if obj.tzinfo is None:
        obj = obj.replace(tzinfo=JST)
    return obj.astimezone(JST)


def draw_cutoff(draw_date: str | dt.date | dt.datetime, cutoff_hour_jst: int = 18) -> dt.datetime:
    if isinstance(draw_date, dt.datetime):
        d = draw_date.astimezone(JST).date() if draw_date.tzinfo else draw_date.date()
    elif isinstance(draw_date, dt.date):
        d = draw_date
    else:
        d = dt.date.fromisoformat(str(draw_date)[:10])
    return dt.datetime.combine(d, dt.time(hour=int(cutoff_hour_jst)), tzinfo=JST)


def read_records(path: Path) -> Tuple[List[MetadataRecord], List[str]]:
    if not path.exists():
        return [], []
    records: List[MetadataRecord] = []
    issues: List[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            try:
                rnd = parse_round(row.get("effective_round", ""))
                if rnd is None:
                    raise ValueError("effective_round missing")
                feature = str(row.get("feature", "")).strip()
                if not feature:
                    raise ValueError("feature missing")
                records.append(MetadataRecord(
                    effective_round=rnd,
                    available_at_jst=parse_datetime(str(row.get("available_at_jst", ""))),
                    feature=feature,
                    value=str(row.get("value", "")).strip(),
                    source=str(row.get("source", "")).strip(),
                    verification=str(row.get("verification", "")).strip().lower(),
                ))
            except Exception as exc:
                issues.append(f"line {line_no}: {exc}")
    return records, issues


def write_template(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writeheader()


def _feature_items(record: MetadataRecord) -> Iterable[Tuple[str, float]]:
    value = record.value.strip()
    try:
        numeric = float(value)
        if math.isfinite(numeric):
            yield record.feature, numeric
            return
    except Exception:
        pass
    if value:
        yield f"{record.feature}={value}", 1.0


def feature_map_for_target(
    records: Sequence[MetadataRecord],
    target_round: int,
    target_draw_date: str | dt.date | dt.datetime,
    cutoff_hour_jst: int = 18,
) -> Dict[str, float]:
    """Return only trusted metadata that demonstrably existed before the target cutoff.

    A row refers to the round it is allowed to affect via ``effective_round``. This
    makes lagged physical metadata possible without ever using a same-draw value that
    became known only after the draw.
    """
    cutoff = draw_cutoff(target_draw_date, cutoff_hour_jst)
    out: Dict[str, float] = {}
    for rec in records:
        if rec.effective_round != int(target_round):
            continue
        if rec.verification not in TRUSTED_VERIFICATIONS:
            continue
        if rec.available_at_jst > cutoff:
            continue
        for name, value in _feature_items(rec):
            out[name] = float(value)
    return out


def design_matrix(
    records: Sequence[MetadataRecord],
    target_rounds: Sequence[int],
    target_draw_dates: Sequence[str | dt.date | dt.datetime],
    cutoff_hour_jst: int = 18,
    feature_names: Sequence[str] | None = None,
) -> Tuple[np.ndarray, List[str], List[Dict[str, float]]]:
    if len(target_rounds) != len(target_draw_dates):
        raise ValueError("target_rounds and target_draw_dates length mismatch")
    maps = [
        feature_map_for_target(records, int(r), d, cutoff_hour_jst)
        for r, d in zip(target_rounds, target_draw_dates)
    ]
    names = list(feature_names) if feature_names is not None else sorted({k for m in maps for k in m})
    mat = np.zeros((len(maps), len(names)), dtype=float)
    index = {name: i for i, name in enumerate(names)}
    for row_i, fmap in enumerate(maps):
        for name, value in fmap.items():
            col = index.get(name)
            if col is not None and math.isfinite(float(value)):
                mat[row_i, col] = float(value)
    return mat, names, maps


def ridge_number_adjustment(
    history_x: np.ndarray,
    history_design: np.ndarray,
    target_vector: np.ndarray,
    ridge: float = 20.0,
    min_rows: int = 30,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Fit a strongly-shrunk metadata -> number residual map using prior draws only."""
    x = np.asarray(history_x, dtype=float)
    f = np.asarray(history_design, dtype=float)
    target = np.asarray(target_vector, dtype=float).reshape(-1)
    if x.ndim != 2 or x.shape[1] != 37:
        raise ValueError("history_x must be [draws, 37]")
    if f.ndim != 2 or f.shape[0] != x.shape[0] or target.shape[0] != f.shape[1]:
        raise ValueError("metadata design dimensions do not align")
    if f.shape[1] == 0 or len(x) < max(int(min_rows), f.shape[1] + 8):
        return np.zeros(37, dtype=float), {"active": 0.0, "coverage": 0.0, "norm": 0.0}

    coverage = float(np.mean(np.any(np.abs(f) > 1e-12, axis=1)))
    if coverage < 0.15 or not np.any(np.abs(target) > 1e-12):
        return np.zeros(37, dtype=float), {"active": 0.0, "coverage": coverage, "norm": 0.0}

    mu = f.mean(axis=0)
    sd = f.std(axis=0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    z = (f - mu) / sd
    zt = (target - mu) / sd
    y = x - x.mean(axis=0, keepdims=True)
    gram = z.T @ z + float(ridge) * np.eye(z.shape[1])
    beta = np.linalg.solve(gram, z.T @ y)
    adj = zt @ beta
    adj = np.asarray(adj, dtype=float)
    adj -= adj.mean()
    scale = float(np.std(adj))
    if scale > 1e-10:
        adj = np.clip(adj / scale, -3.0, 3.0)
    else:
        adj[:] = 0.0
    return adj, {"active": float(np.any(np.abs(adj) > 1e-12)), "coverage": coverage, "norm": float(np.linalg.norm(adj))}


def validate_metadata(
    path: Path,
    target_rounds: Sequence[int] | None = None,
    target_dates: Sequence[str] | None = None,
    cutoff_hour_jst: int = 18,
) -> Dict[str, object]:
    records, issues = read_records(path)
    trusted = [r for r in records if r.verification in TRUSTED_VERIFICATIONS]
    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "path": str(path),
        "records": len(records),
        "trusted_records": len(trusted),
        "issues": issues,
        "cutoff_hour_jst": int(cutoff_hour_jst),
        "same_draw_post_cutoff_is_rejected": True,
        "policy": "Research-only. A feature is usable only when its effective_round matches the target and available_at_jst is at or before the conservative draw cutoff.",
    }
    if target_rounds is not None and target_dates is not None:
        mat, names, _ = design_matrix(records, target_rounds, target_dates, cutoff_hour_jst)
        summary["feature_names"] = names
        summary["rows_with_any_feature"] = int(np.sum(np.any(np.abs(mat) > 1e-12, axis=1))) if len(mat) else 0
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate leakage-safe pre-draw Research metadata")
    ap.add_argument("--metadata", type=Path, default=Path("loto7_agent_output/research_external_metadata.csv"))
    ap.add_argument("--report", type=Path, default=Path("loto7_agent_output/research_metadata_summary.json"))
    ap.add_argument("--cutoff-hour-jst", type=int, default=18)
    args = ap.parse_args()
    write_template(args.metadata)
    result = validate_metadata(args.metadata, cutoff_hour_jst=args.cutoff_hour_jst)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
