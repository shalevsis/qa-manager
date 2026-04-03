# Language-Agnostic Testing Guidance

## Step 1: Discover how tests run

1. `package.json` → `scripts.test`
2. `Makefile` → `test:` target
3. CI config: `.github/workflows/*.yml`, `.gitlab-ci.yml`
4. `tox.ini`, `build.gradle`, `Cargo.toml`, `go.mod`

## Step 2: Read existing tests first

Find: `*_test.*`, `*_spec.*`, `test_*.*`, `tests/`, `spec/`, `__tests__/`

Match style, assertion library, and structure.

## Universal principles

- One behavior per test
- Descriptive names — describe expected outcome
- Arrange-Act-Assert
- Tests must be independent

## Common run commands

```bash
go test ./...
cargo test
./gradlew test / mvn test
bundle exec rspec
dotnet test
```

## When no tests exist

1. State you're bootstrapping the test setup
2. Install the most idiomatic framework for the language
3. Create a minimal config
4. Write a few example tests
5. Tell the user how to run them
