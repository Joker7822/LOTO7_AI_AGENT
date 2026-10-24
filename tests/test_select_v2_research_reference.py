"""A cached 699-only comparator must never crash/contaminate round-700 scout."""
import json
from pathlib import Path

import scripts.select_v2_research_reference as selector
from loto7_evolving_agent import fingerprint_file


def test_reuse_only_identical_registered_historical_dataset(tmp_path):
    csv = tmp_path / "history.csv"
    csv.write_text("one,round\n1,1\n", encoding="utf-8")
    ref = tmp_path / "v2.json"
    good = {"data_sha256": fingerprint_file(csv),
            "evaluated_rounds": 60,
            "last_n": 60,
            "evaluation_type": selector.KIND}
    ref.write_text(json.dumps(good), encoding="utf-8")
    assert selector.choose(csv, ref) == ref
    csv.write_text("one,round\n1,1\n2,2\n", encoding="utf-8")
    assert selector.choose(csv, ref) != ref
    assert not selector.choose(csv, ref).exists()
    ref.write_text(json.dumps({**good, "data_sha256": fingerprint_file(csv),
                               "evaluation_type": "non_prequential"}))
    assert selector.choose(csv, ref) != ref
    ref.write_text(json.dumps({**good, "data_sha256": fingerprint_file(csv),
                               "evaluated_rounds": 59}))
    assert selector.choose(csv, ref) != ref


def test_current_repository_report_is_never_implicitly_mixed(tmp_path):
    csv = Path("loto7.csv")
    old = Path("loto7_agent_output/joint_set_v2_true_nested_summary.json")
    result = selector.choose(csv, old)
    if result == old:
        assert json.loads(old.read_text())["data_sha256"] == fingerprint_file(csv)
    else:
        assert result != old and not result.exists()


def test_predictive_workflow_selects_reference_for_pr_and_schedule():
    w = Path(".github/workflows/predictive_expert_agent.yml").read_text(encoding="utf-8")
    assert w.count("python scripts/select_v2_research_reference.py") == 2
    assert w.count('--v2-summary "$v2_reference"') == 2
    assert w.count("scripts/select_v2_research_reference.py") >= 3
    assert "python predictive_expert_agent.py" in w
