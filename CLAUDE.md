# qa-manager — Claude Code Skill

## What this is

`qa-manager` is a Claude Code skill that acts as a reusable QA auditor across any project. When invoked with `/qa-manager` or natural language like "run QA on this project", it scans the codebase, selects relevant test suites, writes tests, runs them, and produces a structured report — without ever modifying production code.

It is designed to be a **cross-project QA manager**: drop it into any project, and it knows what to test based on what's in the code.

---

## How the skill works

The skill runs an 8-phase workflow:

| Phase | What happens |
|---|---|
| Pre-flight | Announces auditor role to user — sets expectations |
| Run tracking | Notes start time, runs `log_qa_run.py start` |
| 1. Suite selection | Scans project, reads `suite-index.md`, selects relevant suites, announces them |
| 2. Read code | Reads source files and existing tests — read only |
| 3. Write tests | Creates/updates test files only — never production code |
| 4. Run tests | Runs the project's test runner, captures output |
| 5. Analyze | Diagnoses failures — fixes test issues, documents production bugs |
| 6. Report + Cost | QA Report + inline cost summary block |
| 7. QA Backlog | Appends findings to `QA-BACKLOG.md` — never touches existing backlogs |
| 8. Feedback | Collects structured feedback from user, saves to `~/.claude/qa-feedback/` |

---

## Non-negotiable skill behaviors

These are enforced at every phase in SKILL.md — do not remove or weaken them:

1. **Assessment only — never modify production code.** Test files are the only source files the skill may create or edit. Bugs found → documented, not fixed.
2. **Backlog is append-only.** `QA-BACKLOG.md` is the skill's output file. All other backlogs/docs in a project are read-only.
3. **Feedback is always collected.** Every run ends with Phase 8. Skipping it is a failed run. Feedback is saved verbatim, never acted on automatically.

---

## Directory map

```
~/Claude/qa-manager/
├── CLAUDE.md                      ← you are here
├── install.sh                     ← installer script for sharing
├── .claude-plugin/
│   └── plugin.json                ← Claude Code plugin manifest
└── skills/
    └── qa-manager/
        ├── SKILL.md               ← the skill prompt: workflow, phases, constraints
        ├── references/
        │   ├── suite-index.md     ← detection signals → suite file mapping (read this first)
        │   ├── frameworks/        ← test runner patterns (jest/vitest, pytest, playwright, generic)
        │   └── suites/            ← 53 domain-specific test suite files
        └── scripts/
            └── log_qa_run.py      ← run logger (start/finish/summary subcommands)
```

### Key files

- **`SKILL.md`** — the skill's "brain". Controls all behavior. Edit here to change how the skill works.
- **`suite-index.md`** — the detection table. Maps code signals (grep patterns, file names, deps) to suite files. The skill reads this at Phase 1 to decide which suites to load.
- **`suites/*.md`** — individual test domain files. Each covers one area (auth, payments, network, etc.) with: when to apply, what to test, code patterns, and common gaps.
- **`log_qa_run.py`** — persists run metadata to `~/.claude/qa-runs.jsonl`. Run `python3 log_qa_run.py summary` to see run history.

---

## How to add a new suite

1. Create `skills/qa-manager/references/suites/{suite-name}.md` with this structure:
   ```markdown
   # {Suite Name} Suite

   ## When to apply
   One or two sentences. What signals indicate this suite is relevant?

   ## What to test
   - Bullet list of behaviors to verify
   - Keep generic — no project-specific code

   ## Key patterns
   Code examples (language-agnostic, JS and Python variants where useful)

   ## Common gaps
   - Things teams typically miss in this area
   ```

2. Add a row to `skills/qa-manager/references/suite-index.md`:
   ```
   | {detection signal — grep pattern or file/dep name} | `suites/{suite-name}.md` |
   ```

3. Rebuild the zip (see below).

---

## How to edit an existing suite

Edit the file directly in `skills/qa-manager/references/suites/`. Changes are live immediately — this directory IS the installed skill (no cache sync needed). Rebuild the zip when done.

---

## Edit rules

- **This directory is the single source of truth.** `installed_plugins.json` points here directly.
- **No cache sync needed.** The old cache path (`~/.claude/plugins/cache/claude-plugins-official/...`) is no longer the live location.
- **Always rebuild the zip after any change:**
  ```bash
  cd /tmp && rm -rf qa-manager-skill && \
  cp -r ~/Claude/qa-manager/skills/qa-manager qa-manager-skill && \
  zip -q -r ~/Desktop/qa-manager-skill.zip qa-manager-skill
  ```
- **Suite count**: currently **53 suites** in `skills/qa-manager/references/suites/`

---

## Runtime outputs

| Output | Location |
|---|---|
| QA run log | `~/.claude/qa-runs.jsonl` |
| Feedback files | `~/.claude/qa-feedback/{date}--{project}.md` |
| Per-project backlog | `{project}/QA-BACKLOG.md` |

---

## Sharing the skill

Send `~/Desktop/qa-manager-skill.zip` to the recipient. They extract and run `install.sh` inside it. The installer copies files to `~/Claude/qa-manager/` on their machine and registers it in their `installed_plugins.json`.

---

## Suite index quick reference

See `skills/qa-manager/references/suite-index.md` for the full detection table.

**Always-on suites** (loaded regardless of project type):
- `core-unit.md` — function contracts and boundary cases
- `accessibility.md` — keyboard nav, ARIA, focus, contrast
- `appsecur.md` — auth, input safety, session management, CSRF, IDOR, security headers
- `network-conditions.md` — offline, slow network, retry behavior
