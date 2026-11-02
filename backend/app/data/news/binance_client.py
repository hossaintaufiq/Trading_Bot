"""
NEPTUNE Binance Official Announcements Client (`binance_client.py`)

Ingests official Binance announcements via public CMS endpoints:
- Catalog list query: /bapi/composite/v1/public/cms/article/catalog/list/query
- Detail query: /bapi/composite/v1/public/cms/article/detail/query?articleCode={code}

Features:
- Immutable article identity and revision tracking (Rule S-05, ADR-023).
- Exact SHA-256 raw response payload fingerprinting.
- Exponential backoff retry logic for transient errors.
- Bounded and resumable pagination.
- Zero credential requirements (Public REST).
"""
import asyncio
import hashlib
import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.data.news.deduplication import canonicalize_url, normalize_title
from app.data.news.models import NewsArticle, NewsArticleVersion, NewsSourceType, SourceVerificationStatus, TimestampPrecision
from app.data.news.temporal import resolve_temporal_coordinates, to_iso_utc

logger = logging.getLogger(__name__)


class BinanceNewsClient:
    """Public REST client for Binance Announcements."""

    BASE_URL = "https://www.binance.com/bapi/composite/v1/public/cms"

    def __init__(self, timeout: float = 15.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def _http_get_json(self, url: str) -> Dict[str, Any]:
        """Execute HTTP GET with bounded exponential backoff."""
        delay = 1.0
        last_exc = None

        for attempt in range(self.max_retries):
            try:
                loop = asyncio.get_running_loop()
                req = urllib.request.Request(url, headers=self.headers)
                
                def _do_fetch():
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        return resp.read()

                body_bytes = await loop.run_in_executor(None, _do_fetch)
                data = json.loads(body_bytes.decode("utf-8"))
                return data
            except Exception as e:
                last_exc = e
                logger.warning(
                    f"Binance CMS request failed (attempt {attempt + 1}/{self.max_retries}) for {url}: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2.0

        raise RuntimeError(f"HTTP GET failed after {self.max_retries} retries: {last_exc}")

    async def fetch_catalog_page(
        self, catalog_id: Optional[int] = 48, page_no: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Fetch a page of announcement summaries.
        Catalog 48 is 'New Cryptocurrency Listing', 49 is 'Latest Binance News'.
        """
        params = {"pageNo": page_no, "pageSize": page_size}
        if catalog_id is not None:
            params["catalogId"] = catalog_id

        url = f"{self.BASE_URL}/article/catalog/list/query?{urllib.parse.urlencode(params)}"
        data = await self._http_get_json(url)

        if data.get("code") != "000000":
            raise RuntimeError(f"Binance CMS catalog error: {data.get('message', 'Unknown error')}")

        return data.get("data", {})

    async def fetch_article_detail(self, article_code: str) -> Dict[str, Any]:
        """
        Fetch full announcement detail including millisecond timestamps, version, and text.
        """
        params = {"articleCode": article_code}
        url = f"{self.BASE_URL}/article/detail/query?{urllib.parse.urlencode(params)}"
        data = await self._http_get_json(url)

        if data.get("code") != "000000":
            raise RuntimeError(
                f"Binance CMS detail error for {article_code}: {data.get('message', 'Unknown error')}"
            )

        return data.get("data", {})

    def parse_article_data(
        self, detail_payload: Dict[str, Any], collected_at: Optional[datetime] = None
    ) -> Tuple[NewsArticle, NewsArticleVersion]:
        """
        Transform raw Binance detail payload into immutable NewsArticle and NewsArticleVersion records.
        """
        if collected_at is None:
            collected_at = datetime.now(timezone.utc)

        raw_json_str = json.dumps(detail_payload, sort_keys=True, ensure_ascii=False)
        payload_sha256 = hashlib.sha256(raw_json_str.encode("utf-8")).hexdigest()

        code = str(detail_payload.get("code") or detail_payload.get("id"))
        title = detail_payload.get("title") or "Untitled Announcement"
        url = f"https://www.binance.com/en/support/announcement/{code}"
        canonical = canonicalize_url(url)
        norm_title = normalize_title(title)

        # Extract trading pairs / crypto symbols
        pairs = detail_payload.get("pairs") or []
        extracted_entities = []
        clean_pairs = []
        for p in pairs:
            if isinstance(p, dict):
                asset = p.get("asset") or p.get("baseAsset")
                quote = p.get("quoteAsset")
                if asset:
                    extracted_entities.append(str(asset).upper())
                if quote:
                    extracted_entities.append(str(quote).upper())
                if asset and quote:
                    clean_pairs.append(f"{asset}{quote}".upper())
                elif asset:
                    clean_pairs.append(str(asset).upper())
            elif isinstance(p, str):
                extracted_entities.append(p.upper())
                clean_pairs.append(p.upper())

        # Check for BTC, ETH, BNB mentions in title if pairs empty
        title_upper = title.upper()
        for sym in ["BTC", "ETH", "BNB"]:
            if sym not in extracted_entities:
                if sym in title_upper or (sym == "BTC" and "BITCOIN" in title_upper) or (sym == "ETH" and "ETHEREUM" in title_upper):
                    extracted_entities.append(sym)

        # Resolve temporal coordinates
        pub_ms = detail_payload.get("publishDate")
        upd_ms = detail_payload.get("lastUpdateTime")
        temporal = resolve_temporal_coordinates(
            source="binance_announcements",
            raw_pub_ms=pub_ms,
            raw_update_ms=upd_ms,
            collected_at=collected_at,
        )

        now_iso = to_iso_utc(collected_at)
        article_id = "art_binance_" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

        article = NewsArticle(
            article_id=article_id,
            source=NewsSourceType.BINANCE_ANNOUNCEMENTS,
            source_record_id=code,
            url=url,
            canonical_url=canonical,
            domain="binance.com",
            title=title,
            normalized_title=norm_title,
            language="en",
            entities=extracted_entities,
            source_verification_status=temporal["source_verification_status"],
            raw_payload_sha256=payload_sha256,
            created_at=now_iso,
        )

        version_num = int(detail_payload.get("version") or 1)
        version_id = f"ver_{article_id}_{version_num}_{payload_sha256[:8]}"

        body_text = detail_payload.get("body")
        category = detail_payload.get("firstCatalogName") or detail_payload.get("catalogName")

        version = NewsArticleVersion(
            version_id=version_id,
            article_id=article_id,
            version_number=version_num,
            title=title,
            body_text=body_text,
            category=category,
            pairs=clean_pairs,
            raw_payload=raw_json_str,
            raw_payload_sha256=payload_sha256,
            published_at=temporal["published_at"],
            updated_at=temporal["updated_at"],
            provider_seen_at=temporal["provider_seen_at"],
            first_seen_at=temporal["first_seen_at"],
            collected_at=temporal["collected_at"],
            available_at=temporal["available_at"],
            timestamp_precision=temporal["timestamp_precision"],
            created_at=now_iso,
        )

        return article, version
