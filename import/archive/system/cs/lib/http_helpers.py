from __future__ import annotations

import http.client
from urllib.parse import urljoin, urlsplit

_SYMBOL_ROOTS = "$#&%@!"


def is_symbol(value) -> bool:
    return isinstance(value, str) and bool(value) and value[0] in _SYMBOL_ROOTS


def resolve_value(parser, value: str) -> str:
    if not is_symbol(value):
        return str(value)

    out = parser.state.get(value)
    if out["error"]:
        raise ValueError(out["error"])
    if out["result"] is None:
        raise ValueError(f"symbol not found: {value}")

    result = out["result"]
    if isinstance(result, (dict, list)):
        raise ValueError(f"symbol is not scalar: {value}")

    return str(result)


def request_text(
    method: str,
    url: str,
    body: str | bytes | None = None,
    headers: dict | None = None,
    timeout: int = 5,
    max_bytes: int = 200000,
    max_redirects: int = 5,
) -> dict:
    method = str(method).upper().strip()
    if method not in ("GET", "POST"):
        return {
            "ok": False,
            "status": 0,
            "content_type": "",
            "text": "",
            "error": f"unsupported method: {method}",
        }

    current_url = str(url).strip()
    current_method = method
    current_body = _to_bytes(body)
    current_headers = dict(headers or {})

    for _ in range(max_redirects + 1):
        parts = urlsplit(current_url)

        if parts.scheme not in ("http", "https"):
            return {
                "ok": False,
                "status": 0,
                "content_type": "",
                "text": "",
                "error": f"unsupported scheme: {parts.scheme or '(none)'}",
            }

        if not parts.hostname:
            return {
                "ok": False,
                "status": 0,
                "content_type": "",
                "text": "",
                "error": "invalid url",
            }

        conn_cls = (
            http.client.HTTPSConnection
            if parts.scheme == "https"
            else http.client.HTTPConnection
        )

        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query

        conn = None
        try:
            conn = conn_cls(parts.hostname, port=parts.port, timeout=timeout)
            request_body = current_body if current_method == "POST" else None
            conn.request(current_method, path, body=request_body, headers=current_headers)
            resp = conn.getresponse()

            status = int(resp.status)
            reason = str(resp.reason or "").strip()

            if status in (301, 302, 303, 307, 308):
                location = resp.getheader("Location")
                resp.read()
                conn.close()
                conn = None

                if not location:
                    return {
                        "ok": False,
                        "status": status,
                        "content_type": "",
                        "text": "",
                        "error": f"http {status} redirect without location",
                    }

                current_url = urljoin(current_url, location)

                if status == 303:
                    current_method = "GET"
                    current_body = None

                continue

            raw = _read_limited(resp, max_bytes)
            content_type = str(resp.getheader("Content-Type", "") or "")
            text = raw.decode("utf-8", errors="replace")

            return {
                "ok": 200 <= status < 300,
                "status": status,
                "content_type": content_type,
                "text": text,
                "error": None if 200 <= status < 300 else _http_error(status, reason),
            }

        except Exception as e:
            return {
                "ok": False,
                "status": 0,
                "content_type": "",
                "text": "",
                "error": str(e),
            }
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    return {
        "ok": False,
        "status": 0,
        "content_type": "",
        "text": "",
        "error": f"too many redirects (> {max_redirects})",
    }


def _to_bytes(body: str | bytes | None) -> bytes | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        return body
    return str(body).encode("utf-8")


def _read_limited(resp, max_bytes: int) -> bytes:
    chunks = []
    total = 0

    while True:
        chunk = resp.read(16384)
        if not chunk:
            break

        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"response too large (> {max_bytes} bytes)")

        chunks.append(chunk)

    return b"".join(chunks)


def _http_error(status: int, reason: str) -> str:
    if reason:
        return f"http {status}: {reason}"
    return f"http {status}"
