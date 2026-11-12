"""Fixtures for the demo tests only."""

import httpx
import pytest


@pytest.fixture
def unavailable_service() -> None:
    """
    Setup that fails with a network error, so the test using it becomes broken before it starts.
    No real request is sent: the error is raised directly.
    """
    raise httpx.ConnectError("Connection refused: payments service at payments.example.test:443 is down")
