#!/usr/bin/env python3
"""Check documented CodeGraph MCP capabilities against the installed server."""

from __future__ import annotations

import argparse
import json
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TOOLS = {
    "codegraph_callers",
    "codegraph_callees",
    "codegraph_explore",
    "codegraph_files",
    "codegraph_impact",
    "codegraph_node",
    "codegraph_search",
    "codegraph_status",
}
TOOL_PATTERN = re.compile(r"\bcodegraph_[a-z_]+\b")


def static_check() -> list[str]:
    paths = [
        PLUGIN_ROOT / "README.md",
        *(PLUGIN_ROOT / "reference").rglob("*.md"),
        *(PLUGIN_ROOT / "skills").rglob("*.md"),
    ]
    errors: list[str] = []
    documented_in_readme: set[str] = set()
    for path in paths:
        documented = set(TOOL_PATTERN.findall(path.read_text(encoding="utf-8")))
        if path == PLUGIN_ROOT / "README.md":
            documented_in_readme = documented
        for tool in sorted(documented - REQUIRED_TOOLS):
            errors.append(
                f"{path.relative_to(PLUGIN_ROOT)}: unsupported MCP tool `{tool}`; "
                "remove it or update REQUIRED_TOOLS after a live check"
            )
    missing = sorted(REQUIRED_TOOLS - documented_in_readme)
    if missing:
        errors.append(f"README.md: required MCP tools are not documented: {', '.join(missing)}")
    return errors


def read_response(lines: queue.Queue[str], request_id: int, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            line = lines.get(timeout=deadline - time.monotonic())
        except queue.Empty:
            break
        response = json.loads(line)
        if response.get("id") == request_id:
            return response
    raise RuntimeError(f"CodeGraph MCP did not answer request {request_id} within {timeout:g}s")


def send(process: subprocess.Popen[str], message: dict) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def collect_lines(stream, lines: queue.Queue[str]) -> None:
    for line in stream:
        lines.put(line)


def live_check(timeout: float) -> list[str]:
    config = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = config["codegraph"]
    command = [server["command"], *server.get("args", [])]
    process = subprocess.Popen(
        command,
        cwd=Path.cwd(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    try:
        assert process.stdout is not None
        lines: queue.Queue[str] = queue.Queue()
        threading.Thread(
            target=collect_lines, args=(process.stdout, lines), daemon=True
        ).start()
        send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mc-skills-check", "version": "0.1.0"},
                },
            },
        )
        initialized = read_response(lines, 1, timeout)
        if "error" in initialized:
            return [f"CodeGraph MCP initialize failed: {initialized['error']}"]
        send(
            process,
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )
        send(
            process,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        response = read_response(lines, 2, timeout)
        if "error" in response:
            return [f"CodeGraph MCP tools/list failed: {response['error']}"]
        available = {
            tool["name"] for tool in response.get("result", {}).get("tools", [])
        }
        missing = sorted(REQUIRED_TOOLS - available)
        return [f"CodeGraph MCP is missing required tools: {', '.join(missing)}"] if missing else []
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--static", action="store_true", help="check documented tool names")
    mode.add_argument("--live", action="store_true", help="query the installed MCP server")
    parser.add_argument("--timeout", type=float, default=10, help="live request timeout")
    args = parser.parse_args()

    try:
        errors = live_check(args.timeout) if args.live else static_check()
    except (FileNotFoundError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if not errors:
        print("CodeGraph MCP capability check passed.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
