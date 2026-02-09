"""
Celery tasks for background job processing.
"""
from app.celery_app import celery_app
from app.database.database import SessionLocal
from app.services.scraper import NewsScraper
import logging
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.scheduled_scraping_task", bind=True, max_retries=3)
def scheduled_scraping_task(self):
    """
    Scheduled task to scrape news articles from all newspapers.
    Runs daily at configured time (default: 6:00 AM BDT).
    """
    db = SessionLocal()
    task_id = self.request.id
    start_time = datetime.now()
    
    logger.info(f"Starting scheduled scraping task [{task_id}] at {start_time}")
    
    try:
        # Initialize scraper
        scraper = NewsScraper()
        
        # Get today's date for scraping
        today = date.today()
        
        # Scrape from all newspapers
        newspapers = ["prothom_alo", "jugantor", "daily_star", "dhaka_tribune", "samakal"]
        total_articles = 0
        
        import asyncio
        for newspaper in newspapers:
            try:
                articles = asyncio.run(scraper.scrape_articles(newspaper, today, today))
                total_articles += len(articles)
                logger.info(f"Scraped {len(articles)} articles from {newspaper}")
            except Exception as e:
                logger.error(f"Failed to scrape {newspaper}: {str(e)}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"Scheduled scraping task [{task_id}] completed successfully. "
            f"Duration: {duration:.2f}s, Articles scraped: {total_articles}"
        )
        
        return {
            "status": "success",
            "task_id": task_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "articles_scraped": total_articles,
            "result": {"total_articles": total_articles}
        }
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.error(
            f"Scheduled scraping task [{task_id}] failed after {duration:.2f}s: {str(e)}",
            exc_info=True
        )
        
        # Retry the task with exponential backoff
        try:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for task [{task_id}]")
            return {
                "status": "failed",
                "task_id": task_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e)
            }
            
    finally:
        db.close()


@celery_app.task(name="app.tasks.manual_scraping_task", bind=True)
def manual_scraping_task(self, newspaper_names: list[str] = None):
    """
    Manual task to scrape specific newspapers on demand.
    
    Args:
        newspaper_names: List of newspaper names to scrape. If None, scrapes all.
    """
    db = SessionLocal()
    task_id = self.request.id
    start_time = datetime.now()
    
    logger.info(f"Starting manual scraping task [{task_id}] for newspapers: {newspaper_names}")
    
    try:
        # Initialize scraper
        scraper = NewsScraper()
        today = date.today()
        total_articles = 0
        
        import asyncio
        if newspaper_names:
            # Scrape specific newspapers
            for newspaper in newspaper_names:
                try:
                    articles = asyncio.run(scraper.scrape_articles(newspaper, today, today))
                    total_articles += len(articles)
                    logger.info(f"Scraped {len(articles)} articles from {newspaper}")
                except Exception as e:
                    logger.error(f"Failed to scrape {newspaper}: {str(e)}")
        else:
            # Scrape all newspapers
            newspapers = ["prothom_alo", "jugantor", "daily_star", "dhaka_tribune", "samakal"]
            for newspaper in newspapers:
                try:
                    articles = asyncio.run(scraper.scrape_articles(newspaper, today, today))
                    total_articles += len(articles)
                    logger.info(f"Scraped {len(articles)} articles from {newspaper}")
                except Exception as e:
                    logger.error(f"Failed to scrape {newspaper}: {str(e)}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            f"Manual scraping task [{task_id}] completed successfully. "
            f"Duration: {duration:.2f}s, Articles scraped: {total_articles}"
        )
        
        return {
            "status": "success",
            "task_id": task_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "articles_scraped": total_articles,
            "result": {"total_articles": total_articles}
        }
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.error(
            f"Manual scraping task [{task_id}] failed after {duration:.2f}s: {str(e)}",
            exc_info=True
        )
        
        return {
            "status": "failed",
            "task_id": task_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "error": str(e)
        }
        
    finally:
        db.close()
