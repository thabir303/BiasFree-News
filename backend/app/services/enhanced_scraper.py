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
        end_date: date
    ) -> Dict[str, Any]:
        """
        Scrape articles and store in database.
        
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
                end_date
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
                    
                    # Convert published_date string to datetime if needed
                    pub_date = article_data.get("published_date")
                    if pub_date and isinstance(pub_date, str):
                        try:
                            pub_date = datetime.strptime(pub_date, "%Y-%m-%d")
                        except ValueError:
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
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Scrape articles from a specific source using the new scraper classes.
        """
        articles = []
        
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Use the new scraper classes
            scraper_map = {
                "prothom_alo": ProthomAloScraper,
                "jugantor": JugantorScraper,
                "daily_star": DailyStarScraper,
                "dhaka_tribune": DhakaTribuneScraper,
                "samakal": SamakalScraper
            }
            
            scraper_class = scraper_map.get(config.key)
            if not scraper_class:
                logger.warning(f"No scraper implemented for: {config.key}")
                return articles
            
            # Initialize and run scraper
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
        
        except Exception as e:
            logger.error(f"Scraper error for {config.key}: {str(e)}", exc_info=True)
        
        return articles[:settings.max_scrape_articles]
