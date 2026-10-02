"""Source-specific advisory queries. Matching an advisory is not target validation."""
from datetime import datetime, timedelta, timezone
import math
import re
from urllib.parse import urlencode

from fusion_intel_http import fetch
from fusion_store import require, text_field

CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,19}\Z")
ECOSYSTEMS = {"PyPI", "npm", "Maven", "Go", "RubyGems", "crates.io", "Packagist", "NuGet", "Debian", "Alpine"}


def cve_record(data, identity):
    meta = data.get("cveMetadata", {})
    require(isinstance(meta, dict) and meta.get("cveId") == identity and meta.get("state") in {"PUBLISHED", "REJECTED"}, "Invalid CVE record")
    container = data.get("containers", {})
    require(isinstance(container, dict) and isinstance(container.get("cna", {}), dict), "Invalid CNA container")


def kev_record(data):
    require(isinstance(data.get("vulnerabilities"), list) and isinstance(data.get("dateReleased"), str), "Invalid KEV catalog")
    require(data.get("count") == len(data["vulnerabilities"]), "Incomplete KEV catalog")
    require(all(isinstance(row, dict) and CVE.fullmatch(row.get("cveID", "")) for row in data["vulnerabilities"]), "Invalid KEV records")


def epss_record(data, identity):
    require(data.get("status") == "OK" and isinstance(data.get("data"), list), "Invalid EPSS response")
    for row in data["data"]:
        require(isinstance(row, dict) and row.get("cve") == identity and isinstance(row.get("date"), str), "Invalid EPSS identity/date")
        for key in ("epss", "percentile"):
            score = float(row[key])
            require(math.isfinite(score) and 0 <= score <= 1, "Invalid EPSS score")


def osv_record(data):
    require(isinstance(data.get("vulns", []), list) and "error" not in data and "code" not in data, "Invalid OSV response")
    require(all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in data.get("vulns", [])), "Invalid OSV records")


def nvd_record(data, offset):
    require(isinstance(data.get("vulnerabilities"), list) and isinstance(data.get("totalResults"), int), "Invalid NVD response")
    require(all(isinstance(row, dict) and isinstance(row.get("cve"), dict) and CVE.fullmatch(row["cve"].get("id", "")) for row in data["vulnerabilities"]), "Invalid NVD records")
    require(data.get("startIndex") == offset, "NVD page does not match requested offset")
    require(data["vulnerabilities"] or offset >= data["totalResults"], "NVD pagination stalled")


def public_name(value, name, maximum=160):
    text_field(value, name, maximum)
    require(not re.search(r"[\x00-\x1f]|://|[?&#=]", value), name + " must be public product/package metadata, not a target URL or request")
    return value


def lookup_cve(cache, data, options):
    identity = data.get("cve", "")
    require(isinstance(identity, str) and CVE.fullmatch(identity), "Use an exact CVE-YYYY-NNNN identifier")
    _, year, number = identity.split("-")
    bucket = number[:-3] + "xxx"
    cve = fetch(cache, "CVE List V5", f"https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/{year}/{bucket}/{identity}.json",
                validate=lambda value: cve_record(value, identity), **options)
    kev = fetch(cache, "CISA KEV official mirror", "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json",
                validate=kev_record, **options)
    if kev["data"] is not None:
        catalog = kev["data"]
        kev["data"] = {"dateReleased": catalog["dateReleased"], "catalogVersion": catalog.get("catalogVersion"),
                       "catalog_count": catalog["count"], "matches": [r for r in catalog["vulnerabilities"] if r.get("cveID") == identity]}
    epss = fetch(cache, "FIRST EPSS", "https://api.first.org/data/v1/epss?" + urlencode({"cve": identity}),
                 validate=lambda value: epss_record(value, identity), **options)
    return [cve, kev, epss]


def lookup_package(cache, data, options):
    require(data.get("ecosystem") in ECOSYSTEMS, "Unsupported package ecosystem; use the official ecosystem spelling")
    package = public_name(data.get("package"), "package")
    version = public_name(data.get("version"), "version", 100)
    payload = {"package": {"name": package, "ecosystem": data["ecosystem"]}, "version": version}
    if data.get("cursor"):
        text_field(data["cursor"], "OSV cursor", 2000)
        payload["page_token"] = data["cursor"]
    def validate_page(value):
        osv_record(value)
        require(not value.get("next_page_token") or value["next_page_token"] != payload.get("page_token"), "OSV pagination stalled")
    return [fetch(cache, "OSV", "https://api.osv.dev/v1/query", payload, validate=validate_page, **options)]


def recent(cache, data, options):
    days, offset = data.get("days", 1), data.get("offset", 0)
    require(type(days) is int and 1 <= days <= 7 and type(offset) is int and 0 <= offset <= 1000000,
            "Use days 1..7 and a nonnegative NVD offset")
    end = data.get("until")
    if end:
        text_field(end, "until", 32)
        end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        require(end.tzinfo is not None and end <= datetime.now(timezone.utc), "until must be an explicit past UTC timestamp")
    else:
        end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    params = {"lastModStartDate": (end - timedelta(days=days)).isoformat(), "lastModEndDate": end.isoformat(),
              "resultsPerPage": 20, "startIndex": offset}
    if data.get("product"):
        params["keywordSearch"] = public_name(data["product"], "public product name")
    result = fetch(cache, "NVD modified records", "https://services.nvd.nist.gov/rest/json/cves/2.0?" + urlencode(params),
                   validate=lambda value: nvd_record(value, offset), **options)
    result["window"] = {"since": params["lastModStartDate"], "until": params["lastModEndDate"], "offset": offset}
    return [result]


def lookup(cache, data):
    options = {key: data.get(key, False) for key in ("offline", "refresh")}
    require(all(type(value) is bool for value in options.values()), "offline/refresh must be booleans")
    require(not all(options.values()), "offline and refresh cannot both be true")
    operations = {"cve": lookup_cve, "package": lookup_package, "recent": recent}
    require(data.get("mode") in operations, "Unknown public intelligence mode")
    return operations[data["mode"]](cache, data, options)
