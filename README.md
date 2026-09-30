# API Test Suite

Black-box API test suite skeleton. There is no application code here — this repository is purely
a pytest-based test suite that drives a backend's HTTP API against a target environment.

## What's in this repo

- **`clients/`** — thin HTTP clients, one per backend service/domain, each built on a shared base
  client.
- **`pages/`** — page objects for UI tests (a base page plus reusable components), where UI
  coverage exists.
- **`tests/API/`** — the pytest suite itself, organized one directory per service.
- **`data/`** — Factory/Builder layer for generating test entities, shared dataclass models, and
  custom data providers.
- **`docs/`** — the contract(s) the clients and tests are derived from (an API collection/spec,
  etc.) — the single source of truth for request/response shapes.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Running tests

⚠️ **This suite may hit a shared or live environment and create real state.** Never run it against
such an environment without knowing what you're doing.

```bash
pytest                                                    # all tests, verbose
pytest tests/API/<service>/test_file.py                   # one file
pytest tests/API/<service>/test_file.py::TestClassName    # one class
pytest tests/API/<service>/test_file.py -k "some_name"    # by name substring
pytest -m "some_marker"                                   # by marker
pytest -m "marker_a or marker_b"                          # combine markers
pytest -m api_positive                                    # every positive (business-flow) test, all services
pytest -m api_negative                                    # every negative (validation) test, all services
```

Config lives in `pytest.ini` (`testpaths = tests`). Custom markers:

- `smoke`, `regression` — reserved for future use.
- `api_positive` / `api_negative` — universal pair applied to every test across all services
  (business-flow tests get `api_positive`, validation tests get `api_negative`).
- Per-service `api_<service>_positive` / `api_<service>_negative` pairs — add a new pair whenever
  a new service/feature area is added.

## Test suite layout

Each service under `tests/API/<service>/` follows the same shape:

```
tests/API/<service>/
  test_business_flow.py   # positive tests — successful flows
  test_validation.py      # negative tests — invalid input, error responses (4xx only)
  conftest.py              # fixtures used only by this service's tests
```

Fixtures shared by two or more services live in the root `tests/API/conftest.py`; anything
narrower stays in its own directory's `conftest.py`.

## Data layer

`data/factories/` and `data/builders/` generate test entities via a fake-data library and custom
providers, returning a shared `<Entity>Context` dataclass with an `error` field (never raises).
`data/models/` holds the `<Entity>Context` dataclasses themselves.
