"""Dependency-free issued-ticket policy used by Sakura sync and Production."""
import pytest

import production_disjoint35_policy as policy
import production_ticket_geometry35 as geometry


def rows():
    return [
        {
            "ticket": i,
            "model_version": "baseline+" + policy.VERSION,
            "predicted_numbers": " ".join(
                f"{n:02d}" for n in range(1 + (i - 1) * 7, 8 + (i - 1) * 7)
            ),
        }
        for i in range(1, 6)
    ]


def test_same_policy_is_shared_by_publisher_and_dependency_free_sync():
    assert geometry.VERSION == policy.VERSION
    assert geometry.MIN_TARGET_ROUND == policy.MIN_TARGET_ROUND == 702
    assert geometry.validate_issued_rows is policy.validate_issued_rows
    assert policy.validate_issued_rows(rows(), 702) is None


@pytest.mark.parametrize("mutation", ["overlap", "partial", "old_model", "out_of_range", "dup"])
def test_dependency_free_gate_fails_closed(mutation):
    sample = rows()
    if mutation == "overlap":
        sample[1]["predicted_numbers"] = sample[0]["predicted_numbers"]
    elif mutation == "partial":
        sample.pop()
    elif mutation == "old_model":
        sample[1]["model_version"] = "champion_original"
    elif mutation == "out_of_range":
        sample[4]["predicted_numbers"] = "29 30 31 32 33 34 38"
    else:
        sample[0]["ticket"] = 2
    with pytest.raises(ValueError):
        policy.validate_issued_rows(sample, 702)


def test_historical_701_is_not_a_disjoint_policy_target():
    with pytest.raises(ValueError, match="702"):
        policy.validate_issued_rows(rows(), 701)
