"""Bounded public advisory transport; immutable observations, explicit freshness."""
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

from fusion_store import encode, require

MAX_BYTES = 8 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Advisory endpoint redirected; inspect the configured source")


def download(url, payload=None):
    headers = {"User-Agent": "security-fusion-advisory/1", "Accept": "application/json"}
    body = None if payload is None else encode(payload).encode("utf-8")
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=12) as response:
        raw = response.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "Advisory response exceeds 8 MiB; narrow the request")
    value = json.loads(raw)
    require(isinstance(value, dict), "Advisory response is not an object")
    return value


def valid_cache(value, key, now):
    return (isinstance(value, dict) and value.get("key") == key
            and isinstance(value.get("data"), dict)
            and isinstance(value.get("fetched_at"), (int, float))
            and 0 <= value["fetched_at"] <= now
            and value.get("sha256") == hashlib.sha256(encode(value["data"]).encode()).hexdigest())


def fetch(cache, source, url, payload=None, offline=False, refresh=False, ttl=3600, validate=None):
    """Only source builders choose URLs. Offline/stale results never imply live coverage."""
    now = time.time()
    key = hashlib.sha256(encode([url, payload]).encode()).hexdigest()
    root = Path(cache).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / (key + ".json")
    old = None
    try:
        candidate = json.loads(path.read_text(encoding="utf-8"))
        if valid_cache(candidate, key, now):
            if validate:
                validate(candidate["data"])
            old = candidate
    except (OSError, ValueError, KeyError, TypeError):
        pass
    metadata = {"source": source, "url": url, "checked_at": now}
    if offline or (old and not refresh and now - old["fetched_at"] < ttl):
        status = "offline_cache" if offline and old else "unavailable" if offline else "cache"
        return envelope(metadata, old, status, now, ttl)
    try:
        data = download(url, payload)
        if validate:
            validate(data)
        record = {"key": key, "fetched_at": now, "data": data,
                  "sha256": hashlib.sha256(encode(data).encode()).hexdigest()}
        temporary = root / (key + "." + uuid.uuid4().hex + ".tmp")
        with temporary.open("x", encoding="utf-8") as stream:
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            stream.write(encode(record))
        os.replace(temporary, path)
        return envelope(metadata, record, "live", now, ttl)
    except (OSError, ValueError, KeyError, TypeError) as error:
        # No retries or exception messages containing remote URLs/credentials.
        metadata["error"] = {"type": type(error).__name__}
        if isinstance(error, urllib.error.HTTPError):
            metadata["error"]["http_status"] = error.code
        return envelope(metadata, old, "stale_on_error" if old else "unavailable", now, ttl)


def envelope(metadata, record, status, now, ttl):
    return dict(metadata, status=status, fetched_at=record["fetched_at"] if record else None,
                age_seconds=round(now - record["fetched_at"]) if record else None,
                freshness="within_ttl" if record and now - record["fetched_at"] < ttl else "stale_or_missing",
                sha256=record["sha256"] if record else None, data=record["data"] if record else None)
