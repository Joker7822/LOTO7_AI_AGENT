#!/usr/bin/env bash
# Preserve historical 699 regression expectations without downgrading actual
# round-700 evidence, production tickets, or registered prospective ledgers.
set -euo pipefail

PIN="8928cb2e3ef3496e1ad8b6c02b0c3c402beef38b"
ROOT="$(git rev-parse --show-toplevel)"
git -C "$ROOT" cat-file -e "$PIN^{commit}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Run current code/tests with source-controlled 699 reference DATA only inside
# an ephemeral test directory. No git reset/checkout on the production tree.
git -C "$ROOT" archive --format=tar HEAD | tar -xf - -C "$WORK"
rm -rf "$WORK/loto7_agent_output" "$WORK/loto7.csv"
git -C "$ROOT" archive --format=tar "$PIN" loto7.csv loto7_agent_output | tar -xf - -C "$WORK"

python - "$WORK" <<'PY'
import hashlib
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
data = (root / "loto7.csv").read_bytes()
assert hashlib.sha256(data).hexdigest() == (
    "5e4fa6fcc544604e52d591b75076365ff190664ecc508f853f27671f8af595cf"
), "historical regression fixture SHA drift"
assert json.loads((root / "loto7_agent_output/source_validation.json").read_text())["latest"]["round"] == 699
assert json.loads((root / "loto7_agent_output/future_holdout_state.json").read_text())["all_draws"] == 7
print("Running current source-code tests against pinned 699 evidence fixture")
PY
(
  cd "$WORK"
  python -m pytest -q
)
