#!/usr/bin/env python3
"""
Policy tests for qa-manager project.
Source-scan checks — no dependencies, run in milliseconds.
Run: pytest skills/qa-manager/scripts/test_policy.py -v
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # ~/Claude/qa-manager
SKILL_DIR = ROOT / "skills" / "qa-manager"
SCRIPTS_DIR = SKILL_DIR / "scripts"
SUITES_DIR = SKILL_DIR / "references" / "suites"
FRAMEWORKS_DIR = SKILL_DIR / "references" / "frameworks"
SUITE_INDEX = SKILL_DIR / "references" / "suite-index.md"
SKILL_MD = SKILL_DIR / "SKILL.md"
INSTALL_SH = ROOT / "install.sh"


# ── install.sh policy ─────────────────────────────────────────────────────────

class TestInstallSh:
    def test_install_sh_exists(self):
        assert INSTALL_SH.exists(), "install.sh missing"

    def test_install_sh_is_executable(self):
        assert os.access(INSTALL_SH, os.X_OK), "install.sh not executable"

    def test_install_sh_has_set_e(self):
        content = INSTALL_SH.read_text()
        assert "set -e" in content, "install.sh must use 'set -e' to fail on errors"

    def test_install_sh_no_hardcoded_tokens(self):
        content = INSTALL_SH.read_text()
        # No API keys or tokens hardcoded
        assert not re.search(
            r'(api_key|token|secret|password)\s*=\s*["\'][^"\']{8,}',
            content, re.IGNORECASE
        ), "install.sh contains a potential hardcoded secret"

    def test_install_sh_creates_feedback_dir(self):
        content = INSTALL_SH.read_text()
        assert "qa-feedback" in content, \
            "install.sh must create ~/.claude/qa-feedback/ directory"

    def test_install_sh_registers_plugin(self):
        content = INSTALL_SH.read_text()
        assert "installed_plugins.json" in content, \
            "install.sh must register plugin in installed_plugins.json"


# ── log_qa_run.py policy ──────────────────────────────────────────────────────

class TestLogQaRunPolicy:
    def test_log_qa_run_exists(self):
        assert (SCRIPTS_DIR / "log_qa_run.py").exists()

    def test_no_hardcoded_credentials(self):
        content = (SCRIPTS_DIR / "log_qa_run.py").read_text()
        assert not re.search(
            r'(api_key|token|secret|password)\s*=\s*["\'][^"\']{8,}',
            content, re.IGNORECASE
        ), "log_qa_run.py contains a potential hardcoded secret"

    def test_log_file_in_home_claude_dir(self):
        """Log file must write to ~/.claude/ not to a project dir."""
        content = (SCRIPTS_DIR / "log_qa_run.py").read_text()
        assert 'Path.home() / ".claude"' in content, \
            "LOG_FILE must resolve to ~/.claude/qa-runs.jsonl"

    def test_state_file_in_tmp(self):
        """State file must be in /tmp to avoid polluting project dirs."""
        content = (SCRIPTS_DIR / "log_qa_run.py").read_text()
        assert '"/tmp/' in content, \
            "STATE_FILE must be in /tmp"

    def test_has_start_finish_summary_subcommands(self):
        content = (SCRIPTS_DIR / "log_qa_run.py").read_text()
        for cmd in ["start", "finish", "summary"]:
            assert f'sub.add_parser("{cmd}")' in content, \
                f"Missing subcommand: {cmd}"


# ── suite index integrity ─────────────────────────────────────────────────────

class TestSuiteIndex:
    def test_suite_index_exists(self):
        assert SUITE_INDEX.exists(), "suite-index.md missing"

    def test_all_referenced_suite_files_exist(self):
        """Every suites/X.md referenced in suite-index.md must actually exist."""
        content = SUITE_INDEX.read_text()
        # Extract all `suites/xxx.md` references
        refs = re.findall(r'`(suites/[^`]+\.md)`', content)
        missing = []
        for ref in refs:
            target = SKILL_DIR / "references" / ref
            if not target.exists():
                missing.append(ref)
        assert not missing, f"suite-index references non-existent files: {missing}"

    def test_all_suite_files_in_index(self):
        """Every .md in suites/ should be referenced in suite-index.md (or intentional)."""
        content = SUITE_INDEX.read_text()
        suite_files = [f.name for f in SUITES_DIR.glob("*.md")]
        unindexed = []
        for fname in suite_files:
            if fname not in content:
                unindexed.append(fname)
        assert not unindexed, \
            f"Suite files not referenced in suite-index.md: {unindexed}"

    def test_no_duplicate_suite_references(self):
        """Each suite should appear at most once in suite-index.md."""
        content = SUITE_INDEX.read_text()
        refs = re.findall(r'`(suites/[^`]+\.md)`', content)
        seen = {}
        dupes = []
        for ref in refs:
            seen[ref] = seen.get(ref, 0) + 1
            if seen[ref] == 2:
                dupes.append(ref)
        assert not dupes, f"Duplicate suite references in suite-index.md: {dupes}"


# ── SKILL.md integrity ────────────────────────────────────────────────────────

class TestSkillMd:
    def test_skill_md_exists(self):
        assert SKILL_MD.exists(), "SKILL.md missing"

    def test_all_8_phases_present(self):
        content = SKILL_MD.read_text()
        for i in range(8):
            assert f"Phase {i}" in content or f"## Phase {i+1}" in content or \
                   f"Phase {i+1}" in content, \
                f"Phase {i+1} missing from SKILL.md"

    def test_constraint_1_present(self):
        content = SKILL_MD.read_text()
        assert "CONSTRAINT 1" in content, \
            "CONSTRAINT 1 (read-only on production code) must be present in SKILL.md"

    def test_no_hardcoded_project_paths(self):
        """SKILL.md must not hardcode specific project paths (would break cross-project use)."""
        content = SKILL_MD.read_text()
        # Should not contain absolute paths to specific user projects
        # (qa-manager's own path is OK; other project paths are not)
        bad_paths = re.findall(r'/Users/[^/]+/Claude/(?!qa-manager)[^\s"\'`\)]+', content)
        # Filter out paths that are in code blocks as examples
        assert not bad_paths, \
            f"SKILL.md contains hardcoded project paths: {bad_paths}"

    def test_wisdom_files_referenced(self):
        content = SKILL_MD.read_text()
        assert "anti-patterns.md" in content, \
            "SKILL.md must reference anti-patterns.md"
        assert "failure-playbook.md" in content, \
            "SKILL.md must reference failure-playbook.md"

    def test_log_qa_run_invocations_present(self):
        content = SKILL_MD.read_text()
        assert "log_qa_run.py start" in content, "Phase 0 must invoke log_qa_run.py start"
        assert "log_qa_run.py finish" in content, "Phase 6 must invoke log_qa_run.py finish"


# ── no duplicate root-level reference files ───────────────────────────────────

class TestNoDuplicateReferenceFiles:
    def test_no_root_refs_duplicating_suites(self):
        """Files in references/ root that duplicate suites/ are dead code."""
        root_refs = {f.name for f in (SKILL_DIR / "references").glob("*.md")
                     if f.name not in ("suite-index.md",)}
        suite_files = {f.name for f in SUITES_DIR.glob("*.md")}
        framework_files = {f.name for f in FRAMEWORKS_DIR.glob("*.md")}
        canonical = suite_files | framework_files
        dupes = root_refs & canonical
        assert not dupes, (
            f"Duplicate files in references/ root (also exist in suites/ or frameworks/): {sorted(dupes)}. "
            f"Delete the root copies — suites/ and frameworks/ are canonical."
        )

    def test_patterns_dir_not_empty(self):
        """references/patterns/ exists but is empty — either populate or remove."""
        patterns_dir = SKILL_DIR / "references" / "patterns"
        if patterns_dir.exists():
            contents = list(patterns_dir.iterdir())
            assert contents, (
                "references/patterns/ is empty. Either add pattern files or remove the directory."
            )


# ── import needed for executable test ────────────────────────────────────────
import os
