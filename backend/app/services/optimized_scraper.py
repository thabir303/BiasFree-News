"""
Optimized web scraping module for Bangladeshi newspapers.
Implements performance improvements for faster scraping.
"""
import requests
import re
import time
import threading
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.schemas import ScrapedArticle
import hashlib
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)


class OptimizedNewspaperScraper:
    """Optimized base class for newspaper scrapers with performance improvements."""
    
    def __init__(self, start_date: str, end_date: str):
        """Initialize scraper with date range."""
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Optimized headers for faster requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Use session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # URL cache to avoid duplicates
        self._seen_urls: Set[str] = set()
        self._url_lock = threading.Lock()
        
        logger.info(f"Initialized optimized scraper for date range: {start_date} to {end_date}")
    
    def is_within_date_range(self, article_date: datetime) -> bool:
        """Check if article date is within specified range."""
        if article_date.tzinfo is not None:
            article_date = article_date.replace(tzinfo=None)
        
        article_date_only = article_date.date()
        start_date_only = self.start_date.date()
        end_date_only = self.end_date.date()
        
        return start_date_only <= article_date_only <= end_date_only
    
    def make_request(self, url: str, max_retries: int = 2, timeout: int = 15) -> Optional[requests.Response]:
        """
        Make optimized HTTP request with reduced retries and timeout.
        
        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts (reduced from 3)
            timeout: Request timeout in seconds (reduced from 30)
            
        Returns:
            Response object or None
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=timeout, allow_redirects=True)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    # Reduced exponential backoff
                    time.sleep(2 ** attempt * 0.5)  # Reduced from 2^attempt
        return None
    
    def add_seen_url(self, url: str) -> bool:
        """Add URL to seen set and return True if new."""
        with self._url_lock:
            if url in self._seen_urls:
                return False
            self._seen_urls.add(url)
            return True


class OptimizedProthomAloScraper(OptimizedNewspaperScraper):
    """Optimized scraper for Prothom Alo with parallel processing."""
    
    BASE_URL = "https://www.prothomalo.com"
    API_SEARCH_URL = "https://www.prothomalo.com/api/v1/search"
    PAGE_SIZE = 100
    ARTICLES_PER_SECTION = 30  # Reduced from 50 for faster processing
    MAX_PARALLEL_FETCHES = 15  # Increased from 10 for better parallelism
    
    # Optimized section groups - fewer but more relevant
    OPTIMIZED_SECTIONS = [
        '22237',  # রাজনীতি (Politics) - Most important
        '17533,17535,17536,17538,22321,22236',  # বাংলাদেশ (Bangladesh)
        '17690,17693,17691,22329,22327,22330,17694',  # মতামত (Opinion)
    ]
    
    def __init__(self, start_date: str, end_date: str, section_ids: Optional[List[str]] = None):
        super().__init__(start_date, end_date)
        self.section_ids = section_ids if section_ids else self.OPTIMIZED_SECTIONS
        logger.info(f"Prothom Alo scraper initialized with {len(self.section_ids)} optimized section groups")
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Optimized scraping with better parallelization."""
        logger.info("Starting optimized Prothom Alo scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        
        # Process sections in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as section_executor:
            section_futures = [
                section_executor.submit(self.scrape_section, section_id)
                for section_id in self.section_ids
            ]
            
            for future in as_completed(section_futures):
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(f"Section completed: {len(articles)} articles (Total: {len(all_articles)})")
                except Exception as e:
                    logger.error(f"Section scraping failed: {str(e)}")
        
        logger.info(f"Prothom Alo: Scraped {len(all_articles)} total articles from {len(self.section_ids)} sections")
        return all_articles
    
    def scrape_section(self, section_ids: str) -> List[ScrapedArticle]:
        """Optimized section scraping with better error handling."""
        start_dt = self.start_date
        end_dt = self.end_date.replace(hour=23, minute=59, second=59)
        
        published_after = int(start_dt.timestamp() * 1000)
        published_before = int(end_dt.timestamp() * 1000)
        
        logger.info(f"  Processing section: {section_ids}")
        
        # Step 1: Collect story metadata efficiently
        stories_to_process = []
        offset = 0
        max_stories = self.ARTICLES_PER_SECTION
        
        while len(stories_to_process) < max_stories:
            params = {
                'published-after': published_after,
                'published-before': published_before,
                'section-id': section_ids,
                'type': 'text,team-bio,listicle',
                'limit': min(self.PAGE_SIZE, max_stories - len(stories_to_process)),
                'offset': offset
            }
            
            try:
                response = self.session.get(self.API_SEARCH_URL, params=params, timeout=15)
                response.raise_for_status()
                
                if not response.text or response.text.strip() == '':
                    break
                
                data = response.json()
                results = data.get('results', {})
                stories = results.get('stories', [])
                
                if not stories:
                    break
                
                # Filter and collect valid stories
                for story in stories:
                    if len(stories_to_process) >= max_stories:
                        break
                    
                    metadata = self._extract_story_metadata(story)
                    if metadata and self.add_seen_url(metadata['url']):
                        stories_to_process.append(metadata)
                
                offset += len(stories)
                
                if len(stories) < self.PAGE_SIZE:
                    break
                    
                # Reduced delay between API calls
                time.sleep(0.2)  # Reduced from 0.5s
                    
            except Exception as e:
                logger.error(f"  API request failed for section {section_ids}: {str(e)}")
                break
        
        logger.info(f"  Section {section_ids}: Collected {len(stories_to_process)} story metadata")
        
        # Step 2: Fetch content in parallel with increased workers
        articles = []
        
        with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_FETCHES) as content_executor:
            content_futures = [
                content_executor.submit(self._fetch_and_create_article, story)
                for story in stories_to_process
            ]
            
            for future in as_completed(content_futures):
                try:
                    article = future.result()
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"  Failed to fetch article content: {str(e)}")
        
        logger.info(f"  Section {section_ids}: Successfully fetched {len(articles)} articles")
        return articles
    
    def _extract_story_metadata(self, story_data: Dict) -> Optional[Dict]:
        """Optimized metadata extraction."""
        try:
            headline = story_data.get('headline', '').strip()
            slug = story_data.get('slug', '').strip()
            
            if not headline or not slug:
                return None
            
            # Skip problematic sections more efficiently
            skip_sections = ['feature/', 'features/', 'activities/', 'activity/', 'quiz/', 'games/', 'video/']
            if any(section in slug for section in skip_sections):
                return None
            
            url = f"{self.BASE_URL}/{slug}"
            
            published_at = story_data.get('published-at') or story_data.get('first-published-at')
            if not published_at:
                return None
            
            article_date = datetime.fromtimestamp(published_at / 1000)
            
            if not self.is_within_date_range(article_date):
                return None
            
            return {
                'headline': headline,
                'url': url,
                'published_date': article_date.strftime('%Y-%m-%d'),
                'summary': story_data.get('summary', '') or story_data.get('subheadline', '')
            }
            
        except Exception as e:
            logger.debug(f"Failed to extract metadata: {str(e)}")
            return None
    
    def _fetch_and_create_article(self, metadata: Dict) -> Optional[ScrapedArticle]:
        """Optimized article content fetching."""
        try:
            full_content = self.fetch_article_content(metadata['url'])
            content = full_content if full_content and len(full_content) > 100 else metadata['summary']
            
            if not content or len(content) < 50:
                return None
            
            # Truncate content to 2000 characters for LLM processing efficiency
            if len(content) > 2000:
                content = content[:2000]
            
            return ScrapedArticle(
                title=metadata['headline'],
                content=content,
                url=metadata['url'],
                published_date=metadata['published_date'],
                source="prothom_alo"
            )
            
        except Exception as e:
            logger.debug(f"Failed to create article: {str(e)}")
            return None
    
    def fetch_article_content(self, url: str) -> str:
        """Optimized content fetching with better error handling."""
        try:
            response = self.make_request(url)
            if not response:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # More efficient content extraction
            content_parts = []
            
            # Try main content selectors first
            content_selectors = [
                'div.story-content',
                'div.story-details',
                'article .content',
                '.article-content'
            ]
            
            for selector in content_selectors:
                content_divs = soup.select(selector)
                if content_divs:
                    for div in content_divs:
                        paragraphs = div.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 20:
                                content_parts.append(text)
                    
                    if content_parts:
                        break
            
            return ' '.join(content_parts)
            
        except Exception as e:
            logger.debug(f"Failed to fetch article content from {url}: {str(e)}")
            return ""


class OptimizedJugantorScraper(OptimizedNewspaperScraper):
    """Optimized scraper for Jugantor."""
    
    BASE_URL = "https://www.jugantor.com"
    ARCHIVE_BASE_URL = "https://www.jugantor.com/archive"
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Optimized Jugantor scraping with parallel processing."""
        logger.info("Starting optimized Jugantor scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        dates_to_scrape = []
        current_date = self.start_date
        
        # Generate date list
        while current_date <= self.end_date:
            dates_to_scrape.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        logger.info(f"Total dates to scrape: {len(dates_to_scrape)}")
        
        # Process dates in parallel (limited to 3 concurrent workers)
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_date = {
                executor.submit(self.scrape_articles_for_date, date): date 
                for date in dates_to_scrape
            }
            
            for future in as_completed(future_to_date):
                date = future_to_date[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(f"Completed {date}: {len(articles)} articles (Total: {len(all_articles)})")
                except Exception as e:
                    logger.error(f"Failed {date}: {str(e)}")
        
        logger.info(f"Jugantor: Scraped {len(all_articles)} total articles")
        return all_articles
    
    def scrape_articles_for_date(self, date: str) -> List[ScrapedArticle]:
        """Optimized daily scraping."""
        all_articles = []
        page = 1
        max_pages = 20  # Reduced from 50 to limit processing
        
        # Collect article URLs more efficiently
        all_article_urls = []
        
        while page <= max_pages:
            archive_url = self.get_archive_url(date, page)
            article_urls = self.extract_article_links(archive_url)
            
            if not article_urls:
                break
            
            # Filter out already seen URLs immediately
            new_urls = [url for url in article_urls if self.add_seen_url(url)]
            all_article_urls.extend(new_urls)
            
            page += 1
            # Reduced delay
            time.sleep(0.1)  # Reduced from 0.5s
        
        if not all_article_urls:
            return []
        
        logger.info(f"  Total new article URLs for {date}: {len(all_article_urls)}")
        
        # Process articles in parallel with limited workers
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(self.scrape_article, url, date): url 
                for url in all_article_urls
            }
            
            for future in as_completed(future_to_url):
                try:
                    article = future.result()
                    if article:
                        all_articles.append(article)
                except Exception as e:
                    logger.debug(f"Failed to scrape article: {str(e)}")
        
        return all_articles
    
    def get_archive_url(self, date: str, page: int = None) -> str:
        """Generate archive URL for a specific date and page."""
        if page is None or page == 1:
            return f"{self.ARCHIVE_BASE_URL}?date={date}"
        else:
            return f"{self.ARCHIVE_BASE_URL}?date={date}&page={page}"
    
    def extract_article_links(self, archive_url: str) -> List[str]:
        """Extract article links from archive page."""
        response = self.make_request(archive_url)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            article_links = []
            
            # More focused link extraction
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if not href:
                    continue
                
                # Accept various article URL patterns
                valid_patterns = [
                    '/national/', '/politics/', '/international/', 
                    '/sports/', '/entertainment/', '/economics/',
                    '/country/', '/city/', '/lifestyle/', '/opinion/'
                ]
                
                if any(pat in href for pat in valid_patterns):
                    full_url = urljoin(self.BASE_URL, href)
                    if '/archive' not in full_url:
                        article_links.append(full_url)
            
            # Remove duplicates efficiently
            return list(set(article_links))
            
        except Exception as e:
            logger.debug(f"Failed to extract links from {archive_url}: {str(e)}")
            return []
    
    def clean_content(self, content: str) -> str:
        """Optimized content cleaning."""
        if not content:
            return ""
        
        # More efficient regex patterns
        unwanted_patterns = [
            r'ফলো করুন.*?যুগান্তর মেসেঞ্জার',
            r'যুগান্তর প্রতিবেদন.*?পিএম',
            r'আরও পড়ুন.*?সম্পর্কিত খবর',
            r'প্রকাশ:.*?পিএম',
            r'সম্পর্কিত খবর.*',
        ]
        
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # More efficient string operations
        if "সম্পর্কিত খবর" in content:
            content = content.split("সম্পর্কিত খবর")[0]
        
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        
        return content
    
    def scrape_article(self, url: str, date: str) -> Optional[ScrapedArticle]:
        """Optimized article scraping."""
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Faster title extraction
            title = None
            title_selectors = ['h1', 'h1.title', '.headline h1', '.news-title', '.article-title']
            for selector in title_selectors:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if title and len(title) > 5:  # Ensure meaningful title
                        break
            
            if not title:
                return None
            
            # More efficient content extraction
            content_parts = []
            content_selectors = [
                'div.news-element-text',
                'div.content',
                'div.details',
                'div.article-content',
                'div.news-content',
                'article .content'
            ]
            
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    paragraphs = content_div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            content_parts.append(text)
                    
                    if content_parts:
                        break
            
            content = ' '.join(content_parts)
            content = self.clean_content(content)
            
            if not content or len(content) < 50:
                return None
            
            return ScrapedArticle(
                title=title,
                content=content,
                url=url,
                published_date=date,
                source="jugantor"
            )
            
        except Exception as e:
            logger.debug(f"Failed to scrape article {url}: {str(e)}")
            return None


class OptimizedNewsScraper:
    """Main optimized scraper class that coordinates all newspaper scrapers."""
    
    def __init__(self):
        """Initialize the main scraper."""
        # Pre-compile regex patterns for better performance
        self.url_pattern = re.compile(r'https?://[^\s]+')
        
    async def scrape_articles(
        self,
        source: str,
        start_date: date,
        end_date: date
    ) -> List[ScrapedArticle]:
        """
        Scrape articles from specified source within date range using optimized scrapers.
        
        Args:
            source: Newspaper source (prothom_alo, jugantor, daily_star, dhaka_tribune, samakal)
            start_date: Start date for scraping
            end_date: End date for scraping
        
        Returns:
            List of scraped articles
        """
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Map to optimized scrapers
        optimized_scraper_map = {
            "prothom_alo": OptimizedProthomAloScraper,
            "jugantor": OptimizedJugantorScraper,
            # Add other optimized scrapers as they are implemented
        }
        
        scraper_class = optimized_scraper_map.get(source)
        if not scraper_class:
            # Fall back to original scraper for unoptimized sources
            logger.info(f"Using original scraper for {source}")
            from app.services.scraper import NewsScraper
            original_scraper = NewsScraper()
            return await original_scraper.scrape_articles(source, start_date, end_date)
        
        try:
            loop = asyncio.get_event_loop()
            scraper = scraper_class(start_str, end_str)
            articles = await loop.run_in_executor(None, scraper.scrape_articles)
            
            logger.info(f"Optimized scraping: {len(articles)} articles from {source}")
            return articles
            
        except Exception as e:
            logger.error(f"Optimized scraping failed for {source}: {str(e)}")
            # Fall back to original scraper on error
            from app.services.scraper import NewsScraper
            original_scraper = NewsScraper()
            return await original_scraper.scrape_articles(source, start_date, end_date)