"""
Playwright fixtures for Web tests. They replace pytest-playwright's `context` and `page` to attach
screenshots, page HTML, the Playwright trace, HAR and the browser console to Allure.
"""

from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

import allure
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

from config import Settings
from utils.attachments import attach_file, attach_html, attach_playwright_trace, attach_text
from utils.stash_keys import ALLURE_ENVIRONMENT_KEY

PHASE_REPORTS_KEY = pytest.StashKey[dict[str, pytest.TestReport]]()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Keep setup/call/teardown reports on the item, so the context fixture knows the test failed."""
    report = yield
    item.stash.setdefault(PHASE_REPORTS_KEY, {})[report.when] = report
    return report


@pytest.fixture(scope="session")
def web_session_setup(browser: Browser, pytestconfig: pytest.Config, settings: Settings) -> None:
    expect.set_options(timeout=settings.ui_timeout_ms)
    pytestconfig.stash[ALLURE_ENVIRONMENT_KEY]["Browser"] = f"{browser.browser_type.name} {browser.version}"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], settings: Settings) -> dict[str, Any]:
    return {**browser_context_args, "base_url": settings.web_base_url}


def _test_failed(request: pytest.FixtureRequest) -> bool:
    reports = request.node.stash.get(PHASE_REPORTS_KEY, {})
    return any(report.failed for report in reports.values())


@pytest.fixture
def context(
    browser: Browser,
    web_session_setup: None,
    browser_context_args: dict[str, Any],
    settings: Settings,
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> Iterator[BrowserContext]:
    """
    Browser context that attaches artifacts to Allure on teardown: on failure, or for every test
    when WEB_ARTIFACTS=always.
    """
    har_path = tmp_path / "network.har"
    context = browser.new_context(**browser_context_args, record_har_path=har_path, record_har_content="omit")
    context.set_default_timeout(settings.ui_timeout_ms)
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    console_lines: list[str] = []
    context.on("console", lambda message: console_lines.append(f"[{message.type}] {message.text}"))

    yield context

    if not (_test_failed(request) or settings.web_artifacts == "always"):
        context.tracing.stop()
        context.close()
        return

    with allure.step("Browser artifacts"):
        for index, page in enumerate(context.pages, start=1):
            allure.attach(
                page.screenshot(full_page=True),
                name=f"Screenshot #{index}",
                attachment_type=allure.attachment_type.PNG,
            )
            attach_html(f"Page HTML #{index}", page.content())
        trace_path = tmp_path / "trace.zip"
        context.tracing.stop(path=trace_path)
        # The HAR file is written only when the context is closed.
        context.close()

        attach_playwright_trace(trace_path)
        attach_file(har_path, "Network log (HAR)", "application/json", "har")
        if console_lines:
            attach_text("Browser console", "\n".join(console_lines))


@pytest.fixture
def page(context: BrowserContext) -> Page:
    """The context fixture closes its pages itself, after taking screenshots."""
    return context.new_page()
