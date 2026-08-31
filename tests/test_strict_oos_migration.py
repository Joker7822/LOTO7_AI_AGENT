import json
from pathlib import Path

import numpy as np
import pandas as pd

import loto7_v4_runner as v4
import strict_oos_migration as migration


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


class DummyV4:
    e_key = staticmethod(v4.e_key)
    parse_round = staticmethod(v4.parse_round)
    now_jst = staticmethod(lambda: "2026-08-31T13:00:00+09:00")

    @staticmethod
    def read_csv_flexible(path):
        return object()

    @staticmethod
    def make_history(df):
        x = np.zeros((692, 37), dtype=int)
        clean = pd.DataFrame({"回別": [f"第{i}回" for i in range(1, 693)]})
        return x, clean


def test_migration_archives_legacy_unpaired_draw_and_restarts_at_693(tmp_path: Path):
    out = tmp_path / "out"
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text("placeholder", encoding="utf-8")
    write(out / "shadow_registry.json", {
        "target_round": 693,
        "champion_version": "champ",
    })
    write(out / "formal_challenger_state.json", {
        "candidate_version": "cand",
        "champion_version": "champ",
        "trusted_draws_so_far": 1,
        "last_observed_round": 692,
    })
    write(out / "oos_candidate_state.json", {
        "graded_rounds": [692],
        "evidence": {
            v4.e_key("cand", "champ"): {
                "candidate_version": "cand",
                "champion_version": "champ",
                "trusted_draws": 1,
                "sum_delta": 0.0,
                "wins": 0,
                "e_components": {"0.1": 1.0},
                "e_value": 1.0,
                "last_round": 692,
            }
        },
    })

    result = migration.migrate(DummyV4, [
        "--csv", str(csv_path),
        "--out-dir", str(out),
        "--shadow-registry", str(out / "shadow_registry.json"),
    ])
    assert result["migrated"] is True
    assert result["evidence_reset"] is True
    assert result["legacy_trusted_draws"] == 1
    assert result["strict_start_target_round"] == 693

    oos = json.loads((out / "oos_candidate_state.json").read_text())
    assert oos["evidence"] == {}
    assert oos["legacy_pre_strict_evidence"]["through_round"] == 692
    assert oos["strict_evidence_legacy_draws_discarded_from_promotion"] == 1
    formal = json.loads((out / "formal_challenger_state.json").read_text())
    assert formal["trusted_draws_so_far"] == 0
    assert formal["last_observed_round"] is None
    assert formal["strict_evidence_start_target_round"] == 693

    # Migration is one-shot and cannot reset new strict evidence later.
    second = migration.migrate(DummyV4, [
        "--csv", str(csv_path),
        "--out-dir", str(out),
        "--shadow-registry", str(out / "shadow_registry.json"),
    ])
    assert second["reason"] == "already_migrated"
