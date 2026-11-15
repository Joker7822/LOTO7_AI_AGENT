#!/usr/bin/env python3
"""Read-only GitHub Actions risk audit. Static heuristics are not exploit proofs."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import workflow_inventory as inventory

VERSION = "workflow-static-risk-audit-v1"


def _workflow_run_branch_filter(path: Path) -> bool:
    """Look only inside the top-level on.workflow_run block (not jobs/scripts)."""
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^  [A-Za-z_][\w-]*\s*:", line):
            active = bool(re.match(r"^  workflow_run\s*:", line))
        if active and re.match(r"^    branches\s*:", line):
            return True
    return False


def _cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Strongly connected components, including self-triggering workflows."""
    next_index = 0
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    active: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal next_index
        index[node] = low[node] = next_index
        next_index += 1
        stack.append(node)
        active.add(node)
        for previous in sorted(graph[node]):
            if previous not in index:
                visit(previous)
                low[node] = min(low[node], low[previous])
            elif previous in active:
                low[node] = min(low[node], index[previous])
        if low[node] == index[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                active.remove(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1 or node in graph[node]:
                cycles.append(sorted(component))

    for name in sorted(graph):
        if name not in index:
            visit(name)
    return sorted(cycles)


def audit(directory: Path) -> dict:
    rows = inventory.scan_workflows(directory)
    by_name = {row["name"]: row for row in rows}
    if len(by_name) != len(rows):
        raise ValueError("duplicate workflow display names")

    findings: list[dict[str, str]] = []

    def flag(severity: str, code: str, filename: str, detail: str) -> None:
        findings.append({
            "severity": severity, "code": code,
            "file": filename, "detail": detail,
        })

    graph: dict[str, set[str]] = {}
    for item in rows:
        name = item["name"]
        predecessors = set(item["workflow_run_dependencies"])
        graph[name] = predecessors.intersection(by_name)
        for missing in sorted(predecessors - by_name.keys()):
            flag("error", "UNKNOWN_WORKFLOW_RUN_TARGET", item["file"],
                 f"Unknown workflow_run name: {missing}")
        if (item["contents_write"] and item["push_in_shell"]
                and not item["has_concurrency"]):
            flag("warning", "WRITER_WITHOUT_CONCURRENCY", item["file"],
                 "Potential git push writer has no top-level concurrency policy")
        if (predecessors and item["contents_write"]
                and not _workflow_run_branch_filter(directory / item["file"])):
            flag("warning", "PRIVILEGED_WORKFLOW_RUN_WITHOUT_BRANCH_FILTER",
                 item["file"],
                 "Write-permitted workflow_run has no branch filter; review "
                 "event trust, checkout target, and consumed artifacts")

    for component in _cycles(graph):
        flag("error", "WORKFLOW_RUN_CYCLE",
             ", ".join(sorted(by_name[name]["file"] for name in component)),
             "Cycle members: " + ", ".join(component))

    findings.sort(key=lambda x: (x["severity"], x["code"], x["file"], x["detail"]))
    return {
        "version": VERSION,
        "workflow_count": len(rows),
        "error_count": sum(f["severity"] == "error" for f in findings),
        "warning_count": sum(f["severity"] == "warning" for f in findings),
        "findings": findings,
        "scope": "static_heuristic_only_no_execution_or_permissions_verification",
    }


def markdown(report: dict) -> str:
    lines = [
        "# GitHub Actions static risk audit",
        "",
        "Read-only heuristics; findings require human review. No workflows are modified.",
        "",
        f"- Workflows scanned: {report['workflow_count']}",
        f"- Graph errors: {report['error_count']}",
        f"- Warnings: {report['warning_count']}",
        "",
        "| Severity | Code | File | Detail |",
        "|---|---|---|---|",
    ]
    for row in report["findings"]:
        cells = [row[k].replace("|", "\\|").replace("\n", " ")
                 for k in ("severity", "code", "file", "detail")]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-errors", action="store_true",
                        help="Optional strict mode; never used for warnings")
    args = parser.parse_args()
    result = audit(args.workflows_dir)
    output = (json.dumps(result, ensure_ascii=False, indent=2) + "\n"
              if args.format == "json" else markdown(result))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.fail_on_errors and result["error_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
