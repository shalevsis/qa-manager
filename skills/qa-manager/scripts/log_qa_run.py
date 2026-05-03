#!/usr/bin/env python3
"""
QA Run Logger — call this at the start and end of every qa-manager session.

Usage:
    python3 log_qa_run.py start --project /path/to/project
    python3 log_qa_run.py finish --project /path/to/project \
        --files-tested 3 --tests-written 18 --tests-passed 17 --tests-failed 1 \
        --frameworks pytest --notes "Found flaky boundary test"

Log file: ~/.claude/qa-runs.jsonl (one JSON object per line)
View log: python3 log_qa_run.py summary
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "qa-runs.jsonl"
STATE_FILE = Path("/tmp/claude-qa-run-state.json")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def cmd_start(args):
    state = {
        "start_time": time.time(),
        "start_iso": now_iso(),
        "project": args.project or os.getcwd(),
    }
    STATE_FILE.write_text(json.dumps(state))
    print(f"QA run started at {state['start_iso']} in {state['project']}")


def cmd_finish(args):
    end_time = time.time()
    end_iso = now_iso()

    # Load start state
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        duration_s = round(end_time - state["start_time"], 1)
        start_iso = state["start_iso"]
        project = args.project or state.get("project", os.getcwd())
    else:
        duration_s = None
        start_iso = None
        project = args.project or os.getcwd()

    entry = {
        "timestamp": end_iso,
        "project": project,
        "duration_seconds": duration_s,
        "start_time": start_iso,
        "end_time": end_iso,
        "frameworks": args.frameworks or [],
        "files_tested": args.files_tested or 0,
        "tests_written": args.tests_written or 0,
        "tests_passed": args.tests_passed or 0,
        "tests_failed": args.tests_failed or 0,
        "coverage_pct": args.coverage,
        "status": "failed" if (args.tests_failed or 0) > 0 else "passed",
        "notes": args.notes or "",
    }

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if STATE_FILE.exists():
        STATE_FILE.unlink()

    # Print summary
    duration_str = f"{duration_s}s" if duration_s else "unknown"
    status_icon = "✅" if entry["status"] == "passed" else "⚠️"
    print(f"\n{status_icon} QA Run Complete")
    print(f"  Project:  {project}")
    print(f"  Duration: {duration_str}")
    print(f"  Tests:    {entry['tests_written']} written, "
          f"{entry['tests_passed']} passed, {entry['tests_failed']} failed")
    if entry["coverage_pct"] is not None:
        print(f"  Coverage: {entry['coverage_pct']}%")
    if entry["notes"]:
        print(f"  Notes:    {entry['notes']}")
    print(f"  Logged → {LOG_FILE}")


def cmd_summary(args):
    if not LOG_FILE.exists():
        print("No QA runs logged yet.")
        return

    runs = [json.loads(line) for line in LOG_FILE.read_text().splitlines() if line.strip()]
    n = args.last or len(runs)
    runs = runs[-n:]

    if not runs:
        print("No QA runs found.")
        return

    print(f"\n{'─'*70}")
    print(f"  QA Run History (last {len(runs)} runs)")
    print(f"{'─'*70}")

    total_tests = 0
    total_duration = 0
    projects = set()

    for r in runs:
        ts = r.get("timestamp", "")[:16].replace("T", " ")
        proj = Path(r.get("project", "")).name or r.get("project", "?")
        dur = f"{r.get('duration_seconds', '?')}s"
        tw = r.get("tests_written", 0)
        tp = r.get("tests_passed", 0)
        tf = r.get("tests_failed", 0)
        cov = f" {r.get('coverage_pct')}%" if r.get("coverage_pct") else ""
        icon = "✅" if r.get("status") == "passed" else "⚠️"
        fw = ", ".join(r.get("frameworks", [])) or "?"
        print(f"  {icon} {ts}  {proj:<20} {dur:>6}  "
              f"{tw} written / {tp} passed / {tf} failed{cov}  [{fw}]")
        if r.get("notes"):
            print(f"       └─ {r['notes']}")

        total_tests += tw
        if r.get("duration_seconds"):
            total_duration += r["duration_seconds"]
        projects.add(r.get("project", ""))

    print(f"{'─'*70}")
    print(f"  Totals: {len(runs)} runs | {total_tests} tests written | "
          f"{round(total_duration)}s total | {len(projects)} projects")
    print(f"{'─'*70}\n")


def main():
    parser = argparse.ArgumentParser(description="QA Run Logger")
    sub = parser.add_subparsers(dest="cmd")

    p_start = sub.add_parser("start")
    p_start.add_argument("--project", default=None)

    p_finish = sub.add_parser("finish")
    p_finish.add_argument("--project", default=None)
    p_finish.add_argument("--files-tested", type=int, default=0)
    p_finish.add_argument("--tests-written", type=int, default=0)
    p_finish.add_argument("--tests-passed", type=int, default=0)
    p_finish.add_argument("--tests-failed", type=int, default=0)
    p_finish.add_argument("--coverage", type=float, default=None)
    p_finish.add_argument("--frameworks", nargs="*", default=[])
    p_finish.add_argument("--notes", default="")

    p_summary = sub.add_parser("summary")
    p_summary.add_argument("--last", type=int, default=None)

    args = parser.parse_args()
    if args.cmd == "start":
        cmd_start(args)
    elif args.cmd == "finish":
        cmd_finish(args)
    elif args.cmd == "summary":
        cmd_summary(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
