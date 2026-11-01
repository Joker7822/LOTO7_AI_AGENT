#!/usr/bin/env python3
"""Static workflow-trigger/dependency inventory; no GitHub API or write operations."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

NAME = re.compile(r"^name:\s*(.+)$")
CRON = re.compile(r"^\s*-\s*cron:\s*['\"]?([^'\"]+)['\"]?\s*(?:#.*)?$")
WORKFLOW_ENTRY = re.compile(r"^\s{6}-\s*['\"]?(.+?)['\"]?\s*$")


def scan_workflows(directory: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted((*directory.glob("*.yml"), *directory.glob("*.yaml"))):
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        match = next((NAME.match(line) for line in lines if NAME.match(line)), None)
        name = match.group(1).strip().strip("'\"") if match else path.stem
        crons = []
        dependencies = []
        triggers = []
        active_trigger = None
        in_workflow_names = False
        for line in lines:
            if line.startswith("  ") and not line.startswith("   ") and line.strip().endswith(":"):
                head = line.strip()[:-1]
                active_trigger = head if head in ("push", "pull_request", "schedule",
                                                  "workflow_run", "workflow_dispatch") else None
                if active_trigger and active_trigger not in triggers:
                    triggers.append(active_trigger)
                in_workflow_names = False
            if line.startswith("    workflows:") and active_trigger == "workflow_run":
                payload = line.split(":", 1)[1].strip()
                if payload.startswith("[") and payload.endswith("]"):
                    values = next(csv.reader([payload[1:-1]], skipinitialspace=True))
                    dependencies.extend(value.strip().strip("'\"") for value in values if value.strip())
                    in_workflow_names = False
                else:
                    in_workflow_names = True
                continue
            if in_workflow_names and not line.startswith("      ") and line.strip():
                in_workflow_names = False
            if in_workflow_names:
                item = WORKFLOW_ENTRY.match(line)
                if item:
                    dependencies.append(item.group(1).strip().strip("'\""))
            if active_trigger == "schedule":
                cron = CRON.match(line)
                if cron:
                    crons.append(cron.group(1).strip())
        rows.append({
            "file": path.name, "name": name, "triggers": triggers,
            "cron": crons, "workflow_run_dependencies": dependencies,
            "contents_write": bool(re.search(r"^\s+contents:\s*write\s*$", content, re.M)),
            "push_in_shell": bool(re.search(r"\bgit\s+push\b", content)),
            "has_concurrency": bool(re.search(r"^concurrency:\s*$", content, re.M)),
        })
    return rows


def report(rows: list[dict]) -> str:
    names = {x["name"] for x in rows}
    if len(names) != len(rows):
        raise ValueError("duplicate workflow display names")
    dependents = {name: [] for name in names}
    unknown = []
    for workflow in rows:
        for predecessor in workflow["workflow_run_dependencies"]:
            if predecessor in dependents:
                dependents[predecessor].append(workflow["name"])
            else:
                unknown.append((workflow["file"], predecessor))
    lines = [
        "# GitHub Actions トリガー・依存関係の棚卸し",
        "",
        "> 静的構文検査です。workflow_runはワークフロー名で参照します。"
        " GitHub Pagesの内蔵デプロイは含まれません。",
        f"- workflow数: **{len(rows)}**",
        f"- 定期cronを持つworkflow: **{sum(bool(x['cron']) for x in rows)}**",
        f"- workflow_runで連携するworkflow: **{sum(bool(x['workflow_run_dependencies']) for x in rows)}**",
        f"- contents:writeを宣言するworkflow: **{sum(x['contents_write'] for x in rows)}**",
        f"- git pushを含むworkflow: **{sum(x['push_in_shell'] for x in rows)}**",
        f"- 参照先が見つからないworkflow_run: **{len(unknown)}**",
        "",
        "## 更新頻度・依存関係",
        "",
        "| ファイル | cron (UTC) | workflow_run先行処理数 | 下流に持つ処理数 | main書込の可能性 |",
        "|---|---|---:|---:|---|",
    ]
    for x in rows:
        crons = ", ".join(x["cron"]) or "—"
        lines.append(f"| {x['file']} | {crons} | {len(x['workflow_run_dependencies'])} | "
                     f"{len(dependents.get(x['name'], []))} | "
                     f"{'git pushあり' if x['push_in_shell'] else '静的検出なし'} |")
    lines.extend(["", "## 運用上の扱い",
                  "- 本番・当せん結果照合・将来OOSは変更せず、読み取り専用ダッシュボードの"
                  "通知ファンアウトだけを削減します。",
                  "- 公開データの定期更新は30分間隔。新しい照合済み抽せんと本番発行だけ"
                  "即時スナップショット要求を維持します。",
                  "- GitHub Pagesの内蔵ブランチデプロイはmainの更新全体で起動し得ます。"
                  "定期更新削減だけでは競合の完全解消を保証しません。",
                  "- contents:writeとgit pushは静的監査指標であり、"
                  "実際の権限昇格・デプロイ実績の証明ではありません。",
                  ""])
    if unknown:
        lines.extend(["## 未解決の参照", ""])
        lines.extend(f"- {p}: {name}" for p, name in unknown)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflows-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = scan_workflows(args.workflows_dir)
    output = (json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
              if args.format == "json" else report(rows))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
