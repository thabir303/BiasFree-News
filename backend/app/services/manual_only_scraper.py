"""
Enhanced scraper service with database integration - MODIFIED for manual processing only.
Scrapes articles without automatic LLM analysis.
"""
import logging
import asyncio
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import Article
from app.config.newspapers import get_newspaper_config, get_enabled_newspapers
from app.config import settings
from app.services.scraper import ProthomAloScraper, JugantorScraper, DailyStarScraper, DhakaTribuneScraper, SamakalScraper
from app.services.optimized_scraper import OptimizedProthomAloScraper, OptimizedJugantorScraper

logger = logging.getLogger(__name__)


class ManualOnlyNewsScraper:
    """
    Scraping service that ONLY collects articles without automatic processing.
    Articles are stored for manual bias analysis later.
    """
    
    def __init__(self, db: Session):
        """Initialize scraper with database session."""
        self.db = db
    
    async def scrape_only(
        self,
        source: str,
        start_date: date,
        end_date: date,
        section_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Scrape articles and store in database WITHOUT processing.
        
        Args:
            source: Newspaper source key
            start_date: Start date for scraping
            end_date: End date for scraping
            section_ids: Optional list of section IDs (for Prothom Alo)
        
        Returns:
            Dictionary with scraping statistics
        """
        stats = {
            "source": source,
            "total_scraped": 0,
            "new_articles": 0,
            "duplicates": 0,
            "errors": [],
            "scraping_only": True  # Flag to indicate no processing
        }
        
        try:
            # Get newspaper configuration
            config = get_newspaper_config(source)
            if not config:
                raise ValueError(f"Unknown source: {source}")
            
            logger.info(f"Scraping {config.name} ({source}) from {start_date} to {end_date}")
            
            # Scrape articles using the scraper
            articles = self._scrape_source(config, start_date, end_date, section_ids)
            stats["total_scraped"] = len(articles)
            
            logger.info(f"Scraped {len(articles)} articles from {source}")
            
            # Store articles in database without processing
            for article_data in articles:
                try:
                    # Check for duplicate by URL
                    existing = self.db.query(Article).filter(
                        Article.url == article_data["url"]
                    ).first()
                    
                    if existing:
                        stats["duplicates"] += 1
                        logger.debug(f"Duplicate article skipped: {article_data['url']}")
                        continue
                    
                    # Create new article entry (unprocessed)
                    article = Article(
                        url=article_data["url"],
                        title=article_data["title"],
                        original_content=article_data["content"],
                        source=source,
                        published_date=article_data.get("published_date"),
                        author=article_data.get("author"),
                        category=article_data.get("category"),
                        scraped_at=datetime.utcnow(),
                        processed=False,  # Important: Don't process automatically
                        processing_error=None
                    )
                    
                    self.db.add(article)
                    stats["new_articles"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to store article: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            logger.info(
                f"Scraping complete for {source}: "
                f"{stats['new_articles']} new articles stored (unprocessed), "
                f"{stats['duplicates']} duplicates, "
                f"{len(stats['errors'])} errors"
            )
            
        except Exception as e:
            error_msg = f"Scraping failed for {source}: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            self.db.rollback()
        
        return stats
    
    def _scrape_source(
        self,
        config,
        start_date: date,
        end_date: date,
        section_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape articles from a specific source using scraper classes.
        
        Args:
            config: Newspaper configuration
            start_date: Start date
            end_date: End date
            section_ids: Optional section IDs for Prothom Alo
        """
        articles = []
        
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Use optimized scraper classes for better performance
            scraper_map = {
                "prothom_alo": OptimizedProthomAloScraper,
                "jugantor": OptimizedJugantorScraper,
                # Fallback to original for others (not optimized yet)
                "daily_star": DailyStarScraper,
                "dhaka_tribune": DhakaTribuneScraper,
                "samakal": SamakalScraper
            }
            
            scraper_class = scraper_map.get(config.key)
            if not scraper_class:
                logger.warning(f"No scraper implemented for: {config.key}")
                return articles
            
            # Initialize scraper with section_ids if Prothom Alo
            if config.key == "prothom_alo" and section_ids:
                logger.info(f"Initializing scraper with {len(section_ids)} section groups")
                scraper = scraper_class(start_str, end_str, section_ids)
            else:
                scraper = scraper_class(start_str, end_str)
            
            # Scrape articles
            scraped_articles = scraper.scrape_articles()
            
            # Convert ScrapedArticle objects to dictionaries
            for article in scraped_articles:
                articles.append({
                    "url": article.url,
                    "title": article.title,
                    "content": article.content,
                    "published_date": article.published_date,
                    "author": article.author,
                    "category": article.category
                })
            
            logger.info(f"Total articles scraped from {config.key}: {len(articles)}")
        
        except Exception as e:
            logger.error(f"Scraper error for {config.key}: {str(e)}", exc_info=True)
        
        return articles


async def scrape_multiple_newspapers_manual(
    newspapers: List[str],
    start_date: date,
    end_date: date,
    max_articles_per_newspaper: int = 50,
    db: Session = None
) -> Dict[str, Any]:
    """
    Scrape multiple newspapers and store articles WITHOUT processing.
    
    Args:
        newspapers: List of newspaper keys to scrape
        start_date: Start date for scraping
        end_date: End date for scraping
        max_articles_per_newspaper: Maximum articles per newspaper
        db: Database session
        
    Returns:
        Overall scraping statistics
    """
    if not db:
        from app.database.database import SessionLocal
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        scraper = ManualOnlyNewsScraper(db)
        
        overall_stats = {
            "total_scraped": 0,
            "total_new": 0,
            "total_duplicates": 0,
            "newspapers": {},
            "errors": []
        }
        
        logger.info(f"Starting manual scraping for {len(newspapers)} newspapers")
        
        for newspaper in newspapers:
            try:
                logger.info(f"Scraping {newspaper}...")
                
                stats = await scraper.scrape_only(
                    source=newspaper,
                    start_date=start_date,
                    end_date=end_date
                )
                
                overall_stats["newspapers"][newspaper] = stats
                overall_stats["total_new"] += stats["new_articles"]
                overall_stats["total_duplicates"] += stats["duplicates"]
                overall_stats["errors"].extend(stats["errors"])
                
                logger.info(f"Completed {newspaper}: {stats['new_articles']} new articles")
                
            except Exception as e:
                error_msg = f"Failed to scrape {newspaper}: {str(e)}"
                logger.error(error_msg)
                overall_stats["errors"].append(error_msg)
        
        overall_stats["total_scraped"] = overall_stats["total_new"] + overall_stats["total_duplicates"]
        
        logger.info(
            f"Manual scraping complete: "
            f"{overall_stats['total_new']} new articles stored (unprocessed), "
            f"{overall_stats['total_duplicates']} duplicates"
        )
        
        return overall_stats
        
    finally:
        if should_close:
            db.close()