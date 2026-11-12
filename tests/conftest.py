"""
Fixtures and hooks shared by every test area (API, Web, Mobile).

Also writes allure-results/environment.properties: the run facts shown on the Allure report overview.
"""

import getpass
import platform
from pathlib import Path

import httpx
import pytest

from config import Settings, get_settings
from utils.stash_keys import ALLURE_ENVIRONMENT_KEY


def pytest_configure(config: pytest.Config) -> None:
    settings = get_settings()
    config.stash[ALLURE_ENVIRONMENT_KEY] = {
        "Stand": settings.stand_name,
        "API base URL": settings.api_base_url,
        "Web base URL": settings.web_base_url,
        "Run by": getpass.getuser(),
        "Python": platform.python_version(),
        "OS": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "pytest": pytest.__version__,
        "httpx": httpx.__version__,
    }


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node: object, error: object) -> None:
    """xdist controller: merge the facts collected by a worker (e.g. the browser version)."""
    worker_environment = getattr(node, "workeroutput", {}).get("allure_environment", {})
    config: pytest.Config = node.config  # type: ignore[attr-defined]
    config.stash[ALLURE_ENVIRONMENT_KEY].update(worker_environment)


def pytest_sessionfinish(session: pytest.Session) -> None:
    config = session.config
    if hasattr(config, "workerinput"):
        config.workeroutput["allure_environment"] = config.stash[ALLURE_ENVIRONMENT_KEY]  # type: ignore[attr-defined]
        return
    alluredir = config.getoption("allure_report_dir", None)
    if not alluredir:
        return
    # A space ends the key in the .properties format, so spaces inside keys are escaped.
    lines = [
        f"{key.replace(' ', '\\ ')}={value}" for key, value in config.stash[ALLURE_ENVIRONMENT_KEY].items()
    ]
    (Path(alluredir) / "environment.properties").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()
