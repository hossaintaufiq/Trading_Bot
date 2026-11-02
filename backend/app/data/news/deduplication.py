"""
NEPTUNE News Deduplication & Event Clustering Engine (`deduplication.py`)

Implements a rigorous 6-stage deduplication and clustering pipeline:
1. Exact URL matching
2. Canonical URL matching (tracking params stripped, scheme/trailing slashes normalized)
3. Exact normalized headline matching (lowercased, punctuation removed, whitespace collapsed)
4. 64-bit SimHash candidate similarity (Hamming distance <= 3)
5. Entity and event-category validation (must share entity/symbol overlap)
6. Time-window validation (sliding 24-hour chronological window)

Enforces Rule: Distinct real-world events must never be merged merely because they
discuss the same asset or share template phrasing across different dates.
Governed by: Rule S-05, ADR-023.
"""
import hashlib
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.data.news.models import NewsArticle, NewsEventCluster, ReviewStatus
from app.data.news.temporal import parse_iso_utc


def canonicalize_url(url: str) -> str:
    """
    Produce canonical URL by stripping marketing query parameters, fragments,
    normalizing scheme to https, and stripping trailing slashes.
    """
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Filter tracking query parameters
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "ref", "ref_src", "fbclid", "gclid", "source", "ncid", "guccounter"
        }
        query_items = urllib.parse.parse_qsl(parsed.query)
        filtered_query = [
            (k, v) for k, v in query_items if k.lower() not in tracking_params
        ]
        query_str = urllib.parse.urlencode(sorted(filtered_query))

        # Normalize scheme to https (unless local/file)
        scheme = "https" if parsed.scheme in ["http", "https"] else parsed.scheme

        return urllib.parse.urlunparse((scheme, netloc, path, "", query_str, ""))
    except Exception:
        return url.strip().rstrip("/")


def normalize_title(title: str) -> str:
    """
    Normalize headline: lowercase, strip punctuation and non-alphanumeric chars,
    and collapse whitespace. Handles numbers and contractions cleanly.
    """
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    t = re.sub(r"['’]", "", t)
    cleaned = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", cleaned).strip()


def compute_simhash_64(text: str) -> int:
    """
    Compute a deterministic 64-bit SimHash fingerprint for text using
    sliding 4-character n-grams on normalized text.
    Provides mathematically stable near-duplicate detection.
    """
    if not text:
        return 0

    norm_text = normalize_title(text)
    if not norm_text:
        return 0

    n = 4
    if len(norm_text) <= n:
        ngrams = [norm_text]
    else:
        ngrams = [norm_text[i : i + n] for i in range(len(norm_text) - n + 1)]

    v = [0] * 64
    for token in ngrams:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        token_hash = int.from_bytes(digest[:8], byteorder="big", signed=False)
        for i in range(64):
            bit = (token_hash >> i) & 1
            if bit == 1:
                v[i] += 1
            else:
                v[i] -= 1

    simhash = 0
    for i in range(64):
        if v[i] > 0:
            simhash |= 1 << i

    return simhash


def hamming_distance_64(hash1: int, hash2: int) -> int:
    """Calculate the Hamming distance (number of differing bits) between two 64-bit integers."""
    x = (hash1 ^ hash2) & 0xFFFFFFFFFFFFFFFF
    return bin(x).count("1")


def are_articles_event_duplicates(
    art1: Dict[str, Any],
    art2: Dict[str, Any],
    max_time_delta_seconds: int = 86400,  # 24 hours
) -> Tuple[bool, float, Dict[str, Any]]:
    """
    Evaluate whether two articles represent the same underlying real-world event.

    Returns:
        (is_duplicate, confidence_score, evidence_dict)
    """
    # Stage 1: Exact URL match
    if art1.get("url") and art1.get("url") == art2.get("url"):
        return True, 1.0, {"stage": "exact_url", "detail": "Identical URL"}

    # Stage 2: Canonical URL match
    canon1 = art1.get("canonical_url") or canonicalize_url(art1.get("url", ""))
    canon2 = art2.get("canonical_url") or canonicalize_url(art2.get("url", ""))
    if canon1 and canon1 == canon2:
        return True, 0.99, {"stage": "canonical_url", "canonical_url": canon1}

    # Temporal Window Verification (Rule S-05):
    # Articles occurring > 24 hours apart are NEVER merged into the same event.
    t1_iso = art1.get("available_at") or art1.get("published_at") or art1.get("provider_seen_at")
    t2_iso = art2.get("available_at") or art2.get("published_at") or art2.get("provider_seen_at")

    dt1 = parse_iso_utc(t1_iso)
    dt2 = parse_iso_utc(t2_iso)

    if dt1 and dt2:
        delta_sec = abs((dt1 - dt2).total_seconds())
        if delta_sec > max_time_delta_seconds:
            return False, 0.0, {
                "stage": "time_window_exceeded",
                "delta_seconds": delta_sec,
                "max_allowed": max_time_delta_seconds,
            }
    else:
        delta_sec = 0.0

    # Entity / Symbol Overlap Verification:
    # Must share at least one target asset/entity if entities are defined.
    ent1 = set(art1.get("entities") or [])
    ent2 = set(art2.get("entities") or [])
    shared_entities = ent1.intersection(ent2)

    # Stage 3: Exact Normalized Headline Match
    norm_title1 = art1.get("normalized_title") or normalize_title(art1.get("title", ""))
    norm_title2 = art2.get("normalized_title") or normalize_title(art2.get("title", ""))

    if norm_title1 and norm_title1 == norm_title2:
        return True, 0.95, {
            "stage": "exact_normalized_title",
            "title": norm_title1,
            "delta_seconds": delta_sec,
            "shared_entities": list(shared_entities),
        }

    # Stage 4: SimHash Similarity
    h1 = art1.get("simhash") or compute_simhash_64(art1.get("title", ""))
    h2 = art2.get("simhash") or compute_simhash_64(art2.get("title", ""))
    dist = hamming_distance_64(h1, h2)

    if dist <= 3:
        # Stage 5: Entity and Context Comparison
        # To avoid false merges of different events with similar headline templates,
        # require either entity overlap or high text length
        if (ent1 and ent2 and not shared_entities):
            return False, 0.0, {
                "stage": "simhash_entity_mismatch",
                "distance": dist,
                "entities1": list(ent1),
                "entities2": list(ent2),
            }

        confidence = max(0.70, 0.90 - (dist * 0.05))
        return True, confidence, {
            "stage": "simhash_near_duplicate",
            "simhash_distance": dist,
            "delta_seconds": delta_sec,
            "shared_entities": list(shared_entities),
        }

    return False, 0.0, {"stage": "no_match", "simhash_distance": dist}


class NewsEventClusterer:
    """
    Clusters a list of news articles into deduplicated real-world event clusters.
    """

    def __init__(self, max_time_delta_seconds: int = 86400, simhash_threshold: int = 3):
        self.max_time_delta_seconds = max_time_delta_seconds
        self.simhash_threshold = simhash_threshold

    def cluster_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Partition articles into event clusters.

        Returns list of cluster dicts:
        [
            {
                "cluster_id": "...",
                "cluster_title": "...",
                "primary_symbol": "BTC",
                "earliest_available_at": "...",
                "article_count": N,
                "clustering_algorithm": "simhash_v1_entity_matched",
                "confidence_score": 0.95,
                "matching_evidence": {...},
                "review_status": "UNREVIEWED",
                "created_at": "...",
                "members": [("article_id_1", distance_0), ("article_id_2", distance_2)]
            }
        ]
        """
        if not articles:
            return []

        # Sort articles chronologically by available_at / published_at
        def get_sort_key(a: Dict[str, Any]) -> str:
            return (
                a.get("available_at")
                or a.get("published_at")
                or a.get("provider_seen_at")
                or a.get("created_at")
                or ""
            )

        sorted_articles = sorted(articles, key=get_sort_key)

        # Precompute SimHash, canonical URL, and normalized title
        for art in sorted_articles:
            if "canonical_url" not in art or not art["canonical_url"]:
                art["canonical_url"] = canonicalize_url(art.get("url", ""))
            if "normalized_title" not in art or not art["normalized_title"]:
                art["normalized_title"] = normalize_title(art.get("title", ""))
            if "simhash" not in art:
                art["simhash"] = compute_simhash_64(art.get("title", ""))

        clusters: List[Dict[str, Any]] = []

        for art in sorted_articles:
            matched_cluster = None
            best_evidence = None
            best_confidence = 0.0
            best_dist = 0

            # Compare against existing clusters (represented by their leader / earliest article)
            for cl in clusters:
                leader = cl["leader_article"]
                is_dup, conf, evidence = are_articles_event_duplicates(
                    art, leader, max_time_delta_seconds=self.max_time_delta_seconds
                )
                if is_dup and conf > best_confidence:
                    matched_cluster = cl
                    best_confidence = conf
                    best_evidence = evidence
                    best_dist = evidence.get("simhash_distance", 0)

            if matched_cluster:
                # Add to existing cluster
                matched_cluster["members"].append((art["article_id"], best_dist))
                matched_cluster["article_count"] += 1

                # Update earliest_available_at if earlier
                art_avail = art.get("available_at") or art.get("published_at") or art.get("created_at")
                if art_avail and art_avail < matched_cluster["earliest_available_at"]:
                    matched_cluster["earliest_available_at"] = art_avail

                # Update confidence to the minimum confidence among members
                matched_cluster["confidence_score"] = min(
                    matched_cluster["confidence_score"], best_confidence
                )
            else:
                # Create a new cluster
                avail = (
                    art.get("available_at")
                    or art.get("published_at")
                    or art.get("provider_seen_at")
                    or art.get("created_at")
                )
                cluster_id = "cl_" + hashlib.sha256(
                    f"{art['article_id']}_{avail}".encode("utf-8")
                ).hexdigest()[:16]

                primary_sym = None
                ents = art.get("entities") or []
                for s in ["BTC", "ETH", "BNB"]:
                    if s in ents:
                        primary_sym = s
                        break
                if not primary_sym and ents:
                    primary_sym = ents[0]

                now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

                new_cluster = {
                    "cluster_id": cluster_id,
                    "cluster_title": art.get("title", "Untitled Event"),
                    "primary_symbol": primary_sym,
                    "earliest_available_at": avail,
                    "article_count": 1,
                    "clustering_algorithm": "simhash_v1_entity_matched",
                    "confidence_score": 1.0,
                    "matching_evidence": {
                        "seed_article_id": art["article_id"],
                        "seed_url": art.get("url"),
                    },
                    "review_status": "UNREVIEWED",
                    "created_at": now_iso,
                    "leader_article": art,
                    "members": [(art["article_id"], 0)],
                }
                clusters.append(new_cluster)

        # Remove leader_article before returning
        for cl in clusters:
            cl.pop("leader_article", None)

        return clusters
