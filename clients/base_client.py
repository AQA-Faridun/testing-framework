"""
Base HTTP client.

Wraps httpx.Client with common headers and lifecycle management.
All microservice clients inherit from this class.
"""

import logging

import httpx

logger = logging.getLogger(__name__)


class BaseClient:
    """
    Session-scoped HTTP client with project-wide default headers.

    Usage:
        client = SomeClient()
        response = client._get("/some/path")
        client.close()

    Or as a context manager:
        with SomeClient() as client:
            response = client._get("/some/path")

    A subclass sets its own base path in __init__ (e.g. self.url = f"{self.DEFAULT_BASE_URL}/api/v1/users").
    """

    DEFAULT_BASE_URL: str = "localhost"
    INVALID_TOKEN: str = "eyJhbGciOiJIUzI1NiJ9.invalid.signature"

    DEFAULT_HEADERS: dict[str, str] = {
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

    def __init__(self, extra_headers: dict = None, timeout: float = 60.0, cookies: httpx.Cookies | None = None):
        self._http: httpx.Client = httpx.Client(
            base_url = self.DEFAULT_BASE_URL,
            headers = {**self.DEFAULT_HEADERS, **(extra_headers or {})},
            timeout = timeout,
            follow_redirects = True,
            cookies = cookies or {},
            event_hooks = {"response": [self._log_response]},
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self._http.close()

    # ------------------------------------------------------------------
    # Low-level request helpers (used by subclasses)
    # ------------------------------------------------------------------

    def _get(
        self,
        path: str,
        *,
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
    ) -> httpx.Response:
        return self._http.get(path, params=params, headers=headers, cookies=cookies)

    def _post(
        self,
        path: str,
        *,
        params: dict = None,
        json: dict = None,
        headers: dict = None,
        cookies: dict = None,
        files=None,
        data: dict = None,
    ) -> httpx.Response:
        return self._http.post(
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
        json: dict = None,
        headers: dict = None,
        cookies=None,
        files=None,
        data: dict = None,
    ) -> httpx.Response:
        return self._http.put(
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
        json: dict = None,
        headers: dict = None,
        cookies=None,
        files=None,
        data: dict = None,
    ) -> httpx.Response:
        return self._http.patch(
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
        headers: dict = None,
        cookies=None,
    ) -> httpx.Response:
        return self._http.delete(path, headers=headers, cookies=cookies)

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
        if "reason" in response.json():
            return response.json()["reason"]
        elif "error" in response.json():
            return response.json()["error"]
        elif "message" in response.json():
            return response.json()["message"]
        return response.text