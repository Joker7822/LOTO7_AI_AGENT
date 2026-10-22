#!/usr/bin/env python3
"""Bounded scholarly verification, methodological sandbox, and safe self-repair.

Trusted inputs: SHA-chained discovery, guarded lottery research state.
Untrusted inputs: Crossref/OpenAlex fields, abstracts, transport failures.
Only four new derived reports can be modified. No model/registered/OOS writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np

import always_on_accuracy_agent as discovery
import research_literature_pipeline as reviewer

VERSION = "research-evidence-resilience-v1"
EVIDENCE = "research_verified_publications.json"
SANDBOX = "research_method_sandbox.json"
REPAIRS = "research_self_repair_report.json"
REPORT = "research_verified_method_report.md"
DOI_LIMIT = 3
FAIR_WORLDS = 512
DRAWS_PER_WORLD = 24
SEED = 749293
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[a-z0-9._;():/-]{1,130}\Z", re.I)
HTTP_RETRYABLE = {408, 429, 500, 502, 503, 504}
HEADERS = {"User-Agent": "LOTO7-ResearchVerifier/1.0 (+https://github.com/Joker7822/LOTO7_AI_AGENT)",
           "Accept": "application/json"}


def canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_title(value: str) -> set[str]:
    return set(w for w in re.findall(r"[a-z0-9]+", value.casefold()) if len(w) > 1)


def title_matches(a: str, b: str) -> bool:
    x, y = normalized_title(a), normalized_title(b)
    return bool(x and y and len(x & y) / len(x | y) >= 0.72)


def retryable(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in HTTP_RETRYABLE
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))


def public_get_json(url: str, *, tries: int = 3,
                    opener: Callable | None = None,
                    sleep: Callable[[float], None] = time.sleep) -> tuple[dict, int]:
    """Only fixed public scholarly hosts; retries limited to transient errors."""
    parsed = urllib.parse.urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in
            {"api.crossref.org", "api.openalex.org"} or not parsed.path.startswith("/works/")):
        raise ValueError("unapproved public research endpoint")
    if tries < 1 or tries > 3:
        raise ValueError("retry budget exceeded")
    opener = opener or urllib.request.urlopen
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with opener(req, timeout=8) as response:
                body = response.read(400_001)
            if len(body) > 400_000:
                raise ValueError("remote bibliographic metadata too large")
            doc = json.loads(body)
            if not isinstance(doc, dict):
                raise ValueError("invalid scholarly JSON document")
            return doc, attempt
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                ConnectionError, OSError) as exc:
            if not retryable(exc) or attempt == tries - 1:
                raise
            sleep(float(attempt + 1))
    raise AssertionError("unreachable retry state")


def crossref_url(doi: str) -> str:
    if not DOI_PATTERN.fullmatch(doi):
        raise ValueError("DOI must be allowlisted")
    return "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/.-_;():")


def openalex_url(doi: str) -> str:
    if not DOI_PATTERN.fullmatch(doi):
        raise ValueError("DOI must be allowlisted")
    return ("https://api.openalex.org/works/https://doi.org/" +
            urllib.parse.quote(doi, safe="/.-_;():"))


def abstract_word_count_crossref(item: dict) -> int:
    text = item.get("abstract")
    # Do not retain publisher-owned abstracts or execute embedded markup.
    if not isinstance(text, str) or len(text) > 30_000:
        return 0
    return min(2000, len(re.findall(r"[a-zA-Z]{2,}", re.sub(r"<[^>]*>", " ", text))))


def abstract_word_count_openalex(item: dict) -> int:
    inverted = item.get("abstract_inverted_index")
    if not isinstance(inverted, dict) or len(inverted) > 5000:
        return 0
    positions = [p for values in inverted.values() if isinstance(values, list)
                 for p in values if isinstance(p, int) and 0 <= p <= 3000]
    return min(2000, len(set(positions)))


def crossref_info(payload: dict) -> dict | None:
    work = payload.get("message", {})
    if not isinstance(work, dict):
        return None
    names = work.get("title", [])
    year_parts = work.get("published", {}).get("date-parts", [[]])
    year = year_parts[0][0] if year_parts and year_parts[0] else None
    doi = str(work.get("DOI", "")).lower()
    if (not DOI_PATTERN.fullmatch(doi) or not isinstance(names, list)
            or not names or not isinstance(names[0], str)
            or not isinstance(year, int)):
        return None
    return {"doi": doi, "title": names[0][:250], "year": year,
            "abstract_words": abstract_word_count_crossref(work),
            "publisher_record_type": str(work.get("type", "unknown"))[:60]}


def openalex_info(payload: dict) -> dict | None:
    uri = payload.get("doi")
    if not isinstance(uri, str) or not uri.lower().startswith("https://doi.org/"):
        return None
    doi = urllib.parse.unquote(uri[len("https://doi.org/"):]).lower()
    title = payload.get("title", payload.get("display_name", ""))
    year = payload.get("publication_year")
    if (not DOI_PATTERN.fullmatch(doi) or not isinstance(title, str)
            or not title or not isinstance(year, int)):
        return None
    return {"doi": doi, "title": title[:250], "year": year,
            "abstract_words": abstract_word_count_openalex(payload)}


def verify_one(paper: dict, fetch: Callable[[str], tuple[dict, int]]) -> dict:
    """Independent DOI/title/year cross-check; not scientific peer review."""
    doi = paper["doi"]
    results, errors = {}, {}
    for provider, url in (("crossref", crossref_url(doi)), ("openalex", openalex_url(doi))):
        try:
            response, retries = fetch(url)
            info = crossref_info(response) if provider == "crossref" else openalex_info(response)
            if (not info or info["doi"] != doi or
                    info["year"] != paper["year"] or
                    not title_matches(info["title"], paper["title"])):
                errors[provider] = "bibliographic_identity_conflict"
            else:
                results[provider] = {**info, "transient_retries": retries}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                ConnectionError, OSError) as exc:
            errors[provider] = ("transient_provider_failure" if retryable(exc)
                                else "permanent_provider_failure")
        except (ValueError, TypeError, KeyError):
            errors[provider] = "malformed_provider_metadata"
    if ("bibliographic_identity_conflict" in errors.values() or
            (len(results) == 2 and not title_matches(
                results["crossref"]["title"], results["openalex"]["title"]))):
        status = "conflict_do_not_use"
    elif len(results) == 2:
        status = "two_provider_bibliography_matched"
    elif results:
        status = "single_provider_only"
    else:
        status = "unavailable"
    return {
        "doi": doi, "year": paper["year"], "status": status,
        "crossref_consistent": "crossref" in results,
        "openalex_consistent": "openalex" in results,
        "abstract_metadata_present": any(r["abstract_words"] >= 30 for r in results.values()),
        "abstract_word_count_max": max([r["abstract_words"] for r in results.values()], default=0),
        "source_errors": errors,
        "transient_retry_count": sum(r["transient_retries"] for r in results.values()),
        "full_text_reviewed": False,
        "peer_review_confirmed": False,
        "methods_reproduced_from_paper": False,
        "lottery_prediction_improved": False,
    }


def fair_sandbox(*, worlds: int = FAIR_WORLDS, draws: int = DRAWS_PER_WORLD,
                 seed: int = SEED) -> dict:
    """Fixed reference-only tests: fair null and a deliberately biased forecast.

    This tests safeguards from the *methodological topics*, not any paper's code.
    No LOTO7 history, no fitter, no prospective OOS and no candidate selection.
    """
    if not 10 <= worlds <= 1024 or not 1 <= draws <= 200:
        raise ValueError("sandbox computation cap exceeded")
    rng = np.random.default_rng(seed)
    uniform = np.full(37, 7 / 37, dtype=float)
    biased = np.full(37, (7 - 7 * .3) / 30, dtype=float)
    biased[:7] = .3
    fair_rate = 7 * 7 / 37
    hits = 0
    logscore_edges = []
    brier_edges = []
    e_factor_means = []
    for _ in range(worlds):
        log_e = 0.0
        max_e = 1.0
        score_edge = 0.0
        brier_edge = 0.0
        factors = []
        for _ in range(draws):
            drawn = rng.choice(37, size=7, replace=False)
            observed = np.zeros(37, dtype=float)
            observed[drawn] = 1.0
            # Proper Bernoulli marginal scoring, without treating the balls
            # as independent random events in the null simulation.
            s0 = np.mean(observed * np.log(uniform) +
                         (1 - observed) * np.log1p(-uniform))
            s1 = np.mean(observed * np.log(biased) +
                         (1 - observed) * np.log1p(-biased))
            score_edge += s1 - s0
            brier_edge += float(np.mean((observed - uniform) ** 2) -
                                np.mean((observed - biased) ** 2))
            factor = float(biased[drawn].sum() / fair_rate)
            factors.append(factor)
            log_e += math.log(factor)
            max_e = max(max_e, math.exp(log_e))
        logscore_edges.append(score_edge / draws)
        brier_edges.append(brier_edge / draws)
        e_factor_means.append(float(np.mean(factors)))
        hits += max_e >= 20
    return {
        "scope": "methodology_smoke_test_on_synthetic_fair_7_of_37_only",
        "worlds": worlds, "draws_per_world": draws, "fixed_seed": seed,
        "forecasts_compared": ["uniform_7_of_37", "fixed_biased_probabilities"],
        "biased_sum_inclusion_p": float(biased.sum()),
        "biased_minus_uniform_mean_log_score": float(np.mean(logscore_edges)),
        "biased_minus_uniform_mean_brier_edge": float(np.mean(brier_edges)),
        "observed_null_mean_e_factor": float(np.mean(e_factor_means)),
        "anytime_threshold": 20,
        "null_max_e_threshold_rate": hits / worlds,
        "nominal_alpha": .05,
        "future_oos_draws_consumed": 0,
        "real_model_experiments_executed": 0,
        "auto_promotion_allowed": False,
        "no_claim_about_actual_lottery_predictability": True,
    }


def read_prior(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (ValueError, OSError):
        return {}


def run(root: Path, *, fetch: Callable[[str], tuple[dict, int]] | None = None) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    before = {path: path.read_bytes() for path in (root / "loto7.csv",)
              if path.is_file()}
    guard = discovery.inspect_evidence(root)
    state_file = out / discovery.STATE
    state = discovery.read_json(state_file)
    chain = discovery.read_chain(out / discovery.LEDGER)
    papers = reviewer.checked_papers(state, chain)
    previous = read_prior(out / EVIDENCE)
    previous_records = {i["doi"]: i for i in previous.get("verifications", [])
                        if isinstance(i, dict) and isinstance(i.get("doi"), str)}
    relevant = {x["doi"] for x in papers}
    # Research sources are queried only when the hourly discovery rotates into
    # its literature phase. Each run caps external network work to three DOIs.
    # On initial installation perform one bounded verification immediately,
    # even if the hourly focus has rotated past the literature-search phase.
    # Preserve a persistent first-attempt marker to prevent hourly retry storms.
    first_verification = previous.get("initial_verification_attempted") is not True
    is_search = state.get("current_phase") == "literature_search" or first_verification
    if fetch is None:
        fetch = public_get_json
    output = []
    recovered = 0
    provider_failures = 0
    for paper in papers:
        original = previous_records.get(paper["doi"])
        if is_search and len(output) < DOI_LIMIT:
            observed = verify_one(paper, fetch)
            provider_failures += len(observed["source_errors"])
            if (observed["status"] == "unavailable" and original and
                    original.get("status") == "two_provider_bibliography_matched"):
                # Preserve past evidence but never claim *fresh* verification.
                observed = {**original, "status": "previously_verified_not_refreshed",
                            "source_errors": observed["source_errors"]}
                recovered += 1
        elif original and paper["doi"] in relevant:
            observed = dict(original)
            if observed.get("status") == "two_provider_bibliography_matched":
                observed["status"] = "previously_verified_not_refreshed"
        else:
            observed = {"doi": paper["doi"], "year": paper["year"],
                        "status": "not_yet_checked", "full_text_reviewed": False,
                        "peer_review_confirmed": False, "lottery_prediction_improved": False}
        output.append(observed)
    source_sha = sha256(state_file.read_bytes())
    evid = {
        "version": VERSION, "discovery_state_sha256": source_sha,
        "discovery_tip_sha256": chain[-1]["record_sha256"],
        "research_mode": guard["research_mode"],
        "latest_round": guard["latest_round"],
        "searched_this_cycle": bool(is_search),
        "initial_verification_attempted": True,
        "verification_reason": (
            "initial_bounded_bootstrap" if first_verification
            else "scheduled_literature_search" if is_search else "not_due"
        ),
        "max_dois_per_cycle": DOI_LIMIT,
        "verifications": output,
        "two_provider_matches_this_cycle": sum(x["status"] == "two_provider_bibliography_matched"
                                               for x in output),
        "full_text_reviewed_count": 0, "automatic_adoption": False,
        "future_registry_changed": False, "production_changed": False,
    }
    lab = fair_sandbox()
    recovery = {
        "version": VERSION, "input_discovery_state_sha256": source_sha,
        "decision": "bounded_auto_recovery_only",
        "network_transient_retries": sum(x.get("transient_retry_count", 0) for x in output),
        "provider_errors_or_conflicts": provider_failures,
        "previously_verified_records_preserved_without_fresh_claim": recovered,
        "derived_outputs_regenerated_from_trusted_inputs": True,
        "actions_automatically_allowed": [
            "retry_transient_408_429_5xx_max_three",
            "preserve_prior_verified_DOI_as_stale_on_provider_outage",
            "regenerate_derived_reports_from_SHA_checked_inputs",
            "run_fixed_no_model_change_fair_null_sandbox",
        ],
        "actions_prohibited": [
            "modify_model_code", "run_unapproved_model_training",
            "change_research_budget", "modify_frozen_future_registry",
            "fake_result_source_verification", "promote_champion_or_production",
            "automatically_merge_code_or_relaunch_failed_long_research",
        ],
        "requires_human_review_for_code_or_protocol_bugs": True,
    }
    # Research methods are applied to synthetic fair draws only, not new
    # optimizer trials. Never write any existing input file, even on errors.
    for path, data in ((EVIDENCE, evid), (SANDBOX, lab), (REPAIRS, recovery)):
        (out / path).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                          allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# Scientific Verification and Bounded Recovery",
        "", "- Metadata checks: Crossref/OpenAlex DOI, year, title agreement",
        f"- Candidates inspected: {len(output)}, fully checked now: {evid['two_provider_matches_this_cycle']}",
        "- Peer review / full text validation: **not established**",
        "- External abstracts are checked for presence only, never used as commands",
        "- Provenance: SHA-chain and source guard audited before network calls",
        f"- Network/provider error or conflict count: {provider_failures}",
        f"- Synthetic fair 7/37 worlds: {FAIR_WORLDS} × {DRAWS_PER_WORLD} draws",
        f"- Biased prediction log-score difference vs fair: {lab['biased_minus_uniform_mean_log_score']:+.8f}",
        f"- Biased prediction Brier improvement vs fair: {lab['biased_minus_uniform_mean_brier_edge']:+.8f}",
        f"- Fair null e-test threshold crossing fraction: {lab['null_max_e_threshold_rate']:.4f}",
        "- All experiments are safety smoke tests; **no evidence of actual LOTO7 forecasting advantage**",
        "- Self-repair: retry bounded transport failures, safe stale cache, regenerate derived-only reports.",
        "- Bugs requiring changes to code, model, registration or Production require review.",
        "",
    ]
    (out / REPORT).write_text("\n".join(lines), encoding="utf-8")
    if any(path.read_bytes() != contents for path, contents in before.items()):
        raise ValueError("protected historical draw bytes unexpectedly changed")
    return {"evidence": evid, "sandbox": lab, "recovery": recovery}


def main() -> int:
    p = argparse.ArgumentParser(description="DOI verification / synthetic methods / bounded self-healing")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    args = p.parse_args()
    result = run(args.repo_root)
    print(json.dumps({
        "two_provider_matches": result["evidence"]["two_provider_matches_this_cycle"],
        "synthetic_worlds": result["sandbox"]["worlds"],
        "automatic_model_changes": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
