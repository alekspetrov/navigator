# Navigator Plugin - Quality Gate Targets
# These targets support the CI/CD quality gates

.PHONY: build test lint clean

# Build target - for a plugin, validate JSON and check Python syntax
build:
	@echo "Validating plugin configuration..."
	@python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))" && echo "plugin.json: OK"
	@python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))" && echo "marketplace.json: OK"
	@echo "Checking Python syntax..."
	@python3 -m py_compile skills/nav-loop/functions/status_generator.py && echo "status_generator.py: OK"
	@echo "Build validation complete."

# Directories with genuine unittest suites. Each test_*.py imports its sibling
# module by bare name, so discovery must run per-directory (from inside each dir).
# Deliberately EXCLUDES two files that match test_*.py but are NOT unit tests:
#   skills/frontend-component/functions/test_generator.py  (an argparse CLI generator)
#   skills/product-design/functions/test_mcp_connection.py (a live Figma MCP probe)
TEST_DIRS := \
	skills/nav-upgrade/functions \
	skills/nav-sync-claude/functions \
	skills/nav-simplify/scripts \
	skills/nav-workflow/functions \
	skills/nav-init/functions \
	skills/nav-loop/functions \
	skills/nav-release/functions

# Test target - run all Python unit tests via per-directory discovery
test:
	@echo "Running unit tests..."
	@fail=0; \
	for d in $(TEST_DIRS); do \
		if ls $$d/test_*.py >/dev/null 2>&1; then \
			echo "--- $$d ---"; \
			( cd $$d && python3 -m unittest discover -p "test_*.py" ) || fail=1; \
		fi; \
	done; \
	if [ $$fail -ne 0 ]; then echo "TESTS FAILED"; exit 1; fi; \
	echo "All unit tests passed."

# Lint target - check code style
lint:
	@echo "Running lint checks..."
	@python3 -m py_compile skills/nav-loop/functions/status_generator.py && echo "Python syntax: OK"
	@echo "Lint complete."

# Clean target - remove generated files
clean:
	@echo "Cleaning..."
	@rm -rf coverage/
	@rm -rf __pycache__/
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete."
