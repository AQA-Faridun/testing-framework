"""Allure attachment helpers, including the Allure 3 content types (HTTP exchange, Playwright trace)."""

import json
import shlex
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

import allure
import httpx

HTTP_EXCHANGE_MIME = "application/vnd.allure.http+json"
PLAYWRIGHT_TRACE_MIME = "application/vnd.allure.playwright-trace"

_REDACTED_HEADERS = frozenset({"authorization", "cookie", "set-cookie"})


def attach_text(name: str, text: str) -> None:
    """
    Attach plain text.

    Args:
        name (str): attachment title in the report.
        text (str): attachment content.
    """
    allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_html(name: str, html: str) -> None:
    """
    Attach an HTML document (rendered in the report).

    Args:
        name (str): attachment title in the report.
        html (str): HTML source.
    """
    allure.attach(html, name=name, attachment_type=allure.attachment_type.HTML)


def attach_file(path: Path, name: str, mime_type: str, extension: str) -> None:
    """
    Attach a file from disk.

    Args:
        path (Path): file to attach.
        name (str): attachment title in the report.
        mime_type (str): content type that tells Allure how to render the file.
        extension (str): file extension in the report, without the dot.
    """
    allure.attach.file(str(path), name=name, attachment_type=mime_type, extension=extension)


def attach_playwright_trace(path: Path) -> None:
    """
    Attach a Playwright trace; Allure 3 opens it in the embedded Trace Viewer.

    Args:
        path (Path): trace.zip saved by context.tracing.stop().
    """
    attach_file(path, "Playwright trace", PLAYWRIGHT_TRACE_MIME, "zip")


def attach_http_exchange(response: httpx.Response, started_at_ms: int) -> None:
    """
    Attach a request/response pair in the Allure 3 HTTP exchange format, plus the request as curl.
    Credential headers are masked.

    Args:
        response (httpx.Response): received response; the request is taken from response.request.
        started_at_ms (int): request start time, epoch milliseconds.
    """
    exchange = {
        "schemaVersion": 1,
        "start": started_at_ms,
        "stop": int(time.time() * 1000),
        "request": _request_payload(response.request),
        "response": _response_payload(response),
    }
    allure.attach(
        json.dumps(exchange, ensure_ascii=False),
        name=f"{response.request.method} {response.request.url.path} → {response.status_code}",
        attachment_type=HTTP_EXCHANGE_MIME,
        extension="httpexchange",
    )
    attach_text("curl", _to_curl(response.request))


def _to_curl(request: httpx.Request) -> str:
    parts = ["curl", "-X", request.method, shlex.quote(str(request.url))]
    for name, value in request.headers.items():
        parts += ["-H", shlex.quote(f"{name}: {_masked(name, value)}")]
    if request.content:
        parts += ["--data-raw", shlex.quote(request.content.decode(errors="replace"))]
    return " ".join(parts)


def _masked(header_name: str, value: str) -> str:
    return "***" if header_name.lower() in _REDACTED_HEADERS else value


def _headers(headers: httpx.Headers) -> list[dict[str, str]]:
    return [{"name": name, "value": _masked(name, value)} for name, value in headers.multi_items()]


def _body(content: bytes, content_type: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "encoding": "utf8",
        "value": content.decode(errors="replace"),
        "size": len(content),
    }
    if content_type:
        body["contentType"] = content_type
    if content_type and content_type.startswith("application/x-www-form-urlencoded"):
        body["form"] = [{"name": name, "value": value} for name, value in parse_qsl(body["value"])]
    return body


def _request_payload(request: httpx.Request) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "method": request.method,
        "url": str(request.url),
        "headers": _headers(request.headers),
    }
    if request.url.params:
        payload["query"] = [
            {"name": name, "value": value} for name, value in request.url.params.multi_items()
        ]
    if request.content:
        payload["body"] = _body(request.content, request.headers.get("content-type"))
    return payload


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": response.status_code,
        "statusText": response.reason_phrase,
        "headers": _headers(response.headers),
    }
    if response.content:
        payload["body"] = _body(response.content, response.headers.get("content-type"))
    return payload
