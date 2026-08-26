#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import loto7_v4_runner as v4


def _skip_production_outputs(*args, **kwargs):
    return {
        "cached": True,
        "skipped": True,
        "reason": "weekly_production_published_only_at_friday_17_jst",
    }


def main() -> int:
    # Keep OOS grading, promotion governance, shadow freezing, Research search,
    # and state updates intact while preventing post-draw Research runs from
    # overwriting the frozen weekly Production forecast.
    v4.ensure_production_outputs = _skip_production_outputs
    return v4.main()


if __name__ == "__main__":
    raise SystemExit(main())
