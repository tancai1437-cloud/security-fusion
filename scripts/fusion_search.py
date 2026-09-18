"""Local lexical ranking and optional exact-vector/RRF retrieval, without network calls."""
from collections import Counter
import hashlib
import math
import re

from fusion_store import require, text_field


def tokens(text):
    """English identifiers plus Chinese single characters/bigrams; no semantic expansion."""
    result = []
    for part in re.findall(r"[a-zA-Z0-9_]+|[\u3400-\u9fff]+", text.lower()):
        if "\u3400" <= part[0] <= "\u9fff":
            result.extend(part)
            result.extend(part[i:i + 2] for i in range(len(part) - 1))
        else:
            result.append(part)
    return result


def text_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embedding(data, expected_digest):
    require(isinstance(data, dict), "Embedding must be an object")
    text_field(data.get("model"), "embedding model/version", 200)
    require(data.get("text_sha256") == expected_digest, "Embedding text hash mismatch")
    vector = data.get("vector")
    require(isinstance(vector, list) and 1 <= len(vector) <= 4096, "Invalid embedding dimensions")
    require(all(isinstance(v, (float, int)) and not isinstance(v, bool) and
                -1e300 <= v <= 1e300 and math.isfinite(v) for v in vector),
            "Embedding components must be finite numbers")
    norm = math.hypot(*vector)
    require(math.isfinite(norm) and norm > 0, "Embedding must have a finite nonzero norm")
    return data["model"], [v / norm for v in vector]


def fallback_bm25(rows, query_terms):
    """Used only if this Python SQLite build lacks FTS5."""
    documents = {r["id"]: Counter(tokens(r["search_text"])) for r in rows}
    if not documents:
        return []
    average = sum(sum(d.values()) for d in documents.values()) / len(documents) or 1
    scores = {}
    for term in set(query_terms):
        frequency = sum(term in d for d in documents.values())
        inverse = math.log(1 + (len(documents) - frequency + 0.5) / (frequency + 0.5))
        for identity, document in documents.items():
            count = document[term]
            if count:
                scores[identity] = scores.get(identity, 0) + inverse * count * 2.2 / (
                    count + 1.2 * (0.25 + 0.75 * sum(document.values()) / average))
    return sorted(scores, key=lambda identity: (-scores[identity], identity))


def fused(lexical, semantic):
    scores = {}
    reasons = {}
    for label, ranking in (("lexical", lexical), ("vector", semantic)):
        for rank, identity in enumerate(ranking, 1):
            scores[identity] = scores.get(identity, 0) + 1 / (60 + rank)
            reasons.setdefault(identity, []).append(label)
    return [(identity, reasons[identity]) for identity in
            sorted(scores, key=lambda identity: (-scores[identity], identity))]
