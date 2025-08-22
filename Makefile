.PHONY: setup-hooks test-up test-down test-logs test-up-force-build test-clean \
        _test-up-with-id _test-down-with-id _test-logs-with-id build-if-needed \
        test-run-integration

# Stable project/session handling
RUN_ID_FILE := .run_id
LOG_DIR := logs
BUILD_HASH_FILE := .test-build.hash

# Only files that should trigger an image rebuild (no mounted app/test code here)
BUILD_DEPS := requirements.txt requirements-dev.txt pyproject.toml \
              docker/app.test.Dockerfile docker/docker-compose.yml \
              docker/compose.test.yml

# Avoid repeating long compose invocations
COMPOSE := docker compose -f docker/docker-compose.yml -f docker/compose.test.yml

setup-hooks:
	@echo "Configuring Git hooks path..."
	@git config core.hooksPath scripts/git-hooks
	@echo "Done."

test-up:
	@if [ -f $(RUN_ID_FILE) ]; then \
		EXISTING_RUN_ID=$$(cat $(RUN_ID_FILE)); \
		if $(COMPOSE) -p "$$EXISTING_RUN_ID" ps -q 2>/dev/null | grep -q .; then \
			echo "Test env RUN_ID=$$EXISTING_RUN_ID already running."; \
			echo "Use 'make test-down' to stop it, or 'make test-logs' to view logs."; \
			exit 0; \
		else \
			echo "Stale RUN_ID file found, cleaning up..."; \
			rm -f $(RUN_ID_FILE); \
		fi; \
	fi; \
	RUN_ID=$$(date +%s); \
	echo $$RUN_ID > $(RUN_ID_FILE); \
	$(MAKE) _test-up-with-id RUN_ID=$$RUN_ID

_test-up-with-id:
	@echo "Starting test environment with RUN_ID=$(RUN_ID)..."
	@$(MAKE) build-if-needed RUN_ID=$(RUN_ID)
	@$(COMPOSE) -p "$(RUN_ID)" up -d --wait --wait-timeout 120
	@echo "Test environment started."

build-if-needed:
	@mkdir -p $(LOG_DIR)
	@NEW_HASH=$$(sha256sum $(BUILD_DEPS) | sha256sum | awk '{print $$1}'); \
	OLD_HASH=$$(cat $(BUILD_HASH_FILE) 2>/dev/null || echo ''); \
	if [ "$$NEW_HASH" != "$$OLD_HASH" ]; then \
		echo "Build deps changed; rebuilding images..."; \
		DOCKER_BUILDKIT=1 $(COMPOSE) -p "$(RUN_ID)" build 2>&1 \
		  | tee $(LOG_DIR)/test-build-$(RUN_ID).log; \
		echo $$NEW_HASH > $(BUILD_HASH_FILE); \
	else \
		echo "Build deps unchanged; skipping 'docker compose build'."; \
	fi

test-up-force-build:
	@echo "Force rebuilding test environment..."
	@rm -f $(BUILD_HASH_FILE)
	@if [ -f $(RUN_ID_FILE) ]; then \
		EXISTING_RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(MAKE) _test-down-with-id RUN_ID=$$EXISTING_RUN_ID; \
		rm -f $(RUN_ID_FILE); \
	fi; \
	RUN_ID=$$(date +%s); \
	echo $$RUN_ID > $(RUN_ID_FILE); \
	$(MAKE) _test-up-with-id RUN_ID=$$RUN_ID

test-down:
	@if [ -f $(RUN_ID_FILE) ]; then \
		RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(MAKE) _test-down-with-id RUN_ID=$$RUN_ID; \
		rm -f $(RUN_ID_FILE); \
	else \
		echo "No active test environment found."; \
	fi

_test-down-with-id:
	@echo "Stopping test environment with RUN_ID=$(RUN_ID) ..."
	@$(COMPOSE) -p "$(RUN_ID)" down -v

test-logs:
	@if [ -f $(RUN_ID_FILE) ]; then \
		RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(MAKE) _test-logs-with-id RUN_ID=$$RUN_ID; \
	else \
		echo "No active test environment found."; \
	fi

_test-logs-with-id:
	@echo "Fetching logs for test environment with RUN_ID=$(RUN_ID) ..."
	@$(COMPOSE) -p "$(RUN_ID)" logs -n 200 app weaviate ollama

# Run integration tests inside the app container using existing .run_id
test-run-integration:
	@if [ -f $(RUN_ID_FILE) ]; then \
		RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(COMPOSE) -p "$$RUN_ID" exec -T app /opt/venv/bin/python3 -m pytest tests/integration -q --junitxml=reports/junit_compose_integration.xml; \
	else \
		echo "No active test environment found. Run 'make test-up' first."; \
		exit 1; \
	fi

test-clean:
	@echo "Cleaning up test environment and build cache..."
	@rm -f $(BUILD_HASH_FILE) $(RUN_ID_FILE)
	@echo "Test build cache cleaned."