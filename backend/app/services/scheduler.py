"""
APScheduler service for automated daily scraping and processing.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database.models import SchedulerLog
from app.services.enhanced_scraper import EnhancedNewsScraper
from app.services.article_processor import ArticleProcessor
from app.config.newspapers import get_enabled_newspapers

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Background scheduler for automated scraping and processing.
    """
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    def start(self):
        """Start the scheduler."""
        if self._is_running:
            logger.warning("Scheduler already running")
            return
        
        # Schedule daily scraping at 6 AM Bangladesh time (UTC+6)
        # Using UTC time: 6 AM BDT = 12 AM UTC
        self.scheduler.add_job(
            self.daily_scrape_and_process,
            CronTrigger(hour=0, minute=0),  # 12:00 AM UTC = 6:00 AM BDT
            id='daily_scraping',
            name='Daily Newspaper Scraping',
            replace_existing=True
        )
        
        logger.debug("Scheduled daily scraping at 6:00 AM BDT (00:00 UTC)")
        
        self.scheduler.start()
        self._is_running = True
        logger.debug("Scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler."""
        if not self._is_running:
            return
        
        self.scheduler.shutdown(wait=False)
        self._is_running = False
        logger.info("Scheduler stopped")
    
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
            
            # Process scraped articles
            logger.info("Processing scraped articles...")
            processor = ArticleProcessor(db)
            
            process_stats = await processor.process_unprocessed_articles(limit=50)
            total_processed = process_stats["successful"]
            
            logger.info(
                f"Processing complete: {process_stats['successful']} successful, "
                f"{process_stats['failed']} failed, "
                f"{process_stats['biased_found']} biased articles"
            )
            
            # Update log
            log.status = "success" if not errors else "partial"
            log.completed_at = datetime.utcnow()
            log.articles_scraped = total_scraped
            log.articles_processed = total_processed
            log.errors = errors if errors else None
            db.commit()
            
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
        
        finally:
            db.close()
    
    async def run_manual_scraping(
        self,
        sources: Optional[list] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """
        Manually trigger scraping for specific sources and date range.
        Used for historical data collection.
        
        Args:
            sources: List of newspaper keys (None = all enabled)
            start_date: Start date (None = today)
            end_date: End date (None = today)
        
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
            f"sources={sources}, dates={start_date.date()} to {end_date.date()}"
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
                    stats = await scraper.scrape_and_store(
                        source=newspaper.key,
                        start_date=start_date.date(),
                        end_date=end_date.date()
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
            
            # Process articles
            processor = ArticleProcessor(db)
            process_stats = await processor.process_unprocessed_articles(limit=100)
            total_stats["total_processed"] = process_stats["successful"]
            total_stats["processing"] = process_stats
            
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
