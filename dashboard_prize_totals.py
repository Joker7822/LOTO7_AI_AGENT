"""Read-only prize tallies, kept separate for replay and pre-draw issued tickets."""
from collections import Counter
from datetime import datetime
import re

from dashboard_roi_cash_v2 import AUDITED_DRAW_COUNT, AUDITED_CANDIDATE_PAYOUT_YEN, AUDITED_LAST_ROUND, AUDIT_RUN
from production_disjoint35_policy import ROI_CASH_VERSION, ROI_CASH_MIN_TARGET_ROUND
from public_issued_prediction import forecast_group, grade, parse_round, trusted_draws, TRUST

GRADES = tuple(f"{i}等" for i in range(1, 7)) + ("はずれ",)


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError("invalid nonnegative integer")
    return value


def money(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)円", value.strip()):
        return None
    return int(value.strip()[:-1].replace(",", ""))


def summary(scope, counts, rounds, payout, *, excluded=0, pending=0):
    tickets = sum(counts.values())
    cost = 300 * tickets
    return {
        "scope": scope, "status": "verified" if rounds and payout is not None else
        "payout_incomplete" if rounds else "unavailable",
        "rounds": rounds, "tickets": tickets, "grade_counts": {g: counts.get(g, 0) for g in GRADES},
        "winning_tickets": tickets - counts.get("はずれ", 0),
        "reference_cost_yen": cost, "reference_payout_yen": payout if rounds else None,
        "reference_roi": payout / cost if cost and payout is not None else None,
        "excluded_rounds": excluded, "pending_rounds": pending,
        "actual_purchase_verified": False,
    }


def unavailable(scope):
    return {"scope": scope, "status": "unavailable", "actual_purchase_verified": False}


def history(out=None, scorecard=None):
    """Audited cash_v2 arm of run 44990515557, artifact 14742025156.
    All 703 targets have five unique ticket positions; CSV SHA256 below.
    """
    counts = {"1等": 0, "2等": 0, "3等": 1, "4等": 4, "5等": 52,
              "6等": 90, "はずれ": 3368}
    result = summary("historical_roi_cash_v2", counts, AUDITED_DRAW_COUNT,
                     AUDITED_CANDIDATE_PAYOUT_YEN)
    if result["tickets"] != AUDITED_DRAW_COUNT * 5:
        raise ValueError("audited v2 grade count mismatch")
    return {**result, "model": "production-ai-ranked35-roi-cash-v2",
            "first_round": 2, "last_round": AUDITED_LAST_ROUND,
            "first_draw_date": "2013-04-12", "last_draw_date": "2026-11-20",
            "audit_url": AUDIT_RUN, "artifact_id": 14742025156,
            "ticket_csv_sha256": "da3ae04a601aec74d1ad7b27d08e6ca3ff9408feee3bed877ddc546fc896c030"}


def live(out, source, published, *, v2_only=False):
    scope = "issued_roi_cash_v2" if v2_only else "issued_production"
    try:
        # No number vectors leave this projection. Reuse the existing canonical
        # validation, with a conservative 18:00 JST cutoff for this cash tally.
        import csv
        def rows(name):
            with (out / name).open(encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))
        latest = source["latest"]["round"]
        target = parse_round(published.get("target_round"))
        if type(latest) is not int or published.get("published") is not True or target is None:
            return unavailable(scope)
        invalid = {r["prediction_id"] for r in rows("prediction_corrections.csv")
                   if r.get("action") == "invalidate"}
        active = [r for r in rows("predictions.csv") if r["prediction_id"] not in invalid]
        by_target = {parse_round(r.get("target_round")) for r in active}
        if None in by_target:
            raise ValueError("malformed target")
        def v2_model(row):
            return re.fullmatch(r"baseline-[0-9a-f]{10}\+" + re.escape(ROI_CASH_VERSION),
                                row.get("model_version") or "") is not None
        if v2_only:
            # Select entire targets, not individual tickets; mixed-model groups
            # must fail validation rather than becoming a partial portfolio.
            by_target = {parse_round(r["target_round"]) for r in active if v2_model(r)
                         and parse_round(r["target_round"]) >= ROI_CASH_MIN_TARGET_ROUND}
        trusted = trusted_draws(out)
        raw = {parse_round(r["round"]): r for r in rows("actual_results.csv")
               if r.get("source_status") == "ok" and r.get("source_verification") == TRUST}
        counts = Counter()
        payout = 0
        incomplete = False
        settled = excluded = pending = 0
        first = last = None
        for rnd in sorted(by_target):
            if rnd > target:
                continue
            if rnd > latest:
                if v2_only:
                    try:
                        group = forecast_group(active, rnd, required=True)
                        if (rnd != target or len({r["model_version"] for r in group}) != 1
                                or not all(v2_model(r) for r in group)
                                or published.get("model_version") != group[0]["model_version"]
                                or len({r["prediction_created_at_jst"] for r in group}) != 1
                                or len({r["target_draw_date_estimate"] for r in group}) != 1
                                or datetime.fromisoformat(group[0]["prediction_created_at_jst"]) >=
                                   datetime.fromisoformat(group[0]["target_draw_date_estimate"] + "T18:00:00+09:00")):
                            raise ValueError("unverified v2 pending issue")
                    except (ValueError, TypeError, KeyError):
                        excluded += 1
                        continue
                pending += 1
                continue
            draw = trusted.get(rnd)
            if draw is None:
                excluded += 1
                continue
            if rnd == latest and (source.get("status") != "ok" or source.get("verification") != TRUST
                    or source["latest"].get("main") != draw["main"]
                    or source["latest"].get("bonus") != draw["bonus"]):
                excluded += 1
                continue
            try:
                group = forecast_group(active, rnd, required=True)
                if v2_only and (not all(v2_model(r) for r in group)
                                or len({r["model_version"] for r in group}) != 1):
                    raise ValueError("mixed v2 issuance")
                cutoff = datetime.fromisoformat(draw["date"] + "T18:00:00+09:00")
                if any(r["target_draw_date_estimate"] != draw["date"]
                       or datetime.fromisoformat(r["prediction_created_at_jst"]) >= cutoff
                       for r in group):
                    raise ValueError("not proven before conservative cutoff")
                if len({r["prediction_created_at_jst"] for r in group}) != 1:
                    raise ValueError("mixed issuance")
                scores = grade(group, draw)
            except (ValueError, TypeError, KeyError):
                excluded += 1
                continue
            period = {"round": rnd, "draw_date": draw["date"],
                      "created_at_jst": group[0]["prediction_created_at_jst"]}
            if first is None:
                first = period
            last = period
            settled += 1
            for item in scores:
                g = item["grade"]
                counts[g] += 1
                if g != "はずれ":
                    amount = money(raw[rnd].get(g + "当選金額"))
                    if amount is None:
                        incomplete = True
                    else:
                        payout += amount
        result = {**summary(scope, counts, settled, None if incomplete else payout,
                            excluded=excluded, pending=pending),
                  "first_settled": first, "last_settled": last}
        if v2_only:
            result.update(model=ROI_CASH_VERSION, start_target_round=ROI_CASH_MIN_TARGET_ROUND,
                          independent_future_skill_confirmed=False)
            if not settled:
                result["status"] = "awaiting_first_settlement" if not excluded else "unavailable"
        return result
    except (OSError, ValueError, TypeError, KeyError):
        return unavailable(scope)


def project(out, source, published, scorecard):
    return {"version": "dashboard-prize-totals-v2",
            "historical": history(out, scorecard), "live": live(out, source, published),
            "live_v2": live(out, source, published, v2_only=True)}
