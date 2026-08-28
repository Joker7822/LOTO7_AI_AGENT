#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

SCHEMA_VERSION = "loto7-db-sync-v1"


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def parse_json_object(value: str) -> Dict[str, object]:
    try:
        obj = json.loads(value or "{}")
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def yen_int(value: str, default: int = 0) -> int:
    text = str(value or "").replace(",", "").replace("円", "").strip()
    m = re.search(r"-?\d+", text)
    return int(m.group(0)) if m else int(default)


def latest_invalidations(rows: Sequence[Mapping[str, str]]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for row in rows:
        if str(row.get("action", "")).strip().lower() != "invalidate":
            continue
        pid = str(row.get("prediction_id", "")).strip()
        if not pid:
            continue
        old = out.get(pid)
        if old is None or str(row.get("corrected_at_jst", "")) >= str(old.get("corrected_at_jst", "")):
            out[pid] = dict(row)
    return out


def prediction_payload(
    predictions: Sequence[Mapping[str, str]], corrections: Sequence[Mapping[str, str]]
) -> List[Dict[str, object]]:
    invalid = latest_invalidations(corrections)
    out: List[Dict[str, object]] = []
    for row in predictions:
        pid = str(row.get("prediction_id", "")).strip()
        if not pid:
            continue
        inv = invalid.get(pid)
        out.append({
            "prediction_id": pid,
            "prediction_created_at_jst": str(row.get("prediction_created_at_jst", "")),
            "base_round": str(row.get("base_round", "")),
            "base_draw_date": str(row.get("base_draw_date", "")),
            "target_round": str(row.get("target_round", "")),
            "target_draw_date_estimate": str(row.get("target_draw_date_estimate", "")),
            "ticket": int(row.get("ticket") or 0),
            "predicted_numbers": str(row.get("predicted_numbers", "")),
            "model_version": str(row.get("model_version", "")),
            "git_sha": str(row.get("git_sha", "")),
            "data_sha256": str(row.get("data_sha256", "")),
            "strategy_weights": parse_json_object(str(row.get("strategy_weights_json", "{}"))),
            "is_active": inv is None,
            "invalidated_at_jst": "" if inv is None else str(inv.get("corrected_at_jst", "")),
            "invalidation_reason": "" if inv is None else str(inv.get("reason", "")),
        })
    return out


def result_payload(rows: Sequence[Mapping[str, str]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        pid = str(row.get("prediction_id", "")).strip()
        if not pid:
            continue
        out.append({
            "prediction_id": pid,
            "result_id": str(row.get("result_id", "")),
            "target_round": str(row.get("target_round", "")),
            "ticket": int(row.get("ticket") or 0),
            "actual_draw_date": str(row.get("actual_draw_date", "")),
            "actual_main_numbers": str(row.get("actual_main_numbers", "")),
            "actual_bonus_numbers": str(row.get("actual_bonus_numbers", "")),
            "main_hits": int(row.get("main_hits") or 0),
            "bonus_hits": int(row.get("bonus_hits") or 0),
            "grade": str(row.get("grade", "")),
            "prize_amount_yen": yen_int(str(row.get("prize_amount", "")), 0),
            "purchase_cost_yen": yen_int(str(row.get("purchase_cost", "")), 300),
            "net_result_yen": yen_int(str(row.get("net_result", "")), -300),
            "model_version": str(row.get("model_version", "")),
        })
    return out


def build_payload(
    predictions_path: Path,
    corrections_path: Path,
    reconciliation_path: Path,
) -> Dict[str, object]:
    predictions = prediction_payload(read_csv(predictions_path), read_csv(corrections_path))
    active_ids = {str(row["prediction_id"]) for row in predictions if bool(row.get("is_active"))}
    results = [
        row for row in result_payload(read_csv(reconciliation_path))
        if str(row.get("prediction_id", "")) in active_ids
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "predictions": predictions,
        "results": results,
    }


def encode_payload(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def signature(secret: str, timestamp: int, body: bytes) -> str:
    message = str(int(timestamp)).encode("ascii") + b"." + body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def post_payload(endpoint: str, secret: str, payload: Mapping[str, object], timeout: int = 30) -> Dict[str, object]:
    if not endpoint.lower().startswith("https://"):
        raise ValueError("Sakura endpoint must use HTTPS")
    if len(secret) < 24:
        raise ValueError("HMAC secret must be at least 24 characters")
    body = encode_payload(payload)
    ts = int(time.time())
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "LOTO7-AI-Agent/1.0",
            "X-LOTO7-Timestamp": str(ts),
            "X-LOTO7-Signature": signature(secret, ts, body),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Sakura API HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Sakura API connection failed: {exc.reason}") from exc
    obj = json.loads(raw)
    if not isinstance(obj, dict) or not obj.get("ok"):
        raise RuntimeError(f"Sakura API rejected payload: {raw[:500]}")
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync canonical LOTO7 predictions/results to Sakura MySQL through a signed HTTPS bridge")
    ap.add_argument("--predictions", type=Path, default=Path("loto7_agent_output/predictions.csv"))
    ap.add_argument("--corrections", type=Path, default=Path("loto7_agent_output/prediction_corrections.csv"))
    ap.add_argument("--reconciliation", type=Path, default=Path("loto7_agent_output/reconciliation.csv"))
    ap.add_argument("--endpoint", default=os.environ.get("SAKURA_PREDICTION_API_URL", ""))
    ap.add_argument("--secret", default=os.environ.get("SAKURA_PREDICTION_HMAC_SECRET", ""))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    payload = build_payload(args.predictions, args.corrections, args.reconciliation)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"[SAKURA-DB] predictions={len(payload['predictions'])} "
        f"results={len(payload['results'])} dry_run={args.dry_run}"
    )
    if args.dry_run:
        return 0
    if not args.endpoint or not args.secret:
        raise SystemExit("SAKURA_PREDICTION_API_URL and SAKURA_PREDICTION_HMAC_SECRET are required")
    result = post_payload(args.endpoint, args.secret, payload)
    print(f"[SAKURA-DB] {json.dumps(result, ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
