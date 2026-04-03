# Policy Tests Suite

## When to apply
Always-on. Every project has implicit rules that must never be broken — storage key names, security invariants, content safety rules, code quality standards. Policy tests codify these as source-scan assertions: they grep source files for presence or absence of patterns, not behavior. They are zero-dependency, never flaky, and catch entire categories of bugs.

## What policy tests are

Unlike behavior tests (does function X return Y?), policy tests ask: **"what must never be true in this codebase?"**

- They scan source files with grep/regex
- They assert counts: `count === 0` (pattern must not exist) or `count > 0` (pattern must exist)
- They require no test runner setup — pure Node/Python file reads
- They never fail due to timing, randomness, or network
- They catch regressions the moment a rule is violated, not at runtime

**This pattern is more portable than any behavior test.** The same grep-based test works across React, Python, Go, or any language.

## Categories of policy tests to generate

Ask the user (or infer from the codebase): "What are this project's rules that should never be broken?" Then write a test for each.

### 1. Security policy
```js
// No hardcoded API keys or secrets in source
it('no hardcoded API keys in source', () => {
  const files = glob('src/**/*.{js,ts,jsx,tsx}');
  const violations = files.filter(f =>
    /API_KEY\s*=\s*['"][A-Za-z0-9]{20,}['"]|sk-[A-Za-z0-9]{40,}/.test(readFileSync(f, 'utf8'))
  );
  expect(violations).toEqual([]);
});

// No credentials in config files committed to repo
it('no .env files in src directory', () => {
  const envFiles = glob('src/**/.env*');
  expect(envFiles).toHaveLength(0);
});
```

```python
def test_no_hardcoded_secrets(source_files):
    patterns = [r'password\s*=\s*["\'][^"\']{6,}["\']', r'api_key\s*=\s*["\'][^"\']{10,}["\']']
    for f in source_files:
        content = open(f).read()
        for pat in patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            assert not matches, f"Potential secret in {f}: {matches}"
```

### 2. Children/safety policy (for apps targeting minors)
```js
it('no browser dialogs in child-facing code', () => {
  const files = glob('src/**/*.{js,jsx,ts,tsx}');
  const violations = [];
  files.forEach(f => {
    const content = readFileSync(f, 'utf8');
    if (/\b(confirm|alert|prompt)\s*\(/.test(content)) violations.push(f);
  });
  expect(violations).toEqual([]);
});

it('no adult content keywords in visible strings', () => {
  const blocklist = ['casino', 'gambling', 'violence', /* project-specific list */];
  const files = glob('src/**/*.{js,jsx,ts,tsx}');
  files.forEach(f => {
    const content = readFileSync(f, 'utf8').toLowerCase();
    blocklist.forEach(word => {
      expect(content).not.toContain(word);
    });
  });
});
```

### 3. Data integrity policy
```js
// Storage key name must never silently change (would break all existing user data)
it('localStorage key name is unchanged', () => {
  const src = readFileSync('src/store.js', 'utf8');
  expect(src).toContain("'myapp-user-data'"); // locked value
});

// All topic IDs are unique
it('no duplicate topic IDs in content data', () => {
  const { TOPICS } = require('../src/constants');
  const ids = TOPICS.map(t => t.id);
  expect(new Set(ids).size).toBe(ids.length);
});
```

### 4. Localization policy
```js
// Hebrew exclamation marks must appear at end of string (RTL rule)
it('Hebrew strings with ! have ! at end', () => {
  const files = glob('src/**/*.{js,jsx,ts,tsx}');
  files.forEach(f => {
    const content = readFileSync(f, 'utf8');
    const hebrewStrings = content.match(/['"`][^'"`]*[\u0590-\u05FF][^'"`]*['"`]/g) || [];
    hebrewStrings.forEach(s => {
      if (s.includes('!')) {
        expect(s.trimEnd().slice(-2)).toMatch(/!['"`]/);
      }
    });
  });
});

// Every locale key present in en.json must exist in all other locale files
it('no missing locale keys', () => {
  const en = JSON.parse(readFileSync('src/locales/en.json'));
  const localeFiles = glob('src/locales/*.json').filter(f => !f.endsWith('en.json'));
  localeFiles.forEach(f => {
    const locale = JSON.parse(readFileSync(f));
    Object.keys(en).forEach(key => {
      expect(locale).toHaveProperty(key);
    });
  });
});
```

### 5. Code quality policy
```js
// No console.log left in production source (only allowed in test files)
it('no console.log in production source', () => {
  const files = glob('src/**/*.{js,ts,jsx,tsx}').filter(f => !f.includes('test'));
  const violations = files.filter(f => /console\.log\(/.test(readFileSync(f, 'utf8')));
  expect(violations).toEqual([]);
});

// No TODO/FIXME comments in critical paths
it('no TODO in payment or auth code', () => {
  const criticalFiles = glob('src/{auth,payment,billing}/**/*.{js,ts}');
  criticalFiles.forEach(f => {
    expect(readFileSync(f, 'utf8')).not.toMatch(/\/\/\s*(TODO|FIXME|HACK)/i);
  });
});
```

### 6. Architecture/dependency policy
```js
// UI components must not import from server-only modules
it('UI components do not import server modules', () => {
  const uiFiles = glob('src/components/**/*.{js,jsx,ts,tsx}');
  uiFiles.forEach(f => {
    const content = readFileSync(f, 'utf8');
    expect(content).not.toMatch(/from ['"]\.\.\/server\//);
    expect(content).not.toMatch(/require\(['"]\.\.\/server\//);
  });
});
```

## How to generate policy tests for a new project

1. Read the project's README, constants file, and any existing `QA_KNOWN_ISSUES` or `CONTRIBUTING` docs
2. Ask: what are the non-obvious rules? Storage keys that must never change? Strings that must match a format? Files that must never import from certain paths?
3. For each rule: write one grep test. Name it after the rule, not the implementation.
4. Group them in a single `policy.test.js` (or `test_policy.py`) — don't scatter them

## Common gaps

- Storage key policy test written but uses a variable reference instead of a string literal — if the variable is renamed, the test still passes but the key has changed
- Security grep too narrow: checks `API_KEY =` but misses `apiKey:`, `api_key:`, `token =`
- Locale policy checks key presence but not that the value is non-empty / not a copy of the English fallback
- `console.log` check excludes test files but includes `src/utils/logger.js` which intentionally uses it — add exceptions explicitly
- Architecture policy checks `import` statements but misses dynamic `require()` calls
