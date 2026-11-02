"""
NEPTUNE News Ingestion & Management Service (`service.py`)

Central orchestrator for historical news acquisition, revision tracking,
deterministic event classification, multi-stage event clustering, Parquet export,
and data-quality reporting.
Governed by: Rule S-05, Rule S-08, ADR-001, ADR-023, ADR-024.
"""
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config.settings import get_settings
from app.data.news.binance_client import BinanceNewsClient
from app.data.news.classifier import DeterministicNewsClassifier
from app.data.news.deduplication import NewsEventClusterer
from app.data.news.gdelt_client import GdeltGkgClient
from app.data.news.macro_calendar import HistoricalMacroCalendarRegistry
from app.data.news.models import NewsIngestionRun, NewsSourceType
from app.data.news.parquet_exporter import NewsParquetExporter
from app.data.news.quality_reporter import NewsQualityReporter
from app.data.news.temporal import to_iso_utc
from app.data.repositories.news_repo import SqliteNewsRepository

logger = logging.getLogger(__name__)


class NewsDataService:
    """Service orchestrating news ingestion, classification, deduplication, and persistence."""

    def __init__(
        self,
        repo: Optional[SqliteNewsRepository] = None,
        db_path: Optional[str] = None,
        storage_root: str = "storage/news",
    ):
        if repo:
            self.repo = repo
        else:
            self.repo = SqliteNewsRepository(db_path=db_path)
        self.db_path = self.repo.db_path
        self.storage_root = storage_root
        self.binance_client = BinanceNewsClient()
        self.gdelt_client = GdeltGkgClient()
        self.classifier = DeterministicNewsClassifier()
        self.clusterer = NewsEventClusterer()
        self.parquet_exporter = NewsParquetExporter(
            db_path=self.db_path, storage_root=self.storage_root
        )
        self.quality_reporter = NewsQualityReporter(db_path=self.db_path)

    async def ingest_binance_announcements(
        self,
        catalog_id: Optional[int] = 48,
        start_page: int = 1,
        max_pages: int = 5,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Bounded, resumable ingestion of Binance official announcements.
        Fetches summaries, retrieves full detail payloads, detects version bumps,
        classifies events & relevance, and saves immutable article identities and version records.
        """
        run_id = f"run_binance_cat{catalog_id}_{uuid.uuid4().hex[:8]}"
        now_dt = datetime.now(timezone.utc)
        now_iso = to_iso_utc(now_dt)

        run = NewsIngestionRun(
            run_id=run_id,
            source=NewsSourceType.BINANCE_ANNOUNCEMENTS,
            target_asset=f"CAT_{catalog_id}",
            status="RUNNING",
            started_at=now_iso,
        )
        await self.repo.record_ingestion_run(run.to_dict())

        total_processed = 0
        new_articles_count = 0
        version_bumps_count = 0
        failed_count = 0
        failed_codes = []

        try:
            for page in range(start_page, start_page + max_pages):
                logger.info(f"Fetching Binance catalog {catalog_id} page {page}...")
                catalog_data = await self.binance_client.fetch_catalog_page(
                    catalog_id=catalog_id, page_no=page, page_size=page_size
                )
                articles_list = catalog_data.get("articles") or []
                if not articles_list:
                    logger.info(f"No more articles found in catalog {catalog_id} at page {page}.")
                    break

                for item in articles_list:
                    code = str(item.get("code") or item.get("id"))
                    try:
                        # Fetch full detail
                        detail = await self.binance_client.fetch_article_detail(code)
                        article, version = self.binance_client.parse_article_data(
                            detail, collected_at=now_dt
                        )

                        # Classify article
                        cls_result = self.classifier.classify_article(
                            title=article.title,
                            body_text=version.body_text,
                            source=article.source.value,
                            pairs=version.pairs,
                        )
                        article.event_category = cls_result["event_category"]
                        article.relevance_classification = cls_result["relevance_classification"]
                        article.affected_assets = cls_result["affected_assets"]
                        article.classification_evidence = cls_result["classification_evidence"]
                        article.classifier_version = cls_result["classifier_version"]
                        article.confidence_score = cls_result["confidence_score"]
                        article.classified_at = cls_result["classified_at"]

                        # Check existing article
                        existing_art = await self.repo.find_article_by_source_record(
                            source="binance_announcements", source_record_id=code
                        )
                        if not existing_art:
                            await self.repo.save_article(article.to_dict())
                            new_articles_count += 1
                        else:
                            await self.repo.save_article(article.to_dict())

                        # Check existing version
                        latest_ver = await self.repo.get_latest_article_version(article.article_id)
                        if latest_ver is None:
                            await self.repo.save_article_version(version.to_dict())
                        elif latest_ver["raw_payload_sha256"] != version.raw_payload_sha256:
                            # Version incremented: immutable append
                            new_ver_num = latest_ver["version_number"] + 1
                            version.version_number = new_ver_num
                            version.version_id = f"ver_{article.article_id}_{new_ver_num}_{version.raw_payload_sha256[:8]}"
                            await self.repo.save_article_version(version.to_dict())
                            version_bumps_count += 1

                        total_processed += 1

                    except Exception as e:
                        failed_count += 1
                        failed_codes.append({"code": code, "error": str(e)})
                        logger.warning(f"Failed to process Binance article code {code}: {e}")

                # Update run checkpoint
                checkpoint = {
                    "last_completed_page": page,
                    "total_processed": total_processed,
                    "failed_codes": failed_codes,
                }
                await self.repo.record_ingestion_run(
                    {
                        "run_id": run_id,
                        "source": NewsSourceType.BINANCE_ANNOUNCEMENTS.value,
                        "status": "RUNNING",
                        "records_ingested": total_processed,
                        "unique_articles": new_articles_count,
                        "failed_records": failed_count,
                        "cursor_state_json": json.dumps(checkpoint),
                        "started_at": now_iso,
                    }
                )

            # Mark run completed
            completed_iso = to_iso_utc(datetime.now(timezone.utc))
            await self.repo.record_ingestion_run(
                {
                    "run_id": run_id,
                    "source": NewsSourceType.BINANCE_ANNOUNCEMENTS.value,
                    "status": "COMPLETED",
                    "records_ingested": total_processed,
                    "unique_articles": new_articles_count,
                    "failed_records": failed_count,
                    "cursor_state_json": json.dumps(
                        {"last_page": start_page + max_pages - 1, "failed_codes": failed_codes}
                    ),
                    "started_at": now_iso,
                    "completed_at": completed_iso,
                }
            )

        except Exception as e:
            failed_iso = to_iso_utc(datetime.now(timezone.utc))
            await self.repo.record_ingestion_run(
                {
                    "run_id": run_id,
                    "source": NewsSourceType.BINANCE_ANNOUNCEMENTS.value,
                    "status": "FAILED",
                    "records_ingested": total_processed,
                    "unique_articles": new_articles_count,
                    "failed_records": failed_count,
                    "started_at": now_iso,
                    "completed_at": failed_iso,
                    "error_message": str(e),
                }
            )
            raise

        return {
            "run_id": run_id,
            "catalog_id": catalog_id,
            "status": "COMPLETED",
            "records_processed": total_processed,
            "new_articles": new_articles_count,
            "version_bumps": version_bumps_count,
            "failed_count": failed_count,
            "failed_codes": failed_codes,
        }

    async def ingest_gdelt_archive(
        self,
        archive_url: str,
        expected_md5: Optional[str] = None,
        target_assets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Download and ingest a single 15-minute GDELT GKG archive in memory.
        Filters for target crypto assets, classifies events & relevance, and records PARTIALLY_VERIFIED articles.
        """
        run_id = f"run_gdelt_{uuid.uuid4().hex[:12]}"
        now_dt = datetime.now(timezone.utc)
        now_iso = to_iso_utc(now_dt)
        archive_filename = archive_url.split("/")[-1]

        run = NewsIngestionRun(
            run_id=run_id,
            source=NewsSourceType.GDELT_GKG,
            target_asset=",".join(target_assets or ["BTC", "ETH", "BNB"]),
            status="RUNNING",
            started_at=now_iso,
        )
        await self.repo.record_ingestion_run(run.to_dict())

        try:
            # Download archive with optional MD5 verification
            archive_bytes = await self.gdelt_client.download_archive(
                archive_url=archive_url, expected_md5=expected_md5
            )

            # Parse crypto items
            records = self.gdelt_client.parse_gkg_archive_content(
                archive_bytes=archive_bytes,
                archive_filename=archive_filename,
                collected_at=now_dt,
                target_assets=target_assets,
            )

            articles_saved = 0
            for article, version in records:
                # Classify article
                cls_result = self.classifier.classify_article(
                    title=article.title,
                    body_text=version.body_text,
                    source=article.source.value,
                    pairs=version.pairs,
                )
                article.event_category = cls_result["event_category"]
                article.relevance_classification = cls_result["relevance_classification"]
                article.affected_assets = cls_result["affected_assets"]
                article.classification_evidence = cls_result["classification_evidence"]
                article.classifier_version = cls_result["classifier_version"]
                article.confidence_score = cls_result["confidence_score"]
                article.classified_at = cls_result["classified_at"]

                existing = await self.repo.find_article_by_url(article.url)
                if not existing:
                    await self.repo.save_article(article.to_dict())
                    await self.repo.save_article_version(version.to_dict())
                    articles_saved += 1
                else:
                    await self.repo.save_article(article.to_dict())
                    latest_ver = await self.repo.get_latest_article_version(article.article_id)
                    if not latest_ver:
                        await self.repo.save_article_version(version.to_dict())

            completed_iso = to_iso_utc(datetime.now(timezone.utc))
            await self.repo.record_ingestion_run(
                {
                    "run_id": run_id,
                    "source": NewsSourceType.GDELT_GKG.value,
                    "status": "COMPLETED",
                    "records_ingested": len(records),
                    "unique_articles": articles_saved,
                    "failed_records": 0,
                    "started_at": now_iso,
                    "completed_at": completed_iso,
                }
            )

            return {
                "run_id": run_id,
                "archive_filename": archive_filename,
                "crypto_matches_found": len(records),
                "articles_saved": articles_saved,
                "status": "COMPLETED",
            }

        except Exception as e:
            failed_iso = to_iso_utc(datetime.now(timezone.utc))
            await self.repo.record_ingestion_run(
                {
                    "run_id": run_id,
                    "source": NewsSourceType.GDELT_GKG.value,
                    "status": "FAILED",
                    "records_ingested": 0,
                    "unique_articles": 0,
                    "failed_records": 1,
                    "started_at": now_iso,
                    "completed_at": failed_iso,
                    "error_message": str(e),
                }
            )
            raise

    async def ingest_macro_calendar_events(self) -> Dict[str, Any]:
        """
        Source C: Ingest canonical historical macroeconomic and protocol milestones.
        All records are verified with official public URLs and exact release timestamps.
        """
        events = HistoricalMacroCalendarRegistry.get_canonical_events()
        saved_count = 0
        for ev in events:
            await self.repo.save_macro_event(ev.to_dict())
            saved_count += 1

        return {
            "source": "macro_calendar",
            "events_saved": saved_count,
            "status": "COMPLETED",
        }

    async def classify_all_articles(self) -> Dict[str, Any]:
        """
        Run the deterministic classifier on all articles currently in SQLite,
        updating their categories, relevance labels, and affected assets.
        """
        articles = await self.repo.list_all_articles(limit=50000)
        updated_count = 0

        for art in articles:
            latest_ver = await self.repo.get_latest_article_version(art["article_id"])
            body_text = latest_ver.get("body_text") if latest_ver else None
            pairs = latest_ver.get("pairs") if latest_ver else []

            cls_res = self.classifier.classify_article(
                title=art["title"],
                body_text=body_text,
                source=art["source"],
                pairs=pairs,
            )
            await self.repo.update_article_classification(art["article_id"], cls_res)
            updated_count += 1

        return {
            "articles_classified": updated_count,
            "classifier_version": self.classifier.VERSION,
            "status": "COMPLETED",
        }

    async def cluster_all_articles(self) -> Dict[str, Any]:
        """
        Execute multi-stage event clustering over all stored articles and persist clusters.
        """
        with self.repo._get_connection() as conn:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT a.article_id, a.url, a.canonical_url, a.domain, a.title,
                       a.normalized_title, a.entities_json, a.source, a.source_verification_status,
                       a.event_category, a.relevance_classification,
                       v.available_at, v.published_at, v.provider_seen_at, v.created_at
                FROM news_articles a
                LEFT JOIN news_article_versions v ON a.article_id = v.article_id AND v.version_number = 1
                """
            ).fetchall()

        articles = []
        for r in rows:
            d = dict(r)
            d["entities"] = json.loads(d.get("entities_json") or "[]")
            articles.append(d)

        # Cluster articles
        clusters = self.clusterer.cluster_articles(articles)

        # Save clusters and member mappings
        saved_count = 0
        for cl in clusters:
            members = cl.pop("members", [])
            await self.repo.save_event_cluster(cl, member_article_ids=members)
            saved_count += 1

        return {
            "total_articles_evaluated": len(articles),
            "clusters_generated": saved_count,
            "clustering_algorithm": "simhash_v1_entity_matched",
        }

    def export_to_parquet(self) -> Dict[str, Any]:
        """Export all news tables to Parquet partitions."""
        return self.parquet_exporter.export_all()

    def generate_data_quality_report(self) -> Dict[str, Any]:
        """Produce the comprehensive data quality audit report."""
        return self.quality_reporter.generate_report()
