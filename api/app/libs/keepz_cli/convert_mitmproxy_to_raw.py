#!/usr/bin/env python3
"""
mitmproxy_dump_to_raw.py

Convert a mitmproxy dumpfile (saved with `mitmproxy -w flows.mitm`)
into raw HTTP request/response text files (one file per flow).

Usage:
  python3 mitmproxy_dump_to_raw.py -i flows.mitm -o out_raw

Notes:
- Only HTTP flows are exported (websocket-only flows may be skipped).
- Output files are bytes-preserving: bodies are written as-is (may be binary).
"""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mitmproxy import io
from mitmproxy.http import HTTPFlow

DELIM = b"\n\n" + b"=" * 30 + b" RESPONSE " + b"=" * 30 + b"\n\n"


def _iter_raw_headers(message) -> list[tuple[bytes, bytes]]:
    if hasattr(message, "raw_headers") and message.raw_headers is not None:
        return list(message.raw_headers)

    if hasattr(message, "headers") and message.headers is not None:
        return [
            (
                k.encode("latin-1", errors="replace"),
                v.encode("latin-1", errors="replace"),
            )
            for k, v in message.headers.items()
        ]

    return []


def _sanitize_filename(s: str, max_len: int = 140) -> str:
    s = s.strip().replace(os.sep, "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("._-")
    if not s:
        s = "flow"
    return s[:max_len]


def _format_http_request(flow: HTTPFlow) -> bytes:
    req = flow.request

    # mitmproxy provides http_version like "HTTP/1.1" or "HTTP/2.0"
    http_version = req.http_version or "HTTP/1.1"
    method = req.method or "GET"
    path = req.path or "/"

    # Use raw_headers to preserve original bytes (case/order) as much as possible.
    # raw_headers: list[tuple[bytes, bytes]]
    lines = [f"{method} {path} {http_version}".encode("utf-8")]

    for k, v in _iter_raw_headers(req):
        lines.append(k + b": " + v)

    head = b"\r\n".join(lines) + b"\r\n\r\n"
    body = req.raw_content or b""
    return head + body


def _format_http_response(flow: HTTPFlow) -> bytes:
    resp = flow.response
    if resp is None:
        return b""

    http_version = resp.http_version or "HTTP/1.1"
    status_code = resp.status_code or 0

    reason = resp.reason
    if not reason:
        # Avoid importing http.HTTPStatus just for a phrase; keep it minimal.
        reason = ""

    status_line = f"{http_version} {status_code} {reason}".rstrip().encode("utf-8")

    lines = [status_line]
    for k, v in _iter_raw_headers(resp):
        lines.append(k + b": " + v)

    head = b"\r\n".join(lines) + b"\r\n\r\n"
    body = resp.raw_content or b""
    return head + body


def _flow_timestamp(flow: HTTPFlow) -> str:
    # Prefer request timestamp_start (float seconds)
    ts = getattr(flow.request, "timestamp_start", None)
    if ts is None:
        return "unknown_time"
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%S.%fZ")


def _suggest_basename(flow: HTTPFlow, idx: int) -> str:
    req = flow.request
    host = req.host or "unknown_host"
    method = req.method or "GET"
    # Keep path short-ish for filenames
    path = req.path or "/"
    path = path.split("#", 1)[0]
    path = path[:80]

    base = f"{idx:06d}_{_flow_timestamp(flow)}_{host}_{method}_{path}"
    return _sanitize_filename(base)


def convert_dumpfile_to_raw(input_path: Path, output_dir: Path) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    written = 0

    with input_path.open("rb") as f:
        reader = io.FlowReader(f)
        for flow in reader.stream():
            total += 1

            if not isinstance(flow, HTTPFlow):
                continue

            # Require at least a request; response may be missing.
            if flow.request is None:
                continue

            req_bytes = _format_http_request(flow)
            resp_bytes = _format_http_response(flow)

            basename = _suggest_basename(flow, total)
            out_path = output_dir / f"{basename}.http"

            # Ensure uniqueness if collisions happen
            suffix = 1
            while out_path.exists():
                out_path = output_dir / f"{basename}_{suffix}.http"
                suffix += 1

            if resp_bytes:
                blob = req_bytes + DELIM + resp_bytes
            else:
                blob = (
                    req_bytes
                    + b"\n\n"
                    + b"=" * 30
                    + b" NO RESPONSE "
                    + b"=" * 30
                    + b"\n"
                )

            out_path.write_bytes(blob)
            written += 1

    return total, written


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert mitmproxy dump flows to raw request/response files."
    )
    ap.add_argument(
        "-i", "--input", required=True, help="mitmproxy dumpfile (e.g., flows.mitm)"
    )
    ap.add_argument(
        "-o", "--output-dir", required=True, help="output directory for .http files"
    )
    args = ap.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    total, written = convert_dumpfile_to_raw(input_path, output_dir)
    print(f"Done. Read {total} flows, wrote {written} HTTP files to: {output_dir}")


if __name__ == "__main__":
    main()
