"""
APScheduler service for automated daily scraping and processing.
Single scheduler implementation — no Redis/Celery dependency.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import SchedulerLog
from app.services.enhanced_scraper import EnhancedNewsScraper
from app.services.article_processor import ArticleProcessor
from app.config.newspapers import get_enabled_newspapers
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Background scheduler for automated scraping and processing.
    Uses APScheduler with AsyncIOScheduler — runs in-process with the FastAPI server.
    Supports dynamic schedule updates, pause/resume, and status queries.
    """

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
        self._schedule_hour: int = settings.scheduler_hour
        self._schedule_minute: int = settings.scheduler_minute
        self._last_run: Optional[Dict[str, Any]] = None

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(self):
        """Start the scheduler with the configured daily cron job."""
        if self._is_running:
            logger.warning("Scheduler already running")
            return

        self._add_daily_job()
        self.scheduler.start()
        self._is_running = True
        logger.debug(
            f"Scheduler started — daily scraping at "
            f"{self._schedule_hour:02d}:{self._schedule_minute:02d} BDT"
        )

    def stop(self):
        """Stop the scheduler gracefully."""
        if not self._is_running:
            return
        self.scheduler.shutdown(wait=False)
        self._is_running = False
        logger.info("Scheduler stopped")

    # ── Dynamic schedule management ──────────────────────────────────

    def update_schedule(self, hour: int, minute: int) -> bool:
        """
        Update the daily scraping schedule.

        Args:
            hour:   0-23 in BDT
            minute: 0-59

        Returns:
            True on success, False on validation error.
        """
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            logger.error(f"Invalid schedule time: {hour}:{minute}")
            return False

        self._schedule_hour = hour
        self._schedule_minute = minute

        # Re-add the job with the new trigger (replace_existing handles dedup)
        if self._is_running:
            self._add_daily_job()

        logger.info(
            f"Scheduler updated to run daily at {hour:02d}:{minute:02d} BDT"
        )
        return True

    def toggle(self) -> bool:
        """
        Toggle scheduler on/off (pause/resume).

        Returns:
            The new running state (True = running, False = paused).
        """
        if self._is_running:
            self.scheduler.pause()
            self._is_running = False
            logger.info("Scheduler paused")
            return False
        else:
            self.scheduler.resume()
            self._is_running = True
            logger.info("Scheduler resumed")
            return True

    # ── Status / introspection ───────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._is_running

    def get_status(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Comprehensive scheduler status for the API.

        Returns dict with running, schedule, next_run, last_run.
        """
        # Next run from APScheduler
        next_run = self._get_next_run_time()

        # Last run — prefer DB log, fall back to in-memory
        last_run = None
        if db is not None:
            last_run = self.get_last_run_info(db)
        if last_run is None:
            last_run = self._last_run

        return {
            "running": self._is_running,
            "schedule": f"Daily at {self._schedule_hour:02d}:{self._schedule_minute:02d} BDT",
            "next_run": next_run.isoformat() if next_run else None,
            "last_run": last_run,
        }

    def get_last_run_info(self, db: Session) -> Optional[Dict[str, Any]]:
        """Get information about the last scheduler run from the database."""
        last_log = (
            db.query(SchedulerLog)
            .order_by(SchedulerLog.started_at.desc())
            .first()
        )
        if not last_log:
            return None
        return {
            "job_name": last_log.job_name,
            "status": last_log.status,
            "started_at": last_log.started_at.isoformat() if last_log.started_at else None,
            "completed_at": last_log.completed_at.isoformat() if last_log.completed_at else None,
            "articles_scraped": last_log.articles_scraped,
            "articles_processed": last_log.articles_processed,
            "errors": last_log.errors,
            "error_message": last_log.error_message,
        }

    # ── Test helpers ─────────────────────────────────────────────────

   # ── Internal helpers ─────────────────────────────────────────────

    def _add_daily_job(self):
        """Add (or replace) the daily cron job using current schedule."""
        # BDT = UTC+6, so convert BDT hour to UTC
        utc_hour = (self._schedule_hour - 6) % 24
        self.scheduler.add_job(
            self.daily_scrape_and_process,
            CronTrigger(hour=utc_hour, minute=self._schedule_minute),
            id="daily_scraping",
            name="Daily Newspaper Scraping",
            replace_existing=True,
        )

    def _get_next_run_time(self) -> Optional[datetime]:
        """Return the next scheduled fire time for the daily job."""
        job = self.scheduler.get_job("daily_scraping")
        if job and job.next_run_time:
            return job.next_run_time
        return None
    
    async def daily_scrape_and_process(self):
        """
        Daily job: Scrape all enabled newspapers and process articles.
        Runs automatically at 6 AM BDT every day.
        """
        job_name = "daily_scraping"
        started_at = datetime.utcnow()
        
        logger.info("=" * 80)
        logger.info(f"Starting daily scraping job at {started_at}")
        logger.info("=" * 80)
        
        db = SessionLocal()
        log = SchedulerLog(
            job_name=job_name,
            status="running",
            started_at=started_at
        )
        db.add(log)
        db.commit()
        
        total_scraped = 0
        total_processed = 0
        errors = []
        
        try:
            # Get enabled newspapers
            newspapers = get_enabled_newspapers()
            logger.info(f"Scraping {len(newspapers)} newspapers: {[n.name for n in newspapers]}")
            
            # Today's date for scraping
            today = datetime.now().date()
            
            # Scrape each newspaper
            scraper = EnhancedNewsScraper(db)
            
            for newspaper in newspapers:
                try:
                    logger.info(f"Scraping {newspaper.name} ({newspaper.key})...")
                    
                    stats = await scraper.scrape_and_store(
                        source=newspaper.key,
                        start_date=today,
                        end_date=today
                    )
                    
                    total_scraped += stats["new_articles"]
                    
                    if stats["errors"]:
                        errors.extend(stats["errors"])
                    
                    logger.info(
                        f"{newspaper.name}: {stats['new_articles']} new articles, "
                        f"{stats['duplicates']} duplicates"
                    )
                
                except Exception as e:
                    error_msg = f"Failed to scrape {newspaper.name}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Note: Automatic processing disabled - articles will be processed manually
            logger.info("Scraping complete. Articles saved to database for manual processing.")
            total_processed = 0
            
            # Run article clustering on newly scraped articles
            try:
                from app.services.clustering_service import ClusteringService
                logger.info("Running article clustering on recent articles...")
                clustering_service = ClusteringService(db)
                cluster_stats = clustering_service.cluster_articles(days_back=1)
                logger.info(f"Clustering results: {cluster_stats}")
            except Exception as ce:
                cluster_error = f"Clustering failed: {str(ce)}"
                logger.error(cluster_error)
                errors.append(cluster_error)
            
            # Update log
            final_status = "success" if not errors else "partial"
            log.status = final_status
            log.completed_at = datetime.utcnow()
            log.articles_scraped = total_scraped
            log.articles_processed = total_processed
            log.errors = errors if errors else None
            db.commit()

            # Track in memory for instant status queries
            self._last_run = {
                "timestamp": datetime.now().isoformat(),
                "status": final_status,
                "articles_count": total_scraped,
                "error": None,
            }
            
            logger.info("=" * 80)
            logger.info(
                f"Daily scraping job completed: "
                f"{total_scraped} scraped, {total_processed} processed"
            )
            logger.info("=" * 80)
        
        except Exception as e:
            error_msg = f"Daily scraping job failed: {str(e)}"
            logger.error(error_msg)
            
            log.status = "failed"
            log.completed_at = datetime.utcnow()
            log.error_message = error_msg
            log.articles_scraped = total_scraped
            log.articles_processed = total_processed
            db.commit()

            self._last_run = {
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "articles_count": total_scraped,
                "error": error_msg,
            }
        
        finally:
            db.close()
    
    async def run_manual_scraping(
        self,
        sources: Optional[list] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        section_ids: Optional[dict] = None
    ) -> dict:
        """
        Manually trigger scraping for specific sources and date range.
        Used for historical data collection.
        
        Args:
            sources: List of newspaper keys (None = all enabled)
            start_date: Start date (None = today)
            end_date: End date (None = today)
            section_ids: Optional dict mapping source to list of section IDs
        
        Returns:
            Scraping and processing statistics
        """
        # Use today if dates not provided
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = datetime.now()
        
        logger.info(
            f"Manual scraping triggered: "
            f"sources={sources}, dates={start_date.date()} to {end_date.date()}, "
            f"section_ids={section_ids}"
        )
        
        db = SessionLocal()
        
        try:
            # Determine newspapers to scrape
            if sources:
                from app.config.newspapers import get_newspaper_config
                newspapers = []
                for s in sources:
                    try:
                        config = get_newspaper_config(s)
                        newspapers.append(config)
                    except Exception as e:
                        logger.error(f"Invalid source {s}: {str(e)}")
            else:
                newspapers = get_enabled_newspapers()
            
            if not newspapers:
                logger.error("No valid newspapers to scrape")
                return {
                    "total_scraped": 0,
                    "total_processed": 0,
                    "by_source": {},
                    "errors": ["No valid newspapers selected"]
                }
            
            logger.info(f"Will scrape {len(newspapers)} newspaper(s): {[n.key for n in newspapers]}")
            scraper = EnhancedNewsScraper(db)
            total_stats = {
                "total_scraped": 0,
                "total_processed": 0,
                "by_source": {},
                "errors": []
            }
            
            # Scrape each newspaper
            for newspaper in newspapers:
                try:
                    logger.info(f"Starting scraping for {newspaper.name} ({newspaper.key})...")
                    
                    # Get section_ids for this source if provided
                    source_section_ids = None
                    if section_ids and newspaper.key in section_ids:
                        source_section_ids = section_ids[newspaper.key]
                        logger.info(f"Using {len(source_section_ids)} section groups for {newspaper.key}")
                    
                    stats = await scraper.scrape_and_store(
                        source=newspaper.key,
                        start_date=start_date.date(),
                        end_date=end_date.date(),
                        section_ids=source_section_ids
                    )
                    
                    total_stats["total_scraped"] += stats["new_articles"]
                    total_stats["by_source"][newspaper.key] = stats
                    
                    if stats["errors"]:
                        total_stats["errors"].extend(stats["errors"])
                    
                    logger.info(f"Completed {newspaper.name}: {stats['new_articles']} new articles")
                
                except Exception as e:
                    error_msg = f"Failed to scrape {newspaper.name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    total_stats["errors"].append(error_msg)
            
            # Note: Automatic processing disabled - articles will be processed manually
            logger.info("Manual scraping complete. Articles saved to database for manual bias analysis.")
            total_stats["total_processed"] = 0
            total_stats["processing"] = {"successful": 0, "total_processed": 0, "message": "Automatic processing disabled"}
            
            # Run clustering on recently scraped articles
            try:
                from app.services.clustering_service import ClusteringService
                logger.info("Running article clustering after manual scraping...")
                clustering_service = ClusteringService(db)
                cluster_stats = clustering_service.cluster_articles(days_back=3)
                total_stats["clustering"] = cluster_stats
                logger.info(f"Clustering results: {cluster_stats}")
            except Exception as ce:
                logger.error(f"Post-scrape clustering failed: {str(ce)}")
                total_stats["clustering"] = {"status": "failed", "error": str(ce)}
            
            return total_stats
        
        finally:
            db.close()


# Global scheduler instance
scheduler_service: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get or create global scheduler instance."""
    global scheduler_service
    if scheduler_service is None:
        scheduler_service = SchedulerService()
    return scheduler_service
