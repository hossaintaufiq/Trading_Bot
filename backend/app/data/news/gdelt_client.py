"""
NEPTUNE GDELT GKG 2.0 Historical Ingestion Client (`gdelt_client.py`)

Ingests raw 15-minute GKG CSV zip archives from data.gdeltproject.org:
- Preserves raw archive identity, MD5 verification, and line fingerprints.
- Pure in-memory streaming decompression (no temporary disk clutter).
- Word-boundary cryptocurrency entity extraction for BTC, ETH, and BNB.
- Enforces PARTIALLY_VERIFIED status with conservative 5-minute latency buffer.
- Never promotes GDELT indexing timestamps to publisher publication timestamps.
Governed by: Rule S-05, ADR-023.
"""
import asyncio
import hashlib
import io
import logging
import re
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.data.news.deduplication import canonicalize_url, normalize_title
from app.data.news.models import (
    NewsArticle,
    NewsArticleVersion,
    NewsSourceType,
    SourceVerificationStatus,
    TimestampPrecision,
)
from app.data.news.temporal import resolve_temporal_coordinates, to_iso_utc

logger = logging.getLogger(__name__)


# Compiled word-boundary regular expressions for asset detection
CRYPTO_PATTERNS = {
    "BTC": re.compile(r"\b(bitcoin|btc|satoshi|halving)\b", re.IGNORECASE),
    "ETH": re.compile(r"\b(ethereum|ether|eth|vitalik)\b", re.IGNORECASE),
    "BNB": re.compile(r"\b(binance|bnb)\b", re.IGNORECASE),
}

PAGE_TITLE_REGEX = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.IGNORECASE | re.DOTALL)


class GdeltGkgClient:
    """Client for raw GDELT 2.0 Global Knowledge Graph (GKG) 15-minute archives."""

    ARCHIVE_BASE_URL = "http://data.gdeltproject.org/gdeltv2"
    LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    MASTER_LIST_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"

    def __init__(self, timeout: float = 30.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            "Accept": "*/*",
        }

    async def fetch_last_update_manifest(self) -> Dict[str, Dict[str, str]]:
        """
        Fetch the current 15-minute manifest from lastupdate.txt.
        Returns dict keyed by file type ('export', 'mentions', 'gkg').
        """
        loop = asyncio.get_running_loop()
        req = urllib.request.Request(self.LAST_UPDATE_URL, headers=self.headers)

        def _fetch():
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8")

        text = await loop.run_in_executor(None, _fetch)
        manifest = {}
        for line in text.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 3:
                size, md5, url = parts[0], parts[1], parts[2]
                if "gkg.csv.zip" in url:
                    manifest["gkg"] = {"size": size, "md5": md5, "url": url}
                elif "export.CSV.zip" in url:
                    manifest["export"] = {"size": size, "md5": md5, "url": url}
                elif "mentions.CSV.zip" in url:
                    manifest["mentions"] = {"size": size, "md5": md5, "url": url}
        return manifest

    async def download_archive(
        self, archive_url: str, expected_md5: Optional[str] = None
    ) -> bytes:
        """
        Download GDELT zip archive with retry logic and optional MD5 verification.
        """
        loop = asyncio.get_running_loop()
        delay = 1.0
        last_exc = None

        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(archive_url, headers=self.headers)

                def _download():
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        return resp.read()

                data = await loop.run_in_executor(None, _download)

                if expected_md5:
                    actual_md5 = hashlib.md5(data).hexdigest()
                    if actual_md5.lower() != expected_md5.lower():
                        raise ValueError(
                            f"MD5 mismatch for {archive_url}: expected {expected_md5}, got {actual_md5}"
                        )

                return data
            except Exception as e:
                last_exc = e
                logger.warning(
                    f"GDELT download failed (attempt {attempt + 1}/{self.max_retries}) for {archive_url}: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2.0

        raise RuntimeError(f"Failed to download GDELT archive {archive_url}: {last_exc}")

    def parse_gkg_archive_content(
        self,
        archive_bytes: bytes,
        archive_filename: str,
        collected_at: Optional[datetime] = None,
        target_assets: Optional[List[str]] = None,
    ) -> List[Tuple[NewsArticle, NewsArticleVersion]]:
        """
        Decompress GKG CSV zip archive in memory and extract records matching target crypto assets.
        """
        if collected_at is None:
            collected_at = datetime.now(timezone.utc)
        if target_assets is None:
            target_assets = ["BTC", "ETH", "BNB"]

        results: List[Tuple[NewsArticle, NewsArticleVersion]] = []

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
            namelist = zf.namelist()
            if not namelist:
                return []
            internal_csv_name = namelist[0]

            with zf.open(internal_csv_name) as f:
                for line_idx, raw_line in enumerate(f):
                    try:
                        line = raw_line.decode("utf-8", errors="replace")
                        cols = line.split("\t")
                        if len(cols) < 5:
                            continue

                        gkg_id = cols[0].strip()
                        date_str = cols[1].strip()
                        domain = cols[3].strip()
                        url = cols[4].strip()

                        # Extract title from Col 26 (Extras XML) if present
                        title = None
                        if len(cols) > 26 and cols[26]:
                            m = PAGE_TITLE_REGEX.search(cols[26])
                            if m:
                                title = m.group(1).strip()

                        # Fallback title from URL slug if XML title is absent
                        if not title:
                            slug = url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ")
                            if slug and len(slug) > 10:
                                title = slug.title()
                            else:
                                title = f"News report from {domain}"

                        # Detect cryptocurrency mentions
                        # Scan title, themes (col 7/8), organizations (col 13/14), and URL
                        scan_text = f"{title} {url} "
                        if len(cols) > 7:
                            scan_text += f"{cols[7]} "
                        if len(cols) > 13:
                            scan_text += f"{cols[13]} "

                        matched_entities = []
                        for asset, pattern in CRYPTO_PATTERNS.items():
                            if asset in target_assets and pattern.search(scan_text):
                                matched_entities.append(asset)

                        # Skip records that do not mention any target assets
                        if not matched_entities:
                            continue

                        # Compute line hash
                        line_hash = hashlib.sha256(raw_line).hexdigest()

                        # Temporal resolution
                        temporal = resolve_temporal_coordinates(
                            source="gdelt_gkg",
                            gdelt_date_str=date_str,
                            collected_at=collected_at,
                            latency_buffer_seconds=300,
                        )

                        article_id = "art_gdelt_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
                        canonical = canonicalize_url(url)
                        norm_title = normalize_title(title)
                        now_iso = to_iso_utc(collected_at)

                        article = NewsArticle(
                            article_id=article_id,
                            source=NewsSourceType.GDELT_GKG,
                            source_record_id=gkg_id,
                            url=url,
                            canonical_url=canonical,
                            domain=domain,
                            title=title,
                            normalized_title=norm_title,
                            language="en",
                            entities=matched_entities,
                            source_verification_status=temporal["source_verification_status"],
                            raw_payload_sha256=line_hash,
                            created_at=now_iso,
                        )

                        version_id = f"ver_{article_id}_1_{line_hash[:8]}"
                        version = NewsArticleVersion(
                            version_id=version_id,
                            article_id=article_id,
                            version_number=1,
                            title=title,
                            body_text=None,
                            category=archive_filename,
                            pairs=matched_entities,
                            raw_payload=line[:1000],  # Bounded preview of raw GKG row
                            raw_payload_sha256=line_hash,
                            published_at=temporal["published_at"],
                            updated_at=temporal["updated_at"],
                            provider_seen_at=temporal["provider_seen_at"],
                            first_seen_at=temporal["first_seen_at"],
                            collected_at=temporal["collected_at"],
                            available_at=temporal["available_at"],
                            timestamp_precision=temporal["timestamp_precision"],
                            created_at=now_iso,
                        )

                        results.append((article, version))

                    except Exception as e:
                        logger.debug(f"Error parsing GKG line {line_idx}: {e}")
                        continue

        return results
