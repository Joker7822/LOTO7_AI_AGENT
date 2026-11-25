"""Read-only prize tallies, kept separate for replay and pre-draw issued tickets."""
from collections import Counter
from datetime import datetime
import json
import re

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


def history(out, scorecard):
    scope = "historical_replay"
    try:
        p = scorecard["reference_payout"]
        if p["status"] != "historical_hypothetical_only":
            return unavailable(scope)
        raw = json.loads((out / "historical_reconciliation_summary.json").read_text(encoding="utf-8"))
        counts = raw["grade_counts"]
        if not isinstance(counts, dict) or set(counts) - set(GRADES):
            raise ValueError("invalid grades")
        counts = {g: count(counts.get(g, 0)) for g in GRADES}
        rounds = count(raw["evaluated_rounds"])
        result = summary(scope, counts, rounds, count(p["reference_payout_yen"]))
        if (result["tickets"] != p["tickets"] or result["tickets"] != rounds * 5
                or result["winning_tickets"] != p["winning_tickets"]
                or result["reference_cost_yen"] != p["reference_cost_yen"]):
            raise ValueError("replay counts disagree")
        return result
    except (OSError, ValueError, TypeError, KeyError):
        return unavailable(scope)


def live(out, source, published):
    scope = "issued_production"
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
        trusted = trusted_draws(out)
        raw = {parse_round(r["round"]): r for r in rows("actual_results.csv")
               if r.get("source_status") == "ok" and r.get("source_verification") == TRUST}
        counts = Counter()
        payout = 0
        incomplete = False
        settled = excluded = pending = 0
        for rnd in sorted(by_target):
            if rnd > target:
                continue
            if rnd > latest:
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
        return summary(scope, counts, settled, None if incomplete else payout,
                       excluded=excluded, pending=pending)
    except (OSError, ValueError, TypeError, KeyError):
        return unavailable(scope)


def project(out, source, published, scorecard):
    return {"version": "dashboard-prize-totals-v1",
            "historical": history(out, scorecard), "live": live(out, source, published)}
