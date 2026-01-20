# SOP: Debugging Test Failures

**Category**: Debugging
**Created**: 2025-12-09
**Last Updated**: 2025-12-09

---

## Problem Description

Tests are failing unexpectedly. This could be due to:
- Environment issues
- Dependency changes
- Code regressions
- Flaky tests
- Configuration drift

## Symptoms

- `npm test` or `pytest` exits with non-zero code
- CI pipeline fails on test stage
- Tests pass locally but fail in CI (or vice versa)
- Intermittent failures on the same test

## Root Cause Analysis

### Step 1: Isolate the Failure

```bash
# Run single failing test
npm test -- --testNamePattern="failing test name"
# or
pytest path/to/test.py::test_function -v
```

### Step 2: Check Recent Changes

```bash
# What changed since tests last passed?
git log --oneline -10
git diff HEAD~5 -- "**/*.test.*"
```

### Step 3: Verify Environment

```bash
# Node.js
node -v
npm ls

# Python
python --version
pip list
```

### Step 4: Check for Flakiness

```bash
# Run test multiple times
for i in {1..5}; do npm test -- --testNamePattern="suspect test"; done
```

## Solution Steps

### For Dependency Issues

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# or for Python
pip install -r requirements.txt --force-reinstall
```

### For Environment Issues

```bash
# Ensure consistent Node version
nvm use
# or
asdf install
```

### For Flaky Tests

1. Add explicit waits for async operations
2. Mock external dependencies
3. Use test isolation (beforeEach cleanup)
4. Add retry logic for known flaky integrations

### For CI-Specific Failures

1. Check CI environment variables
2. Compare CI Node/Python version with local
3. Check for timing-sensitive tests
4. Verify test database state

## Prevention Checklist

- [ ] Pin dependency versions in package.json/requirements.txt
- [ ] Use consistent Node/Python version (via .nvmrc or .python-version)
- [ ] Mock external services in tests
- [ ] Add test timeouts to catch hanging tests
- [ ] Run tests in CI with same configuration as local
- [ ] Use snapshot testing for UI regressions

## Related Documentation

- Task docs for feature being tested
- CI/CD configuration files
- Testing framework documentation

---

**When to use this SOP**: Any time tests fail unexpectedly

**When to update this SOP**: After discovering new failure patterns
