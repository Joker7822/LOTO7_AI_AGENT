"""Prospective v2 research commitments; no public research ticket vectors.

Only the next explicitly scheduled unobserved draw may be committed. A hash
commitment is NOT independently authenticated pre-draw evidence on its own.
A separate artifact/receipt audit and outcome grading are required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from first_prize_research import checked_source, frozen_now, load_json, sha_object
from loto7_evolving_agent import make_history, read_csv_flexible, walk_forward_evolve, final_score
import loto7_v2_runner as v2
from production_ticket_geometry35 import ranked_portfolio_from_scores
from production_roi_cash35_v2 import candidate_from_canonical_rows
from combination_agent35_core import candidate_from_history
from balanced_uniform_portfolio import validate_portfolio

VERSION = "roi-cash-v2-prospective-commitment-v1"
JST = timezone(timedelta(hours=9))
ARCHIVE = Path("research/roi_cash_v2_prospective")
REGISTRATION = ARCHIVE / "registration.json"


def git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def protocol(root):
    p = load_json(root / REGISTRATION)
    if (p.get("version") != VERSION or p.get("first_target") != 705
            or p.get("last_target") != 730 or p.get("fixed_rounds") != 26
            or p.get("champion") != "baseline-5fdb8dc2ad"
            or p.get("candidate_version") != "research-roi-cash-trained-ranked35-v2"
            or p.get("arms") != ["cash_v2", "pairwise_v1", "matched_random32"]
            or p.get("tickets_per_arm") != 5 or p.get("cost_yen_per_arm") != 1500
            or p.get("cutoff_jst") != "18:00:00"
            or p.get("authority") != "research_only_no_purchase_no_promotion_no_production_change"
            or p.get("independent_receipt_required") is not True):
        raise ValueError("prospective protocol changed")
    pins = p.get("algorithm_git_blob_sha1")
    required = ["audit_ledger.py","balanced_uniform_portfolio.py","combination_agent35_core.py","first_prize_research.py","loto7_evolving_agent.py","loto7_v2_runner.py","production_disjoint35_policy.py","production_roi_cash35_v2.py","production_ticket_geometry35.py","requirements.txt","research/roi_cash_agent_v2.py"]
    if not isinstance(pins, dict) or set(pins) != set(required):
        raise ValueError("algorithm manifest incomplete")
    for name, digest in pins.items():
        if git_blob(root / name) != digest:
            raise ValueError("registered algorithm changed: " + name)
    return p


def hash_portfolios(tickets, ranking):
    normalized = [list(t) for t in tickets]
    validate_portfolio(normalized)
    if sorted(n for t in normalized for n in t) != sorted(ranking[:35]):
        raise ValueError("control does not preserve selected 35 numbers")
    return sha_object(normalized)


def commitments(history, canonical, ranking, p_hash, target, base_sha):
    cash, _ = candidate_from_canonical_rows(canonical, ranking)
    old, _ = candidate_from_history(history, ranking)
    matched = []
    for i in range(32):
        seed = int(hashlib.sha256(f"{p_hash}|{target}|{base_sha}|{i}".encode()).hexdigest(), 16)
        permutation = list(ranking[:35])
        random.Random(seed).shuffle(permutation)
        matched.append(hash_portfolios([sorted(permutation[j:j+7]) for j in range(0,35,7)], ranking))
    return {"cash_v2_sha256": hash_portfolios(cash, ranking),
            "pairwise_v1_sha256": hash_portfolios(old, ranking),
            "matched_random32_sha256": matched,
            "ranking_sha256": sha_object(ranking)}


def freeze(root, *, now=None, run_id=None, source_commit=None):
    root = Path(root)
    p = protocol(root)
    p_hash = sha_object(p)
    out = root / "loto7_agent_output"
    csv_path = root / "loto7.csv"
    source_path = out / "source_validation.json"
    raw_source = load_json(source_path)
    if raw_source.get("status") != "ok" or raw_source.get("verification") != "verified_two_result_sources":
        return {"status":"awaiting_verified_source"}
    canonical, source, base_sha = checked_source(csv_path, source_path)
    target = len(canonical) + 1
    if not p["first_target"] <= target <= p["last_target"]:
        return {"status":"outside_fixed_horizon", "target_round":target}
    schedule = (source.get("sources") or {}).get("official_schedule") or {}
    day = schedule.get("date")
    if schedule.get("round") != target or not isinstance(day, str):
        return {"status":"awaiting_explicit_schedule", "target_round":target}
    now = now or datetime.now(JST)
    if now.tzinfo is None:
        raise ValueError("clock must be timezone aware")
    path = root / ARCHIVE / f"commitment_{target:04d}.json"
    if path.exists():
        old = load_json(path)
        if (old.get("protocol_sha256") != p_hash or old.get("target_round") != target
                or old.get("base_csv_sha256") != base_sha or old.get("draw_date") != day
                or old.get("version") != VERSION):
            raise ValueError("existing commitment differs; never overwrite")
        return {"status":"already_committed", "target_round":target}
    try:
        frozen_now(now, day)
    except ValueError:
        return {"status":"cutoff_passed_no_backfill", "target_round":target}
    if not isinstance(run_id, str) or not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ValueError("GitHub run id required")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[a-f0-9]{40}", source_commit):
        raise ValueError("source commit required")
    raw_champion = load_json(out / "model_champion.json")
    champion = v2.load_champion(out / "model_champion.json")
    if raw_champion.get("model_version") != p["champion"] or champion.version() != p["champion"]:
        raise ValueError("registered Champion changed")
    hist, _ = make_history(read_csv_flexible(csv_path))
    if len(hist) != target - 1:
        raise ValueError("history prefix mismatch")
    bt = walk_forward_evolve(hist, min_train=100, eta=champion.eta, decay=champion.decay,
                             expert_uniform_mix=champion.expert_uniform_mix)
    q = final_score(hist, bt, uniform_mix=champion.final_uniform_mix)
    _, ranking = ranked_portfolio_from_scores(q)
    digests = commitments(hist, canonical, ranking, p_hash, target, base_sha)
    # Recheck real clock before publication; never accept a post-cutoff result
    # from an expensive computation. Explicit test clocks stay deterministic.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        frozen_now(datetime.now(JST), day)
    record = {"version":VERSION,"protocol_sha256":p_hash,"target_round":target,
              "draw_date":day,"base_round":target-1,"base_csv_sha256":base_sha,
              "source_report_sha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),
              "source_commit":source_commit,"github_run_id":run_id,
              "created_at_jst":now.astimezone(JST).isoformat(),
              "cost_yen_per_arm":1500, "digests":digests,
              "independent_snapshot_audit_passed":False,
              "prediction_skill_confirmed":False,"production_changed":False}
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    return {"status":"hash_commitment_created", "target_round":target, "file":str(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--verify-registration", action="store_true")
    args = parser.parse_args()
    root = args.repo_root
    if args.verify_registration:
        print("Registered protocol SHA256:", sha_object(protocol(root)))
        return
    ref = subprocess.check_output(["git","rev-parse","HEAD"], cwd=root, text=True).strip()
    print(json.dumps(freeze(root, run_id=os.environ.get("GITHUB_RUN_ID"), source_commit=ref),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
