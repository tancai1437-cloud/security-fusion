"""TEST ONLY MCP server; HTTP requests are limited to loopback. Not a real provider."""
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

trace = Path(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "ok"
initialized = False
for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    with trace.open("a", encoding="utf-8") as log:
        log.write(json.dumps({"method": method}) + "\n")
    if method == "notifications/initialized":
        initialized = True
        continue
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "SYNTHETIC-loopback-fixture", "version": "1"}}
    elif method == "tools/list":
        assert initialized
        tool = {"name": "fixture_http_read", "inputSchema": {"type": "object",
                "properties": {"target": {"type": "string"}}, "required": ["target"]}}
        if mode == "missing":
            result = {"tools": []}
        elif mode == "paged" and not request.get("params", {}).get("cursor"):
            result = {"tools": [], "nextCursor": "second"}
        else:
            result = {"tools": [tool]}
    elif method == "tools/call":
        assert initialized and request["params"]["name"] == "fixture_http_read"
        if mode == "timeout":
            time.sleep(10)
        if mode == "error":
            result = {"isError": True, "content": [{"type": "text", "text": "Fixture tool failure"}]}
        elif mode == "rpc-error":
            print(json.dumps({"jsonrpc": "2.0", "id": request["id"],
                              "error": {"code": -32602, "message": "Fixture invalid arguments"}}), flush=True)
            continue
        elif mode == "task":
            result = {"task": {"taskId": "fixture-pending", "status": "working"}}
        else:
            target = request["params"]["arguments"]["target"]
            assert urlsplit(target).hostname == "127.0.0.1"
            with urlopen(target, timeout=3) as response:
                body = response.read(4096).decode("utf-8")
            result = {"content": [{"type": "text", "text": body}], "isError": False}
    else:
        result = {}
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
