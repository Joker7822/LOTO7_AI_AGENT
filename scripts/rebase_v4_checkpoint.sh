#!/usr/bin/env bash
# Preserve the remote independently verified result when a concurrent bot
# publishes a v4 checkpoint from an older source report.
set -euo pipefail

git fetch origin main
if git rebase origin/main; then
  exit 0
fi

source_file="loto7_agent_output/source_validation.json"
conflicts="$(git diff --name-only --diff-filter=U)"
if [ "$conflicts" != "$source_file" ]; then
  echo "::error::Research rebase has unexpected conflicting evidence; refusing to override: $conflicts" >&2
  git rebase --abort || true
  exit 1
fi

# During REBASE, --ours is the already-updated main branch, while --theirs is
# the locally replayed research commit. Preserve the remote corroboration.
git checkout --ours -- "$source_file"
if ! python - <<'PY'
from pathlib import Path
import json
from joint_set_v2_signal_oos_guard import validate_trusted_source

csv = Path("loto7.csv")
report = Path("loto7_agent_output/source_validation.json")
record = json.loads(report.read_text(encoding="utf-8"))
if record.get("status") != "ok" or record.get("verification") != "verified_two_result_sources":
    raise ValueError("remote result is not independently corroborated")
proof = validate_trusted_source(csv, report)
if not proof["trusted"] or not proof.get("secondary"):
    raise ValueError("remote second-source result is not consistent with current draw CSV")
print("Preserved authoritative concurrent second-source record, round", proof["round"])
PY
then
  echo "::error::Cannot safely reconcile the remote source with this checkpoint." >&2
  git rebase --abort || true
  exit 1
fi
git add -- "$source_file"
GIT_EDITOR=true git -c core.editor=true rebase --continue
if [ -n "$(git diff --name-only --diff-filter=U)" ]; then
  echo "::error::Research rebase left unresolved conflicts." >&2
  git rebase --abort || true
  exit 1
fi
echo "Research checkpoint rebased while preserving the independently verified remote source."
