from __future__ import annotations

import pytest

from joint_set_parallel_null import assigned_world_indices, merge_world_records, state_identity


def test_assigned_world_indices_partition_all_missing_without_overlap() -> None:
    completed = {1, 4, 9}
    shards = [assigned_world_indices(16, completed, i, 4) for i in range(4)]
    flat = [x for shard in shards for x in shard]
    assert sorted(flat) == [i for i in range(1, 17) if i not in completed]
    assert len(flat) == len(set(flat))


def test_assigned_world_indices_validates_shard_bounds() -> None:
    with pytest.raises(ValueError):
        assigned_world_indices(8, [], 0, 0)
    with pytest.raises(ValueError):
        assigned_world_indices(8, [], 4, 4)


def test_merge_world_records_is_sorted_and_idempotent() -> None:
    existing = [{"world": 2, "seed": 22, "score_delta_vs_random": 0.1}]
    fragments = [
        [{"world": 1, "seed": 11, "score_delta_vs_random": -0.1}],
        [{"world": 2, "seed": 22, "score_delta_vs_random": 0.1}, {"world": 3, "seed": 33, "score_delta_vs_random": 0.2}],
    ]
    merged = merge_world_records(existing, fragments, 3)
    assert [row["world"] for row in merged] == [1, 2, 3]


def test_merge_world_records_rejects_conflict() -> None:
    existing = [{"world": 1, "seed": 11, "score_delta_vs_random": 0.1}]
    fragments = [[{"world": 1, "seed": 11, "score_delta_vs_random": 0.2}]]
    with pytest.raises(ValueError, match="conflicting results"):
        merge_world_records(existing, fragments, 4)


def test_state_identity_excludes_world_payload_only() -> None:
    state = {"report_version": "x", "target_worlds": 64, "worlds": [{"world": 1}]}
    assert state_identity(state) == {"report_version": "x", "target_worlds": 64}
