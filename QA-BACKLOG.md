# QA Backlog — qa-manager

All items prefixed `[QA-AGENT]` were identified by automated QA runs.
Append-only — never overwrite.

---

## [QA-AGENT] Run — 2026-05-05

> Source: qa-manager skill (self-audit) | Project: ~/Claude/qa-manager
> Suites: core-unit [HIGH], policy-tests [MEDIUM]
> Tests added: 50 (47 passed / 3 failed — all failures are production bugs)

### Findings (bugs discovered)

- [ ] [QA-AGENT] **`suite-index.md` references deleted file `suites/application-security.md`** — file was removed via `git rm` during the qa-agent→qa-manager rename but suite-index was never updated. Any project with auth/security signals silently skips this suite. Fix: either restore the file or remove/replace the reference in `suite-index.md`.
  - Exposed by: `test_all_referenced_suite_files_exist` in `test_policy.py`
  - Severity: HIGH

- [ ] [QA-AGENT] **12 duplicate `.md` files in `references/` root** — exact copies of canonical files in `suites/` or `frameworks/`. Orphaned from old flat layout. SKILL.md loads from subdirs only — root copies are never read. Inflate apparent file count and mislead contributors.
  - Files: `background-workers.md`, `canvas-game.md`, `children-app.md`, `db-query-safety.md`, `fixture-factory.md`, `jest-vitest.md`, `language-agnostic.md`, `localstorage-state.md`, `playwright-cypress.md`, `pytest.md`, `speech-voice.md`, `ui-interaction.md`
  - Exposed by: `test_no_root_refs_duplicating_suites` in `test_policy.py`
  - Severity: MEDIUM

- [ ] [QA-AGENT] **`references/patterns/` is an empty directory** — created but never populated. Misleads contributors expecting pattern files there.
  - Exposed by: `test_patterns_dir_not_empty` in `test_policy.py`
  - Severity: MEDIUM

- [ ] [QA-AGENT] **2 orphaned files in `references/` root with no canonical subdir version and no suite-index entry** — `continuous-api.md` and `rest-api-contracts.md`. Not referenced in SKILL.md or suite-index.md. Either promote to `suites/` + add to suite-index, or delete.
  - Severity: MEDIUM

### Gaps (coverage missing)

- [ ] [QA-AGENT] `install.sh` inline Python heredoc (JSON manipulation via `python3 -c`) not exercised under automated test — would require mock filesystem or integration test with temp `installed_plugins.json`
- [ ] [QA-AGENT] `cmd_summary --last N` where N > total run count not tested — behavior is currently correct (returns all), but not regression-protected
- [ ] [QA-AGENT] Concurrent `cmd_start` / `cmd_finish` from two processes — shared `STATE_FILE=/tmp/claude-qa-run-state.json` would cause state corruption. Low priority (single-user CLI tool) but worth noting.

### Recommendations

- [ ] [QA-AGENT] **Fix `suite-index.md` application-security reference** — this is the highest-priority fix. Either restore `suites/application-security.md` or update suite-index to point to an existing security suite.
- [ ] [QA-AGENT] Run dead code cleanup from plan: delete 12 root duplicate files + empty `patterns/` directory + evaluate `continuous-api.md` and `rest-api-contracts.md`.
- [ ] [QA-AGENT] Add `pytest` to `CLAUDE.md` and optionally to `install.sh` as a dev dependency note — currently no documented way to run the test suite.

### Security

✅ Clean — no hardcoded credentials, no committed `.env` files, no private keys found.
