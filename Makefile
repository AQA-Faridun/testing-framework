# Thin wrappers around pytest and Allure 3.
# Extra pytest args: make web ARGS="-n 4". Open the report after the run: OPEN=1.
ARGS ?=
M ?=
OPEN ?=
FULL ?=
ALLURE := npx allure
PYTEST := uv run pytest
PYTHON := uv run python
RESULTS_DIR := ./allure-results
REPORT_DIR := ./allure-report
# test-results/ is the pytest-playwright output dir.
CLEAN_DIRS := $(RESULTS_DIR) $(REPORT_DIR) test-results
API_DIR := tests/API
WEB_DIR := tests/Web
MOBILE_DIR := tests/Mobile

# `allure run` ignores environment.properties when a file with that name was already in
# allure-results when it started (pytest's --clean-alluredir recreates it too late), so the
# results are removed before every run.
reset_results = rm -rf $(RESULTS_DIR)
# $(1) = pytest args. `;` instead of `&&`, so the report opens even when tests fail.
run_and_open = $(reset_results) && $(ALLURE) run -- $(PYTEST) $(1) $(ARGS); $(ALLURE) open $(REPORT_DIR)
run_with_report = $(reset_results) && $(ALLURE) run -- $(PYTEST) $(1) $(ARGS)
run_tests = $(if $(filter 1,$(OPEN)),$(call run_and_open,$(1)),$(call run_with_report,$(1)))

.DEFAULT_GOAL := help
.PHONY: help install test test-open mark mark-open api web mobile ui smoke report open run-summary lint clean

help:               ## Show available commands
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:            ## Python deps, Chromium, Allure 3 CLI
	uv sync
	uv run playwright install chromium
	npm ci

test:               ## All tests + report + quality gate [OPEN=1]
	$(call run_tests,)

test-open:          ## All tests, then open the report (opens even if tests fail)
	$(call run_and_open,)

mark:               ## Tests by marker: make mark M="smoke and not slow" [OPEN=1]
	@test -n "$(M)" || { echo 'Usage: make mark M="<marker expression>" [OPEN=1] [ARGS="..."]'; exit 2; }
	$(if $(filter 1,$(OPEN)),$(call run_and_open,-m "$(M)"),$(PYTEST) -m "$(M)" $(ARGS))

mark-open:          ## Tests by marker, then open the report: make mark-open M="smoke"
	@$(MAKE) --no-print-directory mark OPEN=1

api:                ## API tests [OPEN=1]
	$(call run_tests,$(API_DIR))

web:                ## Web UI tests [OPEN=1]
	$(call run_tests,$(WEB_DIR))

mobile:             ## Mobile UI tests [OPEN=1]
	$(call run_tests,$(MOBILE_DIR))

ui:                 ## Web + Mobile UI tests [OPEN=1]
	$(call run_tests,$(WEB_DIR) $(MOBILE_DIR))

smoke:              ## Smoke tests [OPEN=1]
	$(call run_tests,-m smoke)

report:             ## Rebuild the report from allure-results (adds a history entry)
	$(ALLURE) generate $(RESULTS_DIR)

open:               ## Serve the built report
	$(ALLURE) open $(REPORT_DIR)

run-summary:        ## Summary of the last run from allure-results -> docs/run-summary.md
	$(PYTHON) scripts/make_run_summary.py

lint:               ## ruff + mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

clean:              ## Empty results/report folders; FULL=1 removes the folders too (.allure/ history is kept)
ifeq ($(FULL),1)
	rm -rf $(CLEAN_DIRS)
else
	for dir in $(CLEAN_DIRS); do [ ! -d "$$dir" ] || find "$$dir" -mindepth 1 -delete; done
endif
