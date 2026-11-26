"""Read-only snapshot backup heartbeat; never modifies evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

MAX_AGE_MINUTES = 60
MAX_FUTURE_MINUTES = 5


def refresh_required(path: Path, now: datetime) -> bool:
    if now.tzinfo is None:
        raise ValueError("clock must include a timezone")
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if snapshot.get("version") != "loto7-ops-snapshot-v1":
            return True
        created = datetime.fromisoformat(snapshot["generated_at_jst"])
        if created.tzinfo is None:
            return True
        minutes = (now - created).total_seconds() / 60
        return minutes >= MAX_AGE_MINUTES or minutes < -MAX_FUTURE_MINUTES
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--github-output", action="store_true")
    mode.add_argument("--is-fresh", action="store_true")
    args = parser.parse_args()
    needed = refresh_required(args.snapshot, datetime.now(timezone.utc))
    print("Backup snapshot refresh required:", str(needed).lower())
    if args.github_output:
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write("refresh_required=" + str(needed).lower() + "\n")
        return 0
    return int(needed)


if __name__ == "__main__":
    raise SystemExit(main())
