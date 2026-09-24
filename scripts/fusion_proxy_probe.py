"""Three anonymous exact-URL GET controls for proxy trust observations."""
import argparse
import base64
import hashlib
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

BODY_LIMIT = 64 * 1024
VARIANTS = (None, "192.0.2.17", "192.0.2.17, 198.51.100.29")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(url):
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.fragment or any(ord(c) < 33 for c in url)):
        raise ValueError("Use an exact HTTP(S) URL without userinfo, fragment or control characters")
    # Ignore inherited proxy variables: the tested path is explicitly the supplied URL.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    results = []
    for marker in VARIANTS:
        headers = {"User-Agent": "security-fusion-proxy-controls/1", "Accept-Encoding": "identity"}
        if marker:
            headers["X-Forwarded-For"] = marker
        row = {"method": "GET", "url": url, "request_headers": headers}
        response = None
        try:
            try:
                response = opener.open(Request(url, headers=headers), timeout=5)
            except HTTPError as exc:
                response = exc
            body = response.read(BODY_LIMIT + 1)
            captured = body[:BODY_LIMIT]
            row.update(status=response.code, response_headers=list(response.headers.items()),
                       body_base64=base64.b64encode(captured).decode("ascii"),
                       captured_sha256=hashlib.sha256(captured).hexdigest(),
                       captured_bytes=len(captured), truncated=len(body) > BODY_LIMIT)
        except (OSError, URLError, ValueError) as exc:
            row["error"] = str(exc)
        finally:
            if response is not None:
                response.close()
        results.append(row)
    return {"requests": results, "verdict": "observations_only", "redirects_followed": False,
            "limits": "Response differences or marker reflection do not prove a trust or authorization bypass; compare configured trusted hops and an actual protected decision"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        result = probe(args.url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if any("error" in row for row in result["requests"]) else 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
