"""
Enhanced scraper service with database integration and improved article extraction.
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


class EnhancedNewsScraper:
    """
    Enhanced web scraper for Bengali and English newspapers.
    Includes database integration and better error handling.
    """
    
    def __init__(self, db: Session):
        """Initialize scraper with database session."""
        self.db = db
    
    async def scrape_and_store(
        self,
        source: str,
        start_date: date,
        end_date: date,
        section_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Scrape articles and store in database.
        
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
            "errors": []
        }
        
        try:
            # Get newspaper configuration
            config = get_newspaper_config(source)
            
            # Scrape articles
            loop = asyncio.get_event_loop()
            articles = await loop.run_in_executor(
                None,
                self._scrape_source,
                config,
                start_date,
                end_date,
                section_ids
            )
            
            stats["total_scraped"] = len(articles)
            
            # Store in database
            for article_data in articles:
                try:
                    # Check if article already exists
                    existing = self.db.query(Article).filter(
                        Article.url == article_data["url"]
                    ).first()
                    
                    if existing:
                        stats["duplicates"] += 1
                        logger.debug(f"Duplicate article skipped: {article_data['url']}")
                        continue
                    
                    # Convert published_date to proper datetime object
                    pub_date = article_data.get("published_date")
                    if pub_date:
                        if isinstance(pub_date, str):
                            try:
                                # Try multiple date formats
                                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"]:
                                    try:
                                        pub_date = datetime.strptime(pub_date, fmt)
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    # If no format worked, set to None
                                    logger.warning(f"Could not parse date: {pub_date}")
                                    pub_date = None
                            except Exception as e:
                                logger.warning(f"Date parsing error: {e}")
                                pub_date = None
                        elif isinstance(pub_date, date) and not isinstance(pub_date, datetime):
                            # Convert date to datetime
                            pub_date = datetime.combine(pub_date, datetime.min.time())
                        elif not isinstance(pub_date, datetime):
                            # If it's neither string, date, nor datetime, set to None
                            logger.warning(f"Invalid date type: {type(pub_date)}")
                            pub_date = None
                    
                    # Create new article
                    article = Article(
                        source=source,
                        url=article_data["url"],
                        title=article_data.get("title"),
                        original_content=article_data["content"],
                        published_date=pub_date,
                        scraped_at=datetime.utcnow(),
                        processed=False
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
                f"{stats['new_articles']} new, "
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
        Scrape articles from a specific source using optimized scraper classes.
        
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
                logger.info(f"Initializing optimized Prothom Alo scraper with {len(section_ids)} section groups")
                scraper = scraper_class(start_str, end_str, section_ids)
            else:
                scraper = scraper_class(start_str, end_str)
            
            scraped_articles = scraper.scrape_articles()
            
            # Convert ScrapedArticle objects to dictionaries
            for article in scraped_articles:
                articles.append({
                    "url": article.url,
                    "title": article.title,
                    "content": article.content,
                    "published_date": article.published_date
                })
            
            logger.info(f"Total articles scraped from {config.key}: {len(articles)}")
        
        except Exception as e:
            logger.error(f"Scraper error for {config.key}: {str(e)}", exc_info=True)
        
        # No limit - return all scraped articles
        return articles
