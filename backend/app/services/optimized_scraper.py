"""
Optimized web scraping module for Bangladeshi newspapers.
Implements performance improvements for faster scraping.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
        # NOTE: Do NOT include 'br' (Brotli) in Accept-Encoding unless
        # the 'brotli' package is installed - requests can't decode it natively
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5,bn;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Configure session with increased connection pool
        self.session = requests.Session()
        
        # Increase connection pool size to handle concurrent requests
        adapter = HTTPAdapter(
            pool_connections=20,  # Increased from default 10
            pool_maxsize=20,      # Increased from default 10
            max_retries=Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
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
    ARTICLES_PER_SECTION = 50
    MAX_PARALLEL_FETCHES = 10
    
    # Section groups matching Prothom Alo's section IDs
    OPTIMIZED_SECTIONS = [
        '22237',  # রাজনীতি (Politics)
        '17533,17535,17536,17538,22321,22236',  # বাংলাদেশ (Bangladesh)
        '17690,17693,17691,22329,22327,22330,17694',  # মতামত (Opinion)
        '17584,17586,22323,35621,17585,17587,17588,17589,17591',  # বিশ্ব (World/International)
    ]
    
    # Map section IDs to category names
    SECTION_CATEGORY_MAP = {
        '22237': 'রাজনীতি',
        '17533,17535,17536,17538,22321,22236': 'বাংলাদেশ',
        '17690,17693,17691,22329,22327,22330,17694': 'মতামত',
        '17584,17586,22323,35621,17585,17587,17588,17589,17591': 'বিশ্ব',
    }
    
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
        """Optimized section scraping - extracts content from API response directly."""
        start_dt = self.start_date
        end_dt = self.end_date.replace(hour=23, minute=59, second=59)
        
        published_after = int(start_dt.timestamp() * 1000)
        published_before = int(end_dt.timestamp() * 1000)
        
        # Look up Bengali category name for this section group
        category = self.SECTION_CATEGORY_MAP.get(section_ids)
        logger.info(f"  Processing section: {section_ids} (category: {category})")
        
        # Step 1: Collect stories with content from API (using 'cards' field)
        stories_to_process = []
        offset = 0
        max_stories = self.ARTICLES_PER_SECTION
        
        while len(stories_to_process) < max_stories:
            params = {
                'published-after': published_after,
                'published-before': published_before,
                'section-id': section_ids,
                'type': 'text,team-bio,listicle,',
                'limit': min(self.PAGE_SIZE, max_stories - len(stories_to_process)),
                'offset': offset,
                'fields': 'headline,slug,published-at,first-published-at,subheadline,summary,cards'
            }
            
            try:
                response = self.session.get(self.API_SEARCH_URL, params=params, timeout=20)
                response.raise_for_status()
                
                if not response.text or response.text.strip() == '':
                    break
                
                data = response.json()
                results = data.get('results', {})
                stories = results.get('stories', [])
                
                if not stories:
                    break
                
                # Filter and collect valid stories with content
                for story in stories:
                    if len(stories_to_process) >= max_stories:
                        break
                    
                    metadata = self._extract_story_with_content(story, category)
                    if metadata and self.add_seen_url(metadata['url']):
                        stories_to_process.append(metadata)
                
                offset += len(stories)
                
                if len(stories) < self.PAGE_SIZE:
                    break
                    
                time.sleep(0.3)
                    
            except Exception as e:
                logger.error(f"  API request failed for section {section_ids}: {str(e)}")
                break
        
        logger.info(f"  Section {section_ids}: Collected {len(stories_to_process)} stories")
        
        # Step 2: Create articles - content already extracted from API
        # For stories without API content, fetch from page in parallel
        articles = []
        stories_needing_fetch = []
        
        for story in stories_to_process:
            if story.get('content') and len(story['content']) > 100:
                # Content already available from API
                article = self._create_article_from_metadata(story)
                if article:
                    articles.append(article)
            else:
                stories_needing_fetch.append(story)
        
        logger.info(f"  Section {section_ids}: {len(articles)} articles from API, {len(stories_needing_fetch)} need page fetch")
        
        # Fetch remaining articles from their pages
        if stories_needing_fetch:
            with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_FETCHES) as content_executor:
                content_futures = [
                    content_executor.submit(self._fetch_and_create_article, story)
                    for story in stories_needing_fetch
                ]
                
                for future in as_completed(content_futures):
                    try:
                        article = future.result()
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.error(f"  Failed to fetch article content: {str(e)}")
        
        logger.info(f"  Section {section_ids}: Total {len(articles)} articles")
        return articles
    
    def _extract_story_with_content(self, story_data: Dict, category: Optional[str] = None) -> Optional[Dict]:
        """Extract story metadata and content from API response.
        
        The search API returns cards > story-elements with full article text
        when 'cards' is included in the fields parameter.
        """
        try:
            headline = story_data.get('headline', '').strip()
            slug = story_data.get('slug', '').strip()
            
            if not headline or not slug:
                return None
            
            # Skip non-article content
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
            
            # Extract content from cards > story-elements
            content = self._extract_content_from_cards(story_data.get('cards', []))
            
            return {
                'headline': headline,
                'url': url,
                'published_date': article_date.strftime('%Y-%m-%d'),
                'summary': story_data.get('summary', '') or story_data.get('subheadline', ''),
                'content': content,
                'category': category
            }
            
        except Exception as e:
            logger.debug(f"Failed to extract story data: {str(e)}")
            return None
    
    def _extract_content_from_cards(self, cards: List[Dict]) -> str:
        """Extract text content from API cards > story-elements.
        
        Each card contains story-elements with type='text' having HTML content.
        """
        content_parts = []
        
        for card in cards:
            elements = card.get('story-elements', [])
            for element in elements:
                if element.get('type') == 'text':
                    html_text = element.get('text', '')
                    if html_text:
                        # Parse HTML tags from story-element text
                        soup = BeautifulSoup(html_text, 'html.parser')
                        text = soup.get_text(strip=True)
                        if text and len(text) > 10:
                            # Skip navigation/related text
                            if not text.startswith(('আরও পড়ুন', 'সম্পর্কিত', 'ছবি:', 'ভিডিও:')):
                                content_parts.append(text)
        
        return ' '.join(content_parts)
    
    def _create_article_from_metadata(self, metadata: Dict) -> Optional[ScrapedArticle]:
        """Create a ScrapedArticle from metadata that already has content."""
        try:
            content = metadata.get('content', '')
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
                source="prothom_alo",
                category=metadata.get('category')
            )
        except Exception as e:
            logger.warning(f"Failed to create article from metadata: {str(e)}")
            return None
    
    def _fetch_and_create_article(self, metadata: Dict) -> Optional[ScrapedArticle]:
        """Optimized article content fetching with fallback to summary."""
        try:
            # Try to get full content first
            full_content = self.fetch_article_content(metadata['url'])
            
            # Use full content if good, otherwise use summary
            if full_content and len(full_content) > 100:
                content = full_content
            elif metadata.get('summary') and len(metadata['summary']) > 50:
                content = metadata['summary']
                logger.debug(f"Using summary for {metadata['url']} (full content failed)")
            else:
                logger.debug(f"Skipping {metadata['url']} - insufficient content")
                return None
            
            # Truncate content to 2000 characters for LLM processing efficiency
            if len(content) > 2000:
                content = content[:2000]
            
            return ScrapedArticle(
                title=metadata['headline'],
                content=content,
                url=metadata['url'],
                published_date=metadata['published_date'],
                source="prothom_alo",
                category=metadata.get('category')
            )
            
        except Exception as e:
            logger.warning(f"Failed to create article from {metadata.get('url', 'unknown')}: {str(e)}")
            return None
    
    def fetch_article_content(self, url: str) -> str:
        """Fetch article content from page HTML with comprehensive selector fallbacks."""
        try:
            response = self.make_request(url)
            if not response:
                return ""
            
            # Use 'lxml' parser for better handling of edge cases
            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except Exception:
                soup = BeautifulSoup(response.text, 'html.parser')
            content_parts = []
            
            # Comprehensive list of content selectors (most specific to most general)
            content_selectors = [
                'div.story-content',
                'div.story-details',
                'div.story_content',
                'article .content',
                'div.article-content',
                'div.content-detail',
                'div[itemprop="articleBody"]',
                'div.article_content',
                'div.news-content',
                'div.main-content',
                'article',
                '.content'
            ]
            
            for selector in content_selectors:
                try:
                    content_divs = soup.select(selector)
                    if content_divs:
                        for div in content_divs:
                            # Get all text content, not just <p> tags
                            paragraphs = div.find_all(['p', 'div'], recursive=True)
                            if not paragraphs:
                                # Fallback: get direct text
                                text = div.get_text(strip=True)
                                if text and len(text) > 50:
                                    content_parts.append(text)
                            else:
                                for p in paragraphs:
                                    text = p.get_text(strip=True)
                                    if text and len(text) > 20 and not text.startswith(('আরও পড়ুন', 'সম্পর্কিত', 'ছবি:', 'ভিডিও:')):
                                        content_parts.append(text)
                        
                        if content_parts and len(' '.join(content_parts)) > 100:
                            break
                except Exception:
                    continue
            
            # If still no content, try getting all paragraphs from body
            if not content_parts:
                body = soup.find('body')
                if body:
                    paragraphs = body.find_all('p', limit=50)
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 30:
                            content_parts.append(text)
            
            result = ' '.join(content_parts)
            # Clean up excessive whitespace
            result = re.sub(r'\s+', ' ', result).strip()
            return result
            
        except Exception as e:
            logger.warning(f"Failed to fetch article content from {url}: {str(e)}")
            return ""


class OptimizedJugantorScraper(OptimizedNewspaperScraper):
    """Optimized scraper for Jugantor - Category-based scraping."""
    
    BASE_URL = "https://www.jugantor.com"
    
    # Only scrape these 4 categories
    CATEGORY_MAP = {
        '/opinion': 'মতামত',
        '/national': 'বাংলাদেশ',
        '/politics': 'রাজনীতি',
        '/international': 'বিশ্ব',
    }
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Optimized Jugantor category-based scraping with parallel processing."""
        logger.info("Starting optimized Jugantor category-based scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        
        # Process categories in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._scrape_category, path, category): category
                for path, category in self.CATEGORY_MAP.items()
            }
            
            for future in as_completed(futures):
                category = futures[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(f"Category '{category}': {len(articles)} articles (Total: {len(all_articles)})")
                except Exception as e:
                    logger.error(f"Failed category '{category}': {str(e)}")
        
        logger.info(f"Jugantor: Scraped {len(all_articles)} total articles")
        return all_articles
    
    def _scrape_category(self, path: str, category: str) -> List[ScrapedArticle]:
        """Scrape articles from a single category page."""
        articles = []
        category_url = f"{self.BASE_URL}{path}"
        
        try:
            response = self.make_request(category_url)
            if not response:
                return articles
            
            soup = BeautifulSoup(response.content, 'lxml')
            article_links = []
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if not href:
                    continue
                
                # Accept article links containing the category path
                if path in href or '/news/' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    if '/archive' not in full_url and self.add_seen_url(full_url):
                        article_links.append(full_url)
            
            article_links = list(set(article_links))[:50]
            logger.info(f"  Found {len(article_links)} links for category '{category}'")
            
            # Fetch articles in parallel
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {
                    executor.submit(self._scrape_article, url, category): url
                    for url in article_links
                }
                
                for future in as_completed(future_to_url):
                    try:
                        article = future.result()
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.debug(f"Failed to scrape article: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to scrape Jugantor category {category}: {str(e)}")
        
        return articles
    
    def _clean_content(self, content: str) -> str:
        """Optimized content cleaning."""
        if not content:
            return ""
        
        unwanted_patterns = [
            r'ফলো করুন.*?যুগান্তর মেসেঞ্জার',
            r'যুগান্তর প্রতিবেদন.*?পিএম',
            r'আরও পড়ুন.*?সম্পর্কিত খবর',
            r'প্রকাশ:.*?পিএম',
            r'সম্পর্কিত খবর.*',
        ]
        
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        if "সম্পর্কিত খবর" in content:
            content = content.split("সম্পর্কিত খবর")[0]
        
        content = re.sub(r'\s+', ' ', content.strip())
        return content
    
    def _scrape_article(self, url: str, category: str) -> Optional[ScrapedArticle]:
        """Scrape individual Jugantor article with category."""
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Title extraction
            title = None
            for selector in ['h1', 'h1.title', '.headline h1', '.news-title']:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if title and len(title) > 5:
                        break
            
            if not title:
                return None
            
            # Content extraction
            content_parts = []
            content_selectors = [
                'div.news-element-text',
                'div.news-element',
                'div.content',
                'div.details',
                'div.article-content',
                'div.news-content',
                'div.story-content',
                'article .content',
                'article',
            ]
            
            for selector in content_selectors:
                try:
                    content_div = soup.select_one(selector)
                    if content_div:
                        paragraphs = content_div.find_all(['p', 'div'], recursive=True, limit=100)
                        if paragraphs:
                            for p in paragraphs:
                                text = p.get_text(strip=True)
                                if text and len(text) > 20 and not text.startswith(('আরও পড়ুন', 'সম্পর্কিত', 'ছবি')):
                                    content_parts.append(text)
                        else:
                            text = content_div.get_text(strip=True)
                            if text and len(text) > 50:
                                content_parts.append(text)
                        
                        if content_parts and len(' '.join(content_parts)) > 100:
                            break
                except Exception:
                    continue
            
            content = ' '.join(content_parts)
            content = self._clean_content(content)
            
            if not content or len(content) < 50:
                return None
            
            # Truncate content
            if len(content) > 2000:
                content = content[:2000]
            
            # Try to extract date
            published_date = None
            date_tag = soup.find('time')
            if date_tag:
                published_date = date_tag.get('datetime')
            if not published_date:
                meta_date = soup.find('meta', property='article:published_time')
                if meta_date:
                    published_date = meta_date.get('content')
            
            if published_date:
                try:
                    article_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    if not self.is_within_date_range(article_date):
                        return None
                    published_date = article_date.strftime('%Y-%m-%d')
                except:
                    published_date = datetime.now().strftime('%Y-%m-%d')
            else:
                published_date = datetime.now().strftime('%Y-%m-%d')
            
            return ScrapedArticle(
                title=title,
                content=content,
                url=url,
                published_date=published_date,
                source="jugantor",
                category=category
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