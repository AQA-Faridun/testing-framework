"""
Demo tests that show every Allure status and the main report features. They need no network and no
browser. Some of them fail on purpose, so the `demo` marker is excluded from regular runs
(`-m "not demo"` in pyproject.toml). Run them with: make mark-open M=demo
"""

import json
import time
import uuid
from collections import Counter
from decimal import Decimal

import allure
import httpx
import pytest

from utils.attachments import attach_http_exchange, attach_text

pytestmark = [
    pytest.mark.demo,
    allure.epic("Demo"),
    allure.parent_suite("Demo"),
]

_attempts: Counter[str] = Counter()


@allure.feature("Passed")
@allure.suite("Passed")
@allure.sub_suite("Passed")
class TestPassed:
    @allure.story("Steps and attachments")
    @allure.title("Order total is the sum of its items")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_order_total_is_sum_of_items(self) -> None:
        """Nested steps, a JSON attachment and a text attachment."""
        items = [Decimal("199.90"), Decimal("50.10"), Decimal("750.00")]

        with allure.step("Build the order"):
            order = {"id": 1, "items": [str(item) for item in items], "total": str(sum(items))}
            allure.attach(
                json.dumps(order, indent=2), name="Order", attachment_type=allure.attachment_type.JSON
            )
        with allure.step("Calculate the total"):
            total = sum(items)
            attach_text("Calculation", " + ".join(str(item) for item in items) + f" = {total}")

        assert total == Decimal("1000.00")

    @allure.story("Parametrized test")
    @allure.title("Discount {percent}% turns 1000 into {expected}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        ("percent", "expected"),
        [(0, Decimal("1000")), (10, Decimal("900")), (50, Decimal("500"))],
    )
    def test_discount_is_applied(self, percent: int, expected: Decimal) -> None:
        """Every parameter set is a separate test in the report, with its own title."""
        price = Decimal("1000")

        discounted = price * (100 - percent) / 100

        assert discounted == expected

    @allure.story("Allure 3 HTTP viewer")
    @allure.title("Created order is returned with status 201")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_http_exchange_is_attached(self) -> None:
        """
        The request and the response are built locally (no network) and attached the same way
        BaseClient does it: open the attachment to see the request/response viewer and the curl
        command. The Authorization header is masked.
        """
        request = httpx.Request(
            "POST",
            "https://shop.example.test/api/v1/orders",
            json={"items": [{"sku": "A-1", "quantity": 2}]},
            headers={"Authorization": "Bearer demo-token"},
        )
        response = httpx.Response(201, json={"id": 42, "status": "created"}, request=request)

        with allure.step("POST /api/v1/orders"):
            attach_http_exchange(response, started_at_ms=int(time.time() * 1000))

        assert response.status_code == 201

    @allure.story("Parameter excluded from history")
    @allure.title("Every new order gets a unique number")
    @allure.severity(allure.severity_level.NORMAL)
    def test_order_number_is_unique(self) -> None:
        """
        The order number changes every run. It is shown as a parameter but excluded from the
        history id, so the test keeps one history across runs.
        """
        first_number, second_number = uuid.uuid4().hex, uuid.uuid4().hex
        allure.dynamic.parameter("order number", first_number, excluded=True)

        assert first_number != second_number


@allure.feature("Flaky")
@allure.suite("Flaky")
@allure.sub_suite("Flaky")
class TestFlaky:
    @allure.story("Passed on retry")
    @allure.title("Payment status check passes on the second attempt")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.flaky(reruns=1)
    def test_passes_on_retry(self, request: pytest.FixtureRequest) -> None:
        """Fails on the first attempt and passes on the rerun: see the Retries tab."""
        _attempts[request.node.nodeid] += 1

        assert _attempts[request.node.nodeid] > 1, "Simulated flaky failure on the first attempt"


@allure.feature("Failed")
@allure.suite("Failed")
@allure.sub_suite("Failed")
class TestFailed:
    @allure.story("Product defect")
    @allure.title("Product price matches the catalog price")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_price_matches_catalog(self) -> None:
        """An assertion fails: the status is failed and the report shows expected vs actual."""
        catalog_price = Decimal("1999.00")

        cart_price = Decimal("1899.00")

        assert cart_price == catalog_price

    @allure.story("Known issue")
    @allure.title("Deleted user can't log in")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.issue("DEMO-101", "Deleted users keep their sessions")
    def test_known_issue(self) -> None:
        """
        Fails with a message that starts with a ticket id, so it lands in the "Known issues"
        category of allurerc.mjs.
        """
        login_allowed = True

        assert not login_allowed, "DEMO-101: a deleted user can still log in"

    @allure.story("Fixed bug")
    @allure.title("Search returns results for a Cyrillic query")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.xfail(reason="DEMO-102: Cyrillic search was broken", strict=True)
    def test_strict_xpass(self) -> None:
        """
        Marked as a strict xfail but passes: XPASS(strict) is failed, as a reminder to remove the
        mark once the bug is fixed.
        """
        results = ["Ноутбук"]

        assert results


@allure.feature("Broken")
@allure.suite("Broken")
@allure.sub_suite("Broken")
class TestBroken:
    @allure.story("Test defect")
    @allure.title("Order has a delivery date")
    @allure.severity(allure.severity_level.NORMAL)
    def test_broken_by_test_code(self) -> None:
        """The test code raises KeyError before any check: the status is broken, not failed."""
        order: dict[str, str] = {"id": "1", "status": "created"}

        assert order["delivery_date"]

    @allure.story("Environment defect")
    @allure.title("Payment is accepted by the payments service")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.usefixtures("unavailable_service")
    def test_broken_in_setup(self) -> None:
        """
        The fixture fails with a network error, so the test is broken in setup and lands in the
        "Network / stand unavailable" category.
        """
        assert True


@allure.feature("Skipped")
@allure.suite("Skipped")
@allure.sub_suite("Skipped")
class TestSkipped:
    @allure.story("Skip")
    @allure.title("Wishlist keeps added products")
    @allure.severity(allure.severity_level.TRIVIAL)
    @pytest.mark.skip(reason="Wishlist is not deployed on this stand")
    def test_skipped(self) -> None:
        """Skipped by a mark: the body never runs."""

    @allure.story("Skip at runtime")
    @allure.title("Gift cards can be used at checkout")
    @allure.severity(allure.severity_level.MINOR)
    def test_skipped_at_runtime(self) -> None:
        """Skipped from inside the test, when a condition is known only at runtime."""
        gift_cards_enabled = False

        if not gift_cards_enabled:
            pytest.skip("Gift cards feature flag is off")

    @allure.story("Expected failure")
    @allure.title("Export to PDF keeps the table layout")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.xfail(reason="DEMO-103: PDF export breaks tables", strict=False)
    def test_expected_failure(self) -> None:
        """A known bug marked with xfail: the test fails as expected and is shown as skipped."""
        columns_in_pdf = 2

        assert columns_in_pdf == 3
