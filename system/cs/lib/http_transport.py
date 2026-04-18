from __future__ import annotations

import http.client
import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

from system.state.api import read_value


_STREAM_TCP_KEEPIDLE = 15
_STREAM_TCP_KEEPINTVL = 15
_STREAM_TCP_KEEPCNT = 4


class HTTPTransportError(Exception):
    pass


@dataclass
class HTTPResponse:
    status: int
    reason: str
    headers: dict[str, str]
    body: bytes
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= int(self.status) < 300

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        try:
            return json.loads(self.text)
        except Exception as exc:
            raise HTTPTransportError(f"invalid JSON response: {exc}") from exc


class HTTPStream:
    def __init__(
        self,
        conn: http.client.HTTPConnection,
        response: http.client.HTTPResponse,
        url: str,
    ) -> None:
        self.conn = conn
        self.response = response
        self.url = url
        self.status = int(response.status)
        self.reason = str(response.reason or "")
        self.headers = _headers_dict(response)

    def readline(self) -> bytes:
        return self.response.readline()

    def close(self) -> None:
        try:
            self.response.close()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


_SYMBOL_ROOTS = "$#&%@!|"


def is_symbol(value) -> bool:
    return isinstance(value, str) and bool(value) and value[0] in _SYMBOL_ROOTS


def resolve_value(parser, value: str) -> str:
    if not is_symbol(value):
        return str(value)

    result = read_value(parser.state, value, None)
    if result is None:
        raise ValueError(f"symbol not found: {value}")
    if isinstance(result, (dict, list)):
        raise ValueError(f"symbol is not scalar: {value}")

    return str(result)


def request(
    method: str,
    url: str,
    *,
    body: str | bytes | None = None,
    headers: dict[str, Any] | None = None,
    timeout: float = 5,
    max_bytes: int = 200000,
    max_redirects: int = 5,
) -> HTTPResponse:
    current_url = str(url or "").strip()
    current_method = str(method or "GET").upper().strip()
    current_body = _to_bytes(body)
    current_headers = _normalize_headers(headers)

    if current_method == "POST" and current_body is not None and "content-length" not in current_headers:
        current_headers["Content-Length"] = str(len(current_body))

    for _ in range(max_redirects + 1):
        conn = None
        try:
            conn, path = _open_connection(current_url, float(timeout))
            conn.request(current_method, path, body=current_body, headers=current_headers)
            response = conn.getresponse()
            status = int(response.status)

            if status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                response.read()
                conn.close()
                conn = None

                if not location:
                    raise HTTPTransportError(f"http {status}: redirect without location")

                current_url = urljoin(current_url, location)
                if status == 303:
                    current_method = "GET"
                    current_body = None
                    current_headers.pop("Content-Length", None)
                continue

            raw = _read_limited(response, max_bytes)
            return HTTPResponse(
                status=status,
                reason=str(response.reason or ""),
                headers=_headers_dict(response),
                body=raw,
                url=current_url,
            )

        except socket.timeout as exc:
            raise HTTPTransportError(f"timeout: {exc}") from exc
        except TimeoutError as exc:
            raise HTTPTransportError(f"timeout: {exc}") from exc
        except OSError as exc:
            raise HTTPTransportError(str(exc)) from exc
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    raise HTTPTransportError(f"too many redirects (> {max_redirects})")


def request_json(
    method: str,
    url: str,
    *,
    body: str | bytes | None = None,
    headers: dict[str, Any] | None = None,
    timeout: float = 5,
    max_bytes: int = 200000,
    max_redirects: int = 5,
) -> Any:
    response = request(
        method,
        url,
        body=body,
        headers=headers,
        timeout=timeout,
        max_bytes=max_bytes,
        max_redirects=max_redirects,
    )

    if not response.ok:
        raise HTTPTransportError(_http_error(response.status, response.reason, response.text))

    ctype = response.headers.get("content-type", "").lower()
    if "application/json" in ctype:
        return response.json()

    try:
        return response.json()
    except HTTPTransportError:
        return response.text


def request_text(
    method: str,
    url: str,
    body: str | bytes | None = None,
    headers: dict | None = None,
    timeout: int = 5,
    max_bytes: int = 200000,
    max_redirects: int = 5,
) -> dict:
    try:
        response = request(
            method,
            url,
            body=body,
            headers=headers,
            timeout=float(timeout),
            max_bytes=max_bytes,
            max_redirects=max_redirects,
        )
    except Exception as exc:
        return {
            "ok": False,
            "status": 0,
            "content_type": "",
            "text": "",
            "error": str(exc),
        }

    text = response.text
    return {
        "ok": response.ok,
        "status": response.status,
        "content_type": response.headers.get("content-type", ""),
        "text": text,
        "error": None if response.ok else _http_error(response.status, response.reason, text),
    }


def open_stream(
    method: str,
    url: str,
    *,
    body: str | bytes | None = None,
    headers: dict[str, Any] | None = None,
    connect_timeout: float = 30.0,
    read_timeout: float | None = None,
    max_redirects: int = 2,
    tcp_keepalive: bool = True,
) -> HTTPStream:
    current_url = str(url or "").strip()
    current_method = str(method or "GET").upper().strip()
    current_body = _to_bytes(body)
    current_headers = _normalize_headers(headers)

    if current_method == "POST" and current_body is not None and "content-length" not in current_headers:
        current_headers["Content-Length"] = str(len(current_body))
    if "connection" not in current_headers:
        current_headers["Connection"] = "keep-alive"
    if "accept" not in current_headers:
        current_headers["Accept"] = "text/event-stream, application/x-ndjson, application/json"

    for _ in range(max_redirects + 1):
        conn = None
        try:
            conn, path = _open_connection(current_url, float(connect_timeout))
            conn.request(current_method, path, body=current_body, headers=current_headers)
            response = conn.getresponse()
            status = int(response.status)

            if status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                response.read()
                conn.close()
                conn = None

                if not location:
                    raise HTTPTransportError(f"http {status}: redirect without location")

                current_url = urljoin(current_url, location)
                if status == 303:
                    current_method = "GET"
                    current_body = None
                    current_headers.pop("Content-Length", None)
                continue

            if not (200 <= status < 300):
                raw = _read_limited(response, 65536)
                message = _http_error(status, str(response.reason or ""), raw.decode("utf-8", errors="replace"))
                response.close()
                conn.close()
                raise HTTPTransportError(message)

            _configure_stream_socket(conn, read_timeout=read_timeout, tcp_keepalive=tcp_keepalive)
            return HTTPStream(conn, response, current_url)

        except socket.timeout as exc:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            raise HTTPTransportError(f"timeout: {exc}") from exc
        except TimeoutError as exc:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            raise HTTPTransportError(f"timeout: {exc}") from exc
        except OSError as exc:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            raise HTTPTransportError(str(exc)) from exc

    raise HTTPTransportError(f"too many redirects (> {max_redirects})")


def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (headers or {}).items():
        if value is None:
            continue
        text_key = str(key)
        if not text_key:
            continue
        out[text_key] = str(value)
    return out


def _open_connection(url: str, timeout: float) -> tuple[http.client.HTTPConnection, str]:
    parts = urlsplit(str(url or "").strip())

    if parts.scheme not in ("http", "https"):
        raise HTTPTransportError(f"unsupported scheme: {parts.scheme or '(none)'}")
    if not parts.hostname:
        raise HTTPTransportError("invalid url")

    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(parts.hostname, port=parts.port, timeout=timeout)

    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query

    return conn, path


def _headers_dict(response: http.client.HTTPResponse) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in response.getheaders()}


def _to_bytes(body: str | bytes | None) -> bytes | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        return body
    return str(body).encode("utf-8")


def _read_limited(response: http.client.HTTPResponse, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = response.read(16384)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPTransportError(f"response too large (> {max_bytes} bytes)")
        chunks.append(chunk)

    return b"".join(chunks)


def _configure_stream_socket(
    conn: http.client.HTTPConnection,
    *,
    read_timeout: float | None,
    tcp_keepalive: bool,
) -> None:
    sock = getattr(conn, "sock", None)
    if sock is None:
        return

    try:
        if read_timeout in (None, ""):
            sock.settimeout(None)
        else:
            sock.settimeout(float(read_timeout))
    except Exception:
        pass

    if not tcp_keepalive:
        return

    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception:
        return

    ioctl = getattr(sock, "ioctl", None)
    if callable(ioctl) and hasattr(socket, "SIO_KEEPALIVE_VALS"):
        try:
            ioctl(
                socket.SIO_KEEPALIVE_VALS,
                (
                    1,
                    int(_STREAM_TCP_KEEPIDLE * 1000),
                    int(_STREAM_TCP_KEEPINTVL * 1000),
                ),
            )
        except Exception:
            pass

    try:
        if hasattr(socket, "TCP_KEEPIDLE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, _STREAM_TCP_KEEPIDLE)
        elif hasattr(socket, "TCP_KEEPALIVE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, _STREAM_TCP_KEEPIDLE)
    except Exception:
        pass

    try:
        if hasattr(socket, "TCP_KEEPINTVL"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, _STREAM_TCP_KEEPINTVL)
    except Exception:
        pass

    try:
        if hasattr(socket, "TCP_KEEPCNT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, _STREAM_TCP_KEEPCNT)
    except Exception:
        pass


def _http_error(status: int, reason: str, text: str) -> str:
    detail = str(text or "").strip()
    if detail:
        return f"http {int(status)}: {detail}"
    reason = str(reason or "").strip()
    if reason:
        return f"http {int(status)}: {reason}"
    return f"http {int(status)}"
