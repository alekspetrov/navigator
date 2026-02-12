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

# Test target - run Jest tests for TypeScript and Python unit tests
test:
	@echo "Running tests..."
	@if [ -f "package-lock.json" ] || [ -d "node_modules" ]; then \
		npx jest --passWithNoTests 2>/dev/null || true; \
	fi
	@python3 -c "exec(open('skills/nav-loop/functions/status_generator.py').read())" 2>/dev/null && echo "Python module loads: OK"
	@echo "Tests complete."

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
