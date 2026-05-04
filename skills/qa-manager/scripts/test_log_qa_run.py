#!/usr/bin/env python3
"""
Tests for log_qa_run.py — QA run logger
Run: pytest skills/qa-manager/scripts/test_log_qa_run.py -v
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest import mock
import pytest

# ── import the module under test ──────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
import log_qa_run as lqr


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_paths(tmp_path):
    """Redirect LOG_FILE and STATE_FILE to tmp dirs so tests never touch real files."""
    log_file = tmp_path / "qa-runs.jsonl"
    state_file = tmp_path / "qa-run-state.json"
    with mock.patch.object(lqr, "LOG_FILE", log_file), \
         mock.patch.object(lqr, "STATE_FILE", state_file):
        yield {"log": log_file, "state": state_file}


def make_args(**kwargs):
    """Build a Namespace object for cmd_start / cmd_finish / cmd_summary."""
    from argparse import Namespace
    defaults = {
        "project": "/test/project",
        "files_tested": 0,
        "tests_written": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "coverage": None,
        "frameworks": [],
        "notes": "",
        "last": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


# ── cmd_start ─────────────────────────────────────────────────────────────────

class TestCmdStart:
    def test_creates_state_file(self, isolated_paths):
        lqr.cmd_start(make_args(project="/my/proj"))
        assert isolated_paths["state"].exists()

    def test_state_contains_project(self, isolated_paths):
        lqr.cmd_start(make_args(project="/my/proj"))
        state = json.loads(isolated_paths["state"].read_text())
        assert state["project"] == "/my/proj"

    def test_state_contains_start_time(self, isolated_paths):
        before = time.time()
        lqr.cmd_start(make_args(project="/any"))
        after = time.time()
        state = json.loads(isolated_paths["state"].read_text())
        assert before <= state["start_time"] <= after

    def test_state_contains_iso_timestamp(self, isolated_paths):
        lqr.cmd_start(make_args(project="/any"))
        state = json.loads(isolated_paths["state"].read_text())
        # ISO 8601 with timezone offset
        assert "T" in state["start_iso"]
        assert state["start_iso"].endswith("+00:00") or "Z" in state["start_iso"]

    def test_prints_confirmation(self, isolated_paths, capsys):
        lqr.cmd_start(make_args(project="/my/proj"))
        out = capsys.readouterr().out
        assert "/my/proj" in out


# ── cmd_finish ────────────────────────────────────────────────────────────────

class TestCmdFinish:
    def test_writes_jsonl_entry(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(
            project="/proj", tests_written=5, tests_passed=4,
            tests_failed=1, frameworks=["pytest"], notes="all good"
        ))
        lines = isolated_paths["log"].read_text().splitlines()
        assert len(lines) == 1

    def test_entry_fields_correct(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(
            project="/proj", tests_written=10, tests_passed=10,
            tests_failed=0, frameworks=["vitest"], notes="clean run"
        ))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["tests_written"] == 10
        assert entry["tests_passed"] == 10
        assert entry["tests_failed"] == 0
        assert entry["frameworks"] == ["vitest"]
        assert entry["notes"] == "clean run"
        assert entry["project"] == "/proj"

    def test_status_passed_when_zero_failures(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(project="/proj", tests_failed=0))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["status"] == "passed"

    def test_status_failed_when_nonzero_failures(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(project="/proj", tests_failed=1))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["status"] == "failed"

    def test_duration_is_positive(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        time.sleep(0.05)  # small but real gap
        lqr.cmd_finish(make_args(project="/proj"))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["duration_seconds"] > 0

    def test_multiple_runs_append(self, isolated_paths):
        for i in range(3):
            lqr.cmd_start(make_args(project=f"/proj{i}"))
            lqr.cmd_finish(make_args(project=f"/proj{i}", tests_written=i))
        lines = isolated_paths["log"].read_text().splitlines()
        assert len(lines) == 3

    def test_finish_without_prior_start_still_writes(self, isolated_paths):
        """cmd_finish must not crash if state file is missing (no prior start)."""
        # No cmd_start called — state file absent
        lqr.cmd_finish(make_args(project="/proj", tests_written=1))
        assert isolated_paths["log"].exists()
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["tests_written"] == 1
        # duration should be None when no state
        assert entry["duration_seconds"] is None

    def test_state_file_deleted_after_finish(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        assert isolated_paths["state"].exists()
        lqr.cmd_finish(make_args(project="/proj"))
        assert not isolated_paths["state"].exists()

    def test_coverage_stored_as_float(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(project="/proj", coverage=84.5))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["coverage_pct"] == 84.5

    def test_coverage_none_when_not_provided(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(project="/proj", coverage=None))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["coverage_pct"] is None


# ── cmd_summary ───────────────────────────────────────────────────────────────

class TestCmdSummary:
    def _seed(self, isolated_paths, n=3):
        """Write n valid log entries directly."""
        entries = []
        for i in range(n):
            e = {
                "timestamp": f"2026-05-0{i+1}T10:00:00+00:00",
                "project": f"/project/{i}",
                "duration_seconds": 10.0 + i,
                "start_time": f"2026-05-0{i+1}T09:59:50+00:00",
                "end_time": f"2026-05-0{i+1}T10:00:00+00:00",
                "frameworks": ["pytest"],
                "files_tested": 2,
                "tests_written": 5 + i,
                "tests_passed": 5 + i,
                "tests_failed": 0,
                "coverage_pct": None,
                "status": "passed",
                "notes": f"run {i}",
            }
            entries.append(e)
        isolated_paths["log"].write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )
        return entries

    def test_no_crash_when_log_missing(self, isolated_paths, capsys):
        lqr.cmd_summary(make_args(last=None))
        out = capsys.readouterr().out
        assert "No QA runs" in out

    def test_shows_all_entries_by_default(self, isolated_paths, capsys):
        self._seed(isolated_paths, n=3)
        lqr.cmd_summary(make_args(last=None))
        out = capsys.readouterr().out
        assert "3 runs" in out

    def test_last_n_limits_output(self, isolated_paths, capsys):
        self._seed(isolated_paths, n=5)
        lqr.cmd_summary(make_args(last=2))
        out = capsys.readouterr().out
        # Should say "last 2 runs"
        assert "2" in out

    def test_totals_line_present(self, isolated_paths, capsys):
        self._seed(isolated_paths, n=2)
        lqr.cmd_summary(make_args(last=None))
        out = capsys.readouterr().out
        assert "Totals" in out

    def test_handles_empty_log_file(self, isolated_paths, capsys):
        isolated_paths["log"].write_text("")
        lqr.cmd_summary(make_args(last=None))
        out = capsys.readouterr().out
        assert "No QA runs" in out

    def test_shows_check_icon_for_passed(self, isolated_paths, capsys):
        self._seed(isolated_paths, n=1)
        lqr.cmd_summary(make_args(last=None))
        out = capsys.readouterr().out
        assert "✅" in out

    def test_shows_warn_icon_for_failed(self, isolated_paths, capsys):
        entry = {
            "timestamp": "2026-05-01T10:00:00+00:00",
            "project": "/proj",
            "duration_seconds": 5.0,
            "frameworks": [],
            "tests_written": 1,
            "tests_passed": 0,
            "tests_failed": 1,
            "status": "failed",
            "notes": "",
        }
        isolated_paths["log"].write_text(json.dumps(entry) + "\n")
        lqr.cmd_summary(make_args(last=None))
        out = capsys.readouterr().out
        assert "⚠️" in out


# ── edge cases / boundary ─────────────────────────────────────────────────────

class TestEdgeCases:
    def test_finish_with_zero_tests_written(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(project="/proj", tests_written=0,
                                  tests_passed=0, tests_failed=0))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["tests_written"] == 0
        assert entry["status"] == "passed"

    def test_finish_large_test_counts(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(project="/proj", tests_written=10000,
                                  tests_passed=9999, tests_failed=1))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["tests_written"] == 10000
        assert entry["status"] == "failed"

    def test_project_path_with_spaces(self, isolated_paths):
        lqr.cmd_start(make_args(project="/Users/me/My Projects/app"))
        lqr.cmd_finish(make_args(project="/Users/me/My Projects/app"))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["project"] == "/Users/me/My Projects/app"

    def test_notes_with_special_chars(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        notes = 'Found bug: "null" key → crash'
        lqr.cmd_finish(make_args(project="/proj", notes=notes))
        # must round-trip through JSON correctly
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["notes"] == notes

    def test_multiple_frameworks(self, isolated_paths):
        lqr.cmd_start(make_args(project="/proj"))
        lqr.cmd_finish(make_args(project="/proj", frameworks=["pytest", "bash", "tsx"]))
        entry = json.loads(isolated_paths["log"].read_text())
        assert entry["frameworks"] == ["pytest", "bash", "tsx"]
