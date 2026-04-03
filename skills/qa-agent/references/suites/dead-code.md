# Dead Code & Obsolete Code Suite

## When to apply
Apply to any codebase undergoing active development, refactoring, or feature rework. This suite uses static analysis and grep patterns — not runtime tests. Run it as a code review / audit step. Detect candidates with: unused imports, unreachable statements, commented-out blocks, TODO/FIXME/deprecated markers, feature flags hardcoded to a constant value.

## What to test

- Functions defined but never called anywhere in the codebase (orphaned functions)
- Imports that are never referenced in the file they appear in
- Variables assigned but never read after assignment
- Code after a `return`, `raise`, `throw`, or `exit` statement (unreachable)
- Commented-out code blocks longer than 3 lines (should be deleted or turned into a ticket)
- Feature flags or constants that are always `True`/`False` — the branch they guard is effectively dead
- Classes or modules that were entry points for features that no longer exist
- Event handlers registered for events that are never emitted
- API endpoints defined in routes but not called by any client code or test
- Database columns or fields present in schema but never read or written by application code
- CSS classes defined in stylesheets but not referenced in any template or component
- Config keys present in config files but never accessed in application code

## Key patterns

**Grep: unreachable code after return**
```
# Python
grep -rn "return\|raise\|sys.exit" --include="*.py" | \
  # manual review: any non-blank, non-comment line after these in the same block
```

**Grep: commented-out code blocks**
```bash
# Large commented blocks (heuristic: 3+ consecutive comment lines with code-like content)
grep -rn "^[ \t]*#.*[=\(\)\[\]\{\}]" --include="*.py" -A2 | \
  grep -c "^--$"  # count block breaks
```

**Grep: TODO/FIXME/deprecated markers**
```bash
grep -rn "TODO\|FIXME\|DEPRECATED\|HACK\|XXX\|REMOVEME" \
  --include="*.py" --include="*.ts" --include="*.js" \
  | sort | tee dead-code-report.txt
```

**Grep: feature flags hardcoded**
```bash
grep -rn "FEATURE_.*= True\|FEATURE_.*= False\|FF_.*= true\|FF_.*= false" \
  --include="*.py" --include="*.ts" --include="*.js"
```

**Static analysis tools**
```bash
# Python
python3 -m vulture .              # finds unused code
python3 -m pylint --disable=all --enable=W0611 .  # unused imports

# JS/TS
npx ts-prune                      # unused exports
npx unimported                    # unused files/imports
npx depcheck                      # unused dependencies in package.json

# CSS
npx purgecss --css src/**/*.css --content src/**/*.{html,tsx,jsx}
```

**Test: no dead exports in public API**
```bash
# Run ts-prune and assert zero results
output=$(npx ts-prune 2>/dev/null)
if [ -n "$output" ]; then
  echo "FAIL: unused exports found:"
  echo "$output"
  exit 1
fi
```

**Test: no unused dependencies**
```bash
npx depcheck --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
unused = data.get('dependencies', [])
if unused:
    print('Unused dependencies:', unused)
    sys.exit(1)
"
```

## Common gaps
- Dead code audit skipped because "we might use it later" — this is how dead code accumulates
- Commented-out code left as documentation of intent — use a code comment or ADR doc instead
- Feature flag set to `True` permanently after rollout but branch never cleaned up — the `False` path is dead
- Orphaned API route still has its handler and tests — tests pass but the route is never called by any client
- Unused DB migration columns never flagged because ORM hides direct column access
- CSS audit skipped — stylesheet grows unboundedly with classes from removed components
