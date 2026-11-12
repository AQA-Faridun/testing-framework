"""
Base HTTP client.

Wraps httpx.Client with common headers, lifecycle management and Allure reporting.
All microservice clients inherit from this class.
"""

import logging
import time
from typing import Any, ClassVar, Self

import allure
import httpx

from config import get_settings
from utils.attachments import attach_http_exchange

logger = logging.getLogger(__name__)


class BaseClient:
    """
    Session-scoped HTTP client with project-wide default headers. Every request becomes an Allure
    step with the request/response attached (Allure 3 HTTP viewer + curl).

    Usage:
        client = SomeClient()
        response = client._get("/some/path")
        client.close()

    Or as a context manager:
        with SomeClient() as client:
            response = client._get("/some/path")

    A subclass sets its own base path in __init__ (e.g. self.url = "/api/v1/users"). Relative paths
    are resolved against API_BASE_URL from config.Settings.
    """

    INVALID_TOKEN: str = "eyJhbGciOiJIUzI1NiJ9.invalid.signature"

    DEFAULT_HEADERS: ClassVar[dict[str, str]] = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) Gecko/20100101 Firefox/147.0",
    }

    @staticmethod
    def _log_response(response: httpx.Response) -> None:
        response.read()
        status = response.status_code
        req = f"{response.request.method} {response.request.url}"

        if status < 400:
            logger.info("%s → %s", req, status)
        elif status == 502:
            logger.error("%s → %s", req, status)
        elif status >= 500:
            logger.error("%s → %s | %s", req, status, response.text)
        else:
            try:
                reason = response.json().get("reason", response.text)
            except Exception:
                reason = response.text
            logger.warning("%s → %s | %s", req, status, reason)

    def __init__(
        self,
        extra_headers: dict[str, str] | None = None,
        timeout: float | None = None,
        cookies: httpx.Cookies | None = None,
    ) -> None:
        """
        Args:
            extra_headers (dict[str, str] | None): headers added to DEFAULT_HEADERS for every request.
            timeout (float | None): request timeout in seconds; API_TIMEOUT_S from settings when None.
            cookies (httpx.Cookies | None): cookies to start the session with.
        """
        settings = get_settings()
        self._http: httpx.Client = httpx.Client(
            base_url=settings.api_base_url,
            headers={**self.DEFAULT_HEADERS, **(extra_headers or {})},
            timeout=settings.api_timeout_s if timeout is None else timeout,
            follow_redirects=True,
            cookies=cookies,
            event_hooks={"response": [self._log_response]},
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------
    # Low-level request helpers (used by subclasses)
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """
        Send a request inside an Allure step and attach the HTTP exchange to that step.

        The typed helpers below all go through it. Call it directly only for what they can't send,
        e.g. a malformed raw body (content=b"...") in a negative test — it still gets reported.

        Args:
            method (str): HTTP method, e.g. "GET".
            path (str): path relative to the base URL, or a full URL.
            **kwargs (Any): passed to httpx.Client.request as is.
        """
        with allure.step(f"{method} {path}"):
            started_at_ms = int(time.time() * 1000)
            response = self._http.request(method, path, **kwargs)
            attach_http_exchange(response, started_at_ms)
            return response

    def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> httpx.Response:
        return self._request("GET", path, params=params, headers=headers, cookies=cookies)

    def _post(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        files: Any = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return self._request(
            "POST",
            path,
            params=params,
            json=json,
            headers=headers,
            cookies=cookies,
            files=files,
            data=data,
        )

    def _put(
        self,
        path: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        files: Any = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return self._request(
            "PUT",
            path,
            json=json,
            headers=headers,
            cookies=cookies,
            files=files,
            data=data,
        )

    def _patch(
        self,
        path: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        files: Any = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        return self._request(
            "PATCH",
            path,
            json=json,
            headers=headers,
            cookies=cookies,
            files=files,
            data=data,
        )

    def _delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> httpx.Response:
        return self._request("DELETE", path, headers=headers, cookies=cookies)

    # ------------------------------------------------------------------
    # Header builders
    # ------------------------------------------------------------------

    @staticmethod
    def _bearer(token: str) -> dict[str, str]:
        """Returns an Authorization header dict for the given token."""
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # Error message helpers
    # ------------------------------------------------------------------
    @staticmethod
    def getting_error_message(response: httpx.Response) -> str:
        """Returns an error message from the response."""
        body = response.json()
        for key in ("reason", "error", "message"):
            if key in body:
                return str(body[key])
        return response.text
