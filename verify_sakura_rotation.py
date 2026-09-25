#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.parse
from pathlib import Path
from typing import Dict

import prediction_db_sync as dbs

INCIDENT_AT = dt.datetime(2026, 9, 6, 8, 56, 30, tzinfo=dt.timezone.utc)
VERSION = "sakura-credential-rotation-verification-v1"


def parse_timestamp(value: str, label: str) -> dt.datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def verify_rotation(
    endpoint: str,
    secret: str,
    credential_generation: str,
    db_rotated_at: str,
    hmac_rotated_at: str,
) -> Dict[str, object]:
    generation = str(credential_generation or "").strip()
    if not generation:
        raise ValueError("credential_generation is required")

    db_at = parse_timestamp(db_rotated_at, "db_rotated_at")
    hmac_at = parse_timestamp(hmac_rotated_at, "hmac_rotated_at")
    if db_at <= INCIDENT_AT:
        raise ValueError("db_rotated_at must be after the 2026-09-06 credential exposure")
    if hmac_at <= INCIDENT_AT:
        raise ValueError("hmac_rotated_at must be after the 2026-09-06 credential exposure")

    payload = {
        "schema_version": dbs.SCHEMA_VERSION,
        "predictions": [],
        "results": [],
    }
    result = dbs.post_payload(
        endpoint,
        secret,
        payload,
        credential_generation=generation,
    )

    verified_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    host = urllib.parse.urlparse(endpoint).hostname or ""
    return {
        "version": VERSION,
        "status": "rotation_attested_and_live_verified",
        "verified_at_utc": verified_at,
        "incident": {
            "issue": 45,
            "exposed_at_or_before_utc": INCIDENT_AT.isoformat().replace("+00:00", "Z"),
        },
        "credential_generation": generation,
        "rotation_attestation": {
            "db_password_rotated_at_utc": db_at.isoformat().replace("+00:00", "Z"),
            "hmac_secret_rotated_at_utc": hmac_at.isoformat().replace("+00:00", "Z"),
        },
        "live_verification": {
            "endpoint_host": host,
            "hmac_authentication": "verified",
            "credential_generation_match": True,
            "database_connection_and_transaction": "verified",
            "predictions_upserted": int(result.get("predictions_upserted", 0) or 0),
            "results_upserted": int(result.get("results_upserted", 0) or 0),
        },
        "limitations": {
            "old_db_password_rejection": "attested_not_independently_retested",
            "old_hmac_rejection": "attested_not_independently_retested",
            "secret_values_recorded": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify Sakura credential rotation without recording secret values."
    )
    ap.add_argument("--endpoint", default=os.environ.get("SAKURA_PREDICTION_API_URL", ""))
    ap.add_argument("--secret", default=os.environ.get("SAKURA_PREDICTION_HMAC_SECRET", ""))
    ap.add_argument(
        "--credential-generation",
        default=os.environ.get("SAKURA_CREDENTIAL_GENERATION", ""),
    )
    ap.add_argument("--db-rotated-at", default=os.environ.get("SAKURA_DB_ROTATED_AT", ""))
    ap.add_argument("--hmac-rotated-at", default=os.environ.get("SAKURA_HMAC_ROTATED_AT", ""))
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("loto7_agent_output/sakura_credential_rotation_status.json"),
    )
    args = ap.parse_args()

    if not args.endpoint or not args.secret:
        raise SystemExit("SAKURA_PREDICTION_API_URL and SAKURA_PREDICTION_HMAC_SECRET are required")

    status = verify_rotation(
        args.endpoint,
        args.secret,
        args.credential_generation,
        args.db_rotated_at,
        args.hmac_rotated_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
