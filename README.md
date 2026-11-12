# Test Automation Framework

Black-box test automation framework skeleton for an HTTP API and a UI on top of it, with
**Allure Report 3** reporting built in. There is no application code here — only the layers a
pytest suite needs to drive a backend and a UI against a target environment.

**Stack:** Python 3.12 · uv · pytest · httpx · Playwright · Appium · mimesis · pydantic-settings ·
allure-pytest · Allure 3 (Node.js) · ruff · mypy.

## What's in this repo

- **`clients/`** — thin HTTP clients, one per backend service/domain, each built on a shared base
  client. Every request is reported to Allure as a step with the request/response attached.
- **`pages/`** — page objects for Web tests (a base page plus reusable components).
- **`screens/`** — screen objects for Mobile tests on Appium (a base screen plus reusable
  components).
- **`tests/API/`, `tests/Web/`, `tests/Mobile/`** — the pytest suite, one directory per
  service/area.
- **`data/`** — Factory/Builder layer for generating test entities, shared dataclass models, and
  custom data providers.
- **`config.py`** — run settings from env vars / `.env`.
- **`utils/`** — Allure attachment helpers.
- **`allurerc.mjs`** — Allure Report 3 config.
- **`scripts/make_run_summary.py`** — short Markdown summary of the last run.
- **`docs/`** — the contract(s) the clients and tests are derived from (an API collection/spec,
  etc.) — the single source of truth for request/response shapes.

## Requirements

| Tool | Version | Install |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | ≥ 0.9 | `brew install uv` |
| Python | 3.12 | installed by uv automatically |
| Node.js | ≥ 22.18 | `brew install node` (only for the Allure CLI) |

## Setup

```bash
make install            # uv sync + playwright install chromium + npm ci
cp .env.example .env    # optional: every variable has a default
```

| Variable | Default | Purpose |
|---|---|---|
| `STAND_NAME` | `local` | stand name in the report |
| `API_BASE_URL` | `http://localhost` | base URL for API clients |
| `WEB_BASE_URL` | `http://localhost` | base URL for the browser |
| `API_TIMEOUT_S` | `60` | httpx timeout, seconds |
| `UI_TIMEOUT_MS` | `15000` | Playwright and `expect` timeout, ms |
| `WEB_ARTIFACTS` | `on-failure` | `always`: attach browser artifacts to every Web test |

## Running tests

⚠️ **This suite may hit a shared or live environment and create real state.** Never run it against
such an environment without knowing what you're doing.

`make` targets wrap `npx allure run -- uv run pytest ...`: tests run, the report is built, and the
quality gate is checked. Extra pytest arguments go through `ARGS`. Run `make` to see all commands.

| Command | What it does |
|---|---|
| `make test` | all tests + report + quality gate |
| `make api` / `web` / `mobile` / `ui` | `tests/API`, `tests/Web`, `tests/Mobile`, Web + Mobile |
| `make smoke` | tests marked `smoke` |
| `make mark M="api_positive"` | any marker expression, plain pytest without a report |
| `make <target> OPEN=1` / `make test-open` / `make mark-open M="..."` | run, then open the report (opens even when tests fail) |
| `make test ARGS="-n 4"` | in parallel (pytest-xdist) |
| `make web ARGS="--headed"` | with a visible browser |
| `make report` / `make open` | rebuild the report from `allure-results/` / serve it |
| `make run-summary` | summary of the last run → `docs/run-summary.md` |
| `make lint` | ruff + mypy |
| `make clean` / `make clean FULL=1` | empty / remove `allure-results/`, `allure-report/`, `test-results/` (`.allure/` history is kept) |

Plain pytest works too; results still go to `allure-results/`:

```bash
uv run pytest tests/API/<service>/test_file.py::TestClassName
uv run pytest -m api_negative
```

Config lives in `pyproject.toml`. Custom markers (`--strict-markers` is on):

- `smoke`, `regression` — reserved for future use.
- `api_positive` / `api_negative`, `web_positive` / `web_negative`, `mobile_positive` /
  `mobile_negative` — universal pairs per area.
- Per-service `api_<service>_positive` / `api_<service>_negative` pairs — add a new pair whenever
  a new service/feature area is added.

## Allure Report 3

`allure-report/index.html` links to the plugin reports:

| Plugin | Where | What it gives |
|---|---|---|
| `awesome` | `allure-report/awesome/` | main UI: epic → feature → story tree, steps, attachments, history, retries, categories, charts, environment |
| `dashboard` | `allure-report/dashboard/` | standalone dashboard with trend charts |
| `csv` | `allure-report/csv/allure-results.csv` | flat export |
| `testplan` | `allure-report/testplan/testplan.json` | failed tests, for a rerun |
| `log` | console | failed tests right after the run |

Attached automatically:

- **API** — each request: an Allure 3 HTTP exchange (request/response viewer) and a curl command.
  `Authorization`, `Cookie` and `Set-Cookie` are masked.
- **Web** — on failure (or always with `WEB_ARTIFACTS=always`): screenshot and HTML of each page,
  Playwright trace (opens in the embedded Trace Viewer), HAR, browser console.
- **Environment** — stand, base URLs, Python, OS, pytest, httpx and browser versions.

**History.** Every report generation appends a line to `.allure/history.jsonl`. That powers the
History tab, trend charts, New/Fixed/Regressed marks and flaky detection. Delete `.allure/` for a
clean start.

**Rerun only the last failures:**

```bash
ALLURE_TESTPLAN_PATH=allure-report/testplan/testplan.json uv run pytest
```

**Known issues, categories, quality gate** are configured in `allurerc.mjs` (`resolutions`,
`categories`, `qualityGate`). A broken quality gate makes `make test` exit with an error.

## Test suite layout

```
tests/
  conftest.py                  # shared fixtures, environment.properties for Allure
  API/<service>/
    test_business_flow.py      # positive tests — successful flows
    test_validation.py         # negative tests — invalid input, error responses (4xx only)
    conftest.py                # fixtures used only by this service's tests
  Web/conftest.py              # Playwright context with Allure artifacts
  Web/<area>/  Mobile/<area>/  # same shape as API
```

Fixtures shared by two or more services live in the nearest common `conftest.py`; anything
narrower stays in its own directory's `conftest.py`.

## Data layer

`data/factories/` and `data/builders/` generate test entities via mimesis and custom providers,
returning a shared `<Entity>Context` dataclass with an `error` field (never raises).
`data/models/` holds the `<Entity>Context` dataclasses themselves.

## Known limitations

- **pytest is pinned `<9`.** With pytest 9, allure-pytest 2.16 adds a junk `<lambda>` teardown
  step with status unknown to every fixture.
- `make` removes `allure-results/` before every `allure run`: when `environment.properties` from
  the previous run is still there, `allure run` ignores the fresh one and the report shows no
  environment.
