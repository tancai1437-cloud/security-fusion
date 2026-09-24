"""TEST ONLY: generic loopback request adapter, not a production MCP provider."""
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def exchange(arguments):
    target = arguments["target"]
    parsed = urlsplit(target)
    assert parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
    results = []
    for item in arguments["requests"]:
        request = Request(target, data=json.dumps(item["body"]).encode(),
                          headers={"Content-Type": "application/json",
                                   "X-Fixture-Identity": item["identity_ref"]})
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            results.append({"identity_ref": item["identity_ref"], "request": item["body"],
                            "status": response.status,
                            "body": json.loads(response.read(8192))})
    return {"content": [{"type": "text", "text": json.dumps(results)}], "isError": False}


trace = Path(sys.argv[1])
initialized = False
for line in sys.stdin:
    request = json.loads(line)
    method = request["method"]
    with trace.open("a", encoding="utf-8") as log:
        log.write(json.dumps({"method": method}) + "\n")
    if method == "notifications/initialized":
        initialized = True
        continue
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "TEST-ONLY-business-http", "version": "1"}}
    elif method == "tools/list":
        assert initialized
        result = {"tools": [{"name": "fixture_compare_requests", "inputSchema": {
            "type": "object", "properties": {"target": {"type": "string"},
            "identity_ref": {"type": "string"}, "requests": {"type": "array"}},
            "required": ["target", "identity_ref", "requests"]}}]}
    elif method == "tools/call":
        assert initialized and request["params"]["name"] == "fixture_compare_requests"
        result = exchange(request["params"]["arguments"])
    else:
        raise ValueError("Unexpected test protocol operation")
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
