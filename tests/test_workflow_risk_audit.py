"""Regression checks for the read-only GitHub Actions risk auditor."""
from pathlib import Path

import workflow_risk_audit as audit


def write(directory: Path, name: str, body: str) -> None:
    (directory / name).write_text(body, encoding="utf-8")


def test_detects_cycles_missing_workflow_names_and_self_edges(tmp_path: Path):
    write(tmp_path, "a.yml", '''name: A
on:
  workflow_run:
    workflows: ["B", "Nonexistent"]
    types: [completed]
permissions:
  contents: read
''')
    write(tmp_path, "b.yml", '''name: B
on:
  workflow_run:
    workflows: ["A"]
    types: [completed]
''')
    write(tmp_path, "c.yml", '''name: C
on:
  workflow_run:
    workflows: ["C"]
    types: [completed]
''')
    result = audit.audit(tmp_path)
    codes = [row["code"] for row in result["findings"]]
    assert codes.count("WORKFLOW_RUN_CYCLE") == 2
    assert codes.count("UNKNOWN_WORKFLOW_RUN_TARGET") == 1
    assert result["error_count"] == 3
    assert any("A, B" in row["detail"] for row in result["findings"])
    assert any("C" in row["detail"] for row in result["findings"])


def test_writer_without_concurrency_warns_but_does_not_claim_exploit(tmp_path: Path):
    write(tmp_path, "parent.yml", "name: Parent\non:\n  workflow_dispatch:\n")
    write(tmp_path, "writer.yml", '''name: Writer
on:
  workflow_run:
    workflows: ["Parent"]
    types: [completed]
permissions:
  contents: write
jobs:
  write:
    runs-on: ubuntu-latest
    steps:
      - run: git push origin HEAD:main
''')
    result = audit.audit(tmp_path)
    assert result["error_count"] == 0
    codes = {row["code"] for row in result["findings"]}
    assert "WRITER_WITHOUT_CONCURRENCY" in codes
    assert "PRIVILEGED_WORKFLOW_RUN_WITHOUT_BRANCH_FILTER" in codes
    assert "static_heuristic" in result["scope"]


def test_branch_filter_and_concurrency_remove_writer_warnings(tmp_path: Path):
    write(tmp_path, "parent.yml", "name: Parent\non:\n  workflow_dispatch:\n")
    write(tmp_path, "writer.yml", '''name: Writer
on:
  workflow_run:
    workflows: ["Parent"]
    branches: [main]
permissions:
  contents: write
concurrency:
  group: writer
  cancel-in-progress: false
jobs:
  write:
    runs-on: ubuntu-latest
    steps:
      - run: git push origin HEAD:main
''')
    result = audit.audit(tmp_path)
    assert result["error_count"] == 0
    assert result["warning_count"] == 0


def test_duplicate_workflow_name_is_error(tmp_path: Path):
    import pytest

    write(tmp_path, "a.yml", "name: Example\non:\n  workflow_dispatch:\n")
    write(tmp_path, "b.yml", "name: Example\non:\n  workflow_dispatch:\n")
    with pytest.raises(ValueError, match="duplicate workflow"):
        audit.audit(tmp_path)


def test_report_is_read_only_and_markdown_is_human_reviewable(tmp_path: Path):
    write(tmp_path, "a.yml", "name: A\non:\n  workflow_dispatch:\n")
    before = (tmp_path / "a.yml").read_bytes()
    result = audit.audit(tmp_path)
    text = audit.markdown(result)
    assert result["workflow_count"] == 1
    assert "| Severity | Code | File | Detail |" in text
    assert (tmp_path / "a.yml").read_bytes() == before


def test_real_workflows_can_be_audited_without_modification():
    # Not a requirement for zero warnings: existing workflows may need review.
    import json

    folder = Path(".github/workflows")
    before = {p.name: p.read_bytes() for p in folder.glob("*.yml")}
    result = audit.audit(folder)
    assert result["workflow_count"] >= 49
    assert result["version"] == audit.VERSION
    assert isinstance(result["findings"], list)
    json.dumps(result, allow_nan=False)
    assert before == {p.name: p.read_bytes() for p in folder.glob("*.yml")}
