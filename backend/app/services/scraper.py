"""
Web scraping module for Bangladeshi newspapers.
Scrapes articles from Prothom Alo, Jugantor, Daily Star, and Dhaka Tribune.
"""
import requests
import re
import time
import threading
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.schemas import ScrapedArticle

# Configure logging
logger = logging.getLogger(__name__)


class NewspaperScraper:
    """Base class for newspaper scrapers."""
    
    def __init__(self, start_date: str, end_date: str):
        """
        Initialize scraper with date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,bn;q=0.8',
            'Referer': 'https://www.prothomalo.com/',
            'Origin': 'https://www.prothomalo.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        logger.info(f"Initialized scraper for date range: {start_date} to {end_date}")
    
    def is_within_date_range(self, article_date: datetime) -> bool:
        """Check if article date is within specified range."""
        if article_date.tzinfo is not None:
            article_date = article_date.replace(tzinfo=None)
        
        article_date_only = article_date.date()
        start_date_only = self.start_date.date()
        end_date_only = self.end_date.date()
        
        return start_date_only <= article_date_only <= end_date_only
    
    def make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Make HTTP request with retries.
        
        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response object or None
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return None


class ProthomAloScraper(NewspaperScraper):
    """Scraper for Prothom Alo (Bangla) - All sections using search API."""
    
    BASE_URL = "https://www.prothomalo.com"
    API_SEARCH_URL = "https://www.prothomalo.com/api/v1/search"
    PAGE_SIZE = 100
    ARTICLES_PER_SECTION = 50  # Max articles to fetch per section
    MAX_PARALLEL_FETCHES = 10  # Number of parallel content fetches
    
    # Default section IDs for different categories (from Prothom Alo website)
    # These are the actual section IDs used in Prothom Alo's search API
    DEFAULT_SECTIONS = [
        '22237',  # রাজনীতি (Politics)
        '17533,17535,17536,17538,22321,22236',  # বাংলাদেশ (Bangladesh)
        '17690,17693,17691,22329,22327,22330,17694',  # মতামত (Opinion)
        '17584,17586,22323,35621,17585,17587,17588,17589,17591'  # বিশ্ব (World/International)
    ]
    
    def __init__(self, start_date: str, end_date: str, section_ids: Optional[List[str]] = None):
        """
        Initialize Prothom Alo scraper with optional section filtering.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            section_ids: Optional list of section IDs to scrape. If None, uses DEFAULT_SECTIONS
        """
        super().__init__(start_date, end_date)
        self._lock = threading.Lock()
        self._seen_urls = set()
        self.section_ids = section_ids if section_ids else self.DEFAULT_SECTIONS
        logger.info(f"Prothom Alo scraper initialized with {len(self.section_ids)} section groups")
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from Prothom Alo using search API with section filtering."""
        logger.info("Starting Prothom Alo scraping (Section-based with date range)...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Sections to scrape: {len(self.section_ids)} groups")
        
        all_articles = []
        
        # Scrape each section group
        for section_id_group in self.section_ids:
            logger.info(f"\n{'='*60}")
            logger.info(f"Scraping section group: {section_id_group}")
            logger.info(f"{'='*60}")
            
            try:
                articles = self.scrape_section(section_id_group)
                all_articles.extend(articles)
                logger.info(f"Section {section_id_group}: Collected {len(articles)} articles (Total so far: {len(all_articles)})")
                time.sleep(0.5)  # Minimal delay between sections
            except Exception as e:
                logger.error(f"Failed to scrape section {section_id_group}: {str(e)}")
        
        logger.info(f"\nProthom Alo: Scraped {len(all_articles)} total articles from {len(self.section_ids)} section groups")
        return all_articles
    
    def scrape_section(self, section_ids: str) -> List[ScrapedArticle]:
        """Scrape articles for a specific section or group of sections with parallelization."""
        start_dt = self.start_date
        end_dt = self.end_date.replace(hour=23, minute=59, second=59)
        
        published_after = int(start_dt.timestamp() * 1000)
        published_before = int(end_dt.timestamp() * 1000)
        
        logger.info(f"  Date range: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
        logger.info(f"  Target: {self.ARTICLES_PER_SECTION} articles per section")
        
        # Step 1: Collect story metadata from API (fast)
        stories_to_process = []
        offset = 0
        
        while len(stories_to_process) < self.ARTICLES_PER_SECTION:
            params = {
                'published-after': published_after,
                'published-before': published_before,
                'section-id': section_ids,
                'type': 'text,team-bio,listicle',
                'limit': min(self.PAGE_SIZE, self.ARTICLES_PER_SECTION - len(stories_to_process)),
                'offset': offset
            }
            
            try:
                response = self.session.get(self.API_SEARCH_URL, params=params, timeout=30)
                response.raise_for_status()
                
                if not response.text or response.text.strip() == '':
                    break
                
                data = response.json()
                results = data.get('results', {})
                stories = results.get('stories', [])
                
                logger.info(f"  API returned {len(stories)} stories at offset {offset}")
                
                if not stories:
                    break
                
                # Filter valid stories
                for story in stories:
                    if len(stories_to_process) >= self.ARTICLES_PER_SECTION:
                        break
                    
                    metadata = self._extract_story_metadata(story)
                    if metadata:
                        with self._lock:
                            if metadata['url'] not in self._seen_urls:
                                self._seen_urls.add(metadata['url'])
                                stories_to_process.append(metadata)
                
                offset += len(stories)
                
                if len(stories) < self.PAGE_SIZE:
                    break
                    
            except Exception as e:
                logger.error(f"  API request failed: {str(e)}")
                break
        
        logger.info(f"  Collected {len(stories_to_process)} story metadata, now fetching content in parallel...")
        
        # Step 2: Fetch content in parallel (the slow part, now parallelized!)
        articles = []
        
        with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_FETCHES) as executor:
            future_to_story = {
                executor.submit(self._fetch_and_create_article, story): story 
                for story in stories_to_process
            }
            
            for future in as_completed(future_to_story):
                try:
                    article = future.result()
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"  Failed to fetch article: {str(e)}")
        
        logger.info(f"  Section {section_ids}: Collected {len(articles)} valid articles")
        return articles
    
    def _extract_story_metadata(self, story_data: Dict) -> Optional[Dict]:
        """Extract metadata from API story data without fetching content."""
        try:
            headline = story_data.get('headline', '')
            if not headline:
                return None
            
            slug = story_data.get('slug', '')
            if not slug:
                return None
            
            # Skip non-article content
            skip_sections = ['feature/', 'features/', 'activities/', 'activity/', 'quiz/', 'games/']
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
            logger.error(f"Failed to extract story metadata: {str(e)}")
            return None
    
    def _fetch_and_create_article(self, metadata: Dict) -> Optional[ScrapedArticle]:
        """Fetch content and create ScrapedArticle from metadata."""
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
            logger.error(f"Failed to create article from {metadata['url']}: {str(e)}")
            return None
    
    def split_date_range_by_month(self) -> List[tuple]:
        """Split the date range into monthly chunks for parallel processing."""
        chunks = []
        current_start = self.start_date
        
        while current_start <= self.end_date:
            if current_start.month == 12:
                next_month = current_start.replace(year=current_start.year + 1, month=1, day=1)
            else:
                next_month = current_start.replace(month=current_start.month + 1, day=1)
            
            current_end = min(next_month - timedelta(days=1), self.end_date)
            
            chunks.append((
                current_start.strftime('%Y-%m-%d'),
                current_end.strftime('%Y-%m-%d')
            ))
            
            current_start = next_month
        
        return chunks
    
    def scrape_articles_for_date_range(self, start_date: str, end_date: str) -> List[ScrapedArticle]:
        """Scrape articles for a specific date range using API."""
        time.sleep(0.5)
        articles = []
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        published_after = int(start_dt.timestamp() * 1000)
        published_before = int(end_dt.timestamp() * 1000)
        
        logger.info(f"  Fetching from API: {start_date} to {end_date}")
        logger.info(f"  Timestamps: after={published_after}, before={published_before}")
        
        offset = 0
        max_offset = 500  # Limit to prevent infinite loops
        
        while offset < max_offset:
            params = {
                'published-after': published_after,
                'published-before': published_before,
                'limit': self.PAGE_SIZE,
                'offset': offset
            }
            
            logger.debug(f"  API request: offset={offset}, limit={self.PAGE_SIZE}")
            
            try:
                response = self.session.get(self.API_SEARCH_URL, params=params, timeout=30)
                response.raise_for_status()
                
                # Check if response has content
                if not response.text or response.text.strip() == '':
                    logger.error(f"  Empty response from API for {start_date} to {end_date}")
                    break
                
                try:
                    data = response.json()
                except ValueError as json_err:
                    logger.error(f"  JSON parse error: {json_err}")
                    logger.error(f"  Response text (first 200 chars): {response.text[:200]}")
                    break
                
                # Correct API response structure
                results = data.get('results', {})
                stories = results.get('stories', [])
                total_in_api = results.get('total', 0)
                
                logger.info(f"  API returned {len(stories)} stories at offset {offset} (total in API: {total_in_api})")
                
                if not stories:
                    logger.info(f"  No more stories found. Total articles collected: {len(articles)}")
                    break
                
                for story in stories:
                    article = self.parse_story_from_api(story)
                    if article:
                        with self._lock:
                            if article.url not in self._seen_urls:
                                self._seen_urls.add(article.url)
                                articles.append(article)
                
                offset += len(stories)
                
                if len(stories) < self.PAGE_SIZE:
                    logger.info(f"  Received fewer stories than page size, ending pagination")
                    break
                    
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"  API request failed: {str(e)}", exc_info=True)
                break
        
        logger.info(f"  Completed scraping: {len(articles)} valid articles from {offset} total API results")
        return articles
    
    def parse_story_from_api(self, story_data: Dict) -> Optional[ScrapedArticle]:
        """Parse story data from Prothom Alo API response."""
        try:
            headline = story_data.get('headline', '')
            if not headline:
                return None
            
            slug = story_data.get('slug', '')
            if not slug:
                return None
            
            # Skip problematic sections that often return 404
            # These are typically non-article content like features, activities, etc.
            skip_sections = ['feature/', 'features/', 'activities/', 'activity/', 'quiz/', 'games/']
            if any(section in slug for section in skip_sections):
                logger.debug(f"Skipping non-article content: {slug}")
                return None
            
            url = f"{self.BASE_URL}/{slug}"
            
            published_at = story_data.get('published-at') or story_data.get('first-published-at')
            if not published_at:
                return None
            
            article_date = datetime.fromtimestamp(published_at / 1000)
            
            if not self.is_within_date_range(article_date):
                return None
            
            summary = story_data.get('summary', '') or story_data.get('subheadline', '')
            full_content = self.fetch_article_content(url)
            content = full_content if full_content and len(full_content) > 100 else summary
            
            if not content or len(content) < 50:
                return None
            
            author = story_data.get('author-name', '')
            
            # Extract category
            sections = story_data.get('sections', [])
            category = 'general'
            if sections:
                category = sections[0].get('name', 'general')
            
            return ScrapedArticle(
                title=headline,
                content=content,
                url=url,
                published_date=article_date.strftime('%Y-%m-%d'),
                source="prothom_alo"
            )
            
        except Exception as e:
            logger.error(f"Failed to parse story: {str(e)}")
            return None
    
    def fetch_article_content(self, url: str) -> str:
        """Fetch full article content from article URL."""
        try:
            response = self.make_request(url)
            if not response:
                return ""
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            content_parts = []
            content_divs = soup.find_all('div', class_=['story-content', 'story-details'])
            
            for div in content_divs:
                paragraphs = div.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
            
            return ' '.join(content_parts)
            
        except Exception as e:
            logger.error(f"Failed to fetch article content from {url}: {str(e)}")
            return ""


class JugantorScraper(NewspaperScraper):
    """Scraper for Jugantor (Bangla) - Category-based scraping."""
    
    BASE_URL = "https://www.jugantor.com"
    
    # Only scrape these 4 categories
    CATEGORY_MAP = {
        '/opinion': 'মতামত',
        '/national': 'বাংলাদেশ',
        '/politics': 'রাজনীতি',
        '/international': 'বিশ্ব',
    }
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__(start_date, end_date)
        self._lock = threading.Lock()
        self._seen_urls: set = set()
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from Jugantor by category."""
        logger.info("Starting Jugantor category-based scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        
        for path, category in self.CATEGORY_MAP.items():
            try:
                articles = self._scrape_category(path, category)
                all_articles.extend(articles)
                logger.info(f"Category '{category}': {len(articles)} articles")
            except Exception as e:
                logger.error(f"Failed to scrape Jugantor category {category}: {str(e)}")
        
        logger.info(f"Jugantor: Scraped {len(all_articles)} total articles")
        return all_articles
    
    def _scrape_category(self, path: str, category: str) -> List[ScrapedArticle]:
        """Scrape articles from a category page."""
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
                
                if path in href or '/news/' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    with self._lock:
                        if full_url not in self._seen_urls and '/archive' not in full_url:
                            self._seen_urls.add(full_url)
                            article_links.append(full_url)
            
            article_links = list(set(article_links))[:50]
            
            with ThreadPoolExecutor(max_workers=2) as executor:
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
                        logger.error(f"Failed to scrape article: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to scrape Jugantor category {category}: {str(e)}")
        
        return articles
    
    def _clean_content(self, content: str) -> str:
        """Clean the content by removing unwanted parts."""
        if not content:
            return ""
        
        unwanted_patterns = [
            r'ফলো করুন.*?যুগান্তর মেসেঞ্জার',
            r'যুগান্তর প্রতিবেদন.*?পিএম',
            r'আরও পড়ুন.*?সম্পর্কিত খবর',
            r'সর্বশেষ.*?সব খবর',
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
        """Scrape individual article from Jugantor with category."""
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
                    if title:
                        break
            
            if not title:
                return None
            
            # Content extraction
            content_parts = []
            content_selectors = [
                'div.news-element-text',
                'div.content',
                'div.details',
                'div.article-content',
                'div.news-content',
                'article .content',
                '.story-content',
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
            
            # Fallback
            if not content_parts:
                article_tag = soup.find('article') or soup.find('main')
                if article_tag:
                    for p in article_tag.find_all('p'):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            content_parts.append(text)
            
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
            logger.error(f"Failed to scrape article {url}: {str(e)}")
            return None


class DailyStarScraper(NewspaperScraper):
    """Scraper for The Daily Star (Bangla) - Category-based scraping."""
    
    BASE_URL = "https://bangla.thedailystar.net"
    
    # Only scrape these 4 categories
    CATEGORY_MAP = {
        '/opinion': 'মতামত',
        '/news/bangladesh': 'বাংলাদেশ',
        '/news/bangladesh/politics': 'রাজনীতি',
        '/news/world': 'বিশ্ব',
    }
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from The Daily Star by category."""
        logger.info("Starting Daily Star category-based scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        seen_urls: set = set()
        
        for path, category in self.CATEGORY_MAP.items():
            category_url = f"{self.BASE_URL}{path}"
            logger.info(f"Scraping Daily Star category: {category} ({category_url})")
            
            try:
                articles = self._scrape_category_page(category_url, category, seen_urls)
                all_articles.extend(articles)
                logger.info(f"  Category '{category}': {len(articles)} articles")
            except Exception as e:
                logger.error(f"Failed to scrape Daily Star category {category}: {str(e)}")
            
            time.sleep(0.5)
        
        logger.info(f"Daily Star: Scraped {len(all_articles)} total articles")
        return all_articles
    
    def _scrape_category_page(self, category_url: str, category: str, seen_urls: set) -> List[ScrapedArticle]:
        """Scrape articles from a single category page."""
        articles = []
        
        try:
            response = self.make_request(category_url)
            if not response:
                return articles
            
            soup = BeautifulSoup(response.content, 'lxml')
            article_links = []
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and ('/news/' in href or '/opinion/' in href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in seen_urls and '/archive' not in full_url:
                        article_links.append(full_url)
            
            article_links = list(set(article_links))[:50]
            logger.info(f"  Found {len(article_links)} article links in {category}")
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_url = {
                    executor.submit(self._scrape_article_with_category, url, category): url
                    for url in article_links
                }
                
                for future in as_completed(future_to_url):
                    try:
                        article = future.result()
                        if article and article.url not in seen_urls:
                            seen_urls.add(article.url)
                            articles.append(article)
                    except Exception as e:
                        logger.debug(f"Failed to scrape article: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to scrape category page {category_url}: {str(e)}")
        
        return articles
    
    def _scrape_article_with_category(self, url: str, category: str) -> Optional[ScrapedArticle]:
        """Scrape individual article from Daily Star with category."""
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try multiple title selectors
            title = None
            title_selectors = ['h1.title', 'h1', '.article-title h1', '.headline']
            for selector in title_selectors:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if title:
                        break
            
            if not title:
                return None
            
            content_parts = []
            
            # Try multiple content selectors
            content_selectors = [
                'div.article-content',
                'div.article-body',
                'div.pb-article-body',
                'div.content',
                'div.story-content',
                '.article-wrapper .content',
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
            
            # Fallback: get paragraphs from article tag
            if not content_parts:
                article_tag = soup.find('article')
                if article_tag:
                    for p in article_tag.find_all('p'):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            content_parts.append(text)
            
            content = ' '.join(content_parts)
            
            if not content or len(content) < 50:
                return None
            
            # Truncate content
            if len(content) > 2000:
                content = content[:2000]
            
            # Try to get published date
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
                    published_date = None
            
            return ScrapedArticle(
                title=title,
                content=content,
                url=url,
                published_date=published_date,
                source="daily_star",
                category=category
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape Daily Star article {url}: {str(e)}")
            return None


class DhakaTribuneScraper(NewspaperScraper):
    """Scraper for Dhaka Tribune (English) - All sections."""
    
    BASE_URL = "https://www.dhakatribune.com"
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from Dhaka Tribune."""
        logger.info("Starting Dhaka Tribune scraping...")
        articles = []
        
        categories = ["bangladesh", "world", "business", "sports", "opinion"]
        
        for category in categories:
            try:
                url = f"{self.BASE_URL}/{category}"
                response = self.make_request(url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'lxml')
                article_links = []
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href and f'/{category}/' in href:
                        full_url = urljoin(self.BASE_URL, href)
                        article_links.append(full_url)
                
                article_links = list(set(article_links))[:50]
                
                for url in article_links:
                    article = self.scrape_article(url)
                    if article:
                        articles.append(article)
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Failed to scrape {category}: {str(e)}")
        
        logger.info(f"Dhaka Tribune: Scraped {len(articles)} articles")
        return articles
    
    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Scrape individual article from Dhaka Tribune."""
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else None
            if not title:
                return None
            
            content_parts = []
            content_div = soup.find('div', class_=['article-content', 'content', 'story-content'])
            
            if content_div:
                paragraphs = content_div.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
            
            content = ' '.join(content_parts)
            
            if not content or len(content) < 50:
                return None
            
            date_tag = soup.find('time')
            published_date = date_tag.get('datetime') if date_tag else None
            
            if published_date:
                try:
                    article_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    if not self.is_within_date_range(article_date):
                        return None
                    published_date = article_date.strftime('%Y-%m-%d')
                except:
                    published_date = None
            
            return ScrapedArticle(
                title=title,
                content=content,
                url=url,
                published_date=published_date,
                source="dhaka_tribune"
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape Dhaka Tribune article {url}: {str(e)}")
            return None


class SamakalScraper(NewspaperScraper):
    """Scraper for Samakal (Bangla) - Category-based scraping."""
    
    BASE_URL = "https://samakal.com"
    
    # Only scrape these 4 categories
    CATEGORY_MAP = {
        'opinion': 'মতামত',
        'bangladesh': 'বাংলাদেশ',
        'politics': 'রাজনীতি',
        'international': 'বিশ্ব',
    }
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__(start_date, end_date)
        self._lock = threading.Lock()
        self._seen_urls: set = set()
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from Samakal by category."""
        logger.info("Starting Samakal category-based scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        
        for path, category in self.CATEGORY_MAP.items():
            try:
                articles = self._scrape_category(path, category)
                all_articles.extend(articles)
                logger.info(f"Category '{category}': {len(articles)} articles")
            except Exception as e:
                logger.error(f"Failed to scrape Samakal category {category}: {str(e)}")
        
        logger.info(f"Samakal: Scraped {len(all_articles)} total articles")
        return all_articles
    
    def _scrape_category(self, path: str, category: str) -> List[ScrapedArticle]:
        """Scrape articles from a category."""
        articles = []
        
        try:
            url = f"{self.BASE_URL}/{path}"
            response = self.make_request(url)
            if not response:
                return articles
            
            soup = BeautifulSoup(response.content, 'lxml')
            article_links = []
            
            # Find article links matching category path
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and (f'/{path}/' in href or '/news/' in href):
                    full_url = urljoin(self.BASE_URL, href)
                    with self._lock:
                        if full_url not in self._seen_urls and '/page/' not in full_url:
                            self._seen_urls.add(full_url)
                            article_links.append(full_url)
            
            article_links = list(set(article_links))[:30]
            logger.info(f"  Found {len(article_links)} links for Samakal category '{category}'")
            
            for article_url in article_links:
                article = self._scrape_article(article_url, category)
                if article:
                    articles.append(article)
                time.sleep(0.3)
                
        except Exception as e:
            logger.error(f"Failed to scrape Samakal category {path}: {str(e)}")
        
        return articles
    
    def _scrape_article(self, url: str, category: str) -> Optional[ScrapedArticle]:
        """Scrape individual article from Samakal with category."""
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try multiple title selectors
            title = None
            title_selectors = ['h1.title', 'h1', 'h2.title', '.article-title', '.news-title']
            for selector in title_selectors:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if title:
                        break
            
            if not title:
                return None
            
            # Extract content
            content_parts = []
            content_selectors = [
                'div.article-content',
                'div.news-content', 
                'div.content',
                'div.post-content',
                'div.story-content',
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
            
            # Fallback
            if not content_parts:
                main_content = soup.find('article') or soup.find('main')
                if main_content:
                    for p in main_content.find_all('p'):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            content_parts.append(text)
            
            content = ' '.join(content_parts)
            
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
                source="samakal",
                category=category
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape Samakal article {url}: {str(e)}")
            return None


class NewsScraper:
    """Main scraper class that coordinates all newspaper scrapers."""
    
    def __init__(self):
        """Initialize the main scraper."""
        pass
    
    async def scrape_articles(
        self,
        source: str,
        start_date: date,
        end_date: date
    ) -> List[ScrapedArticle]:
        """
        Scrape articles from specified source within date range.
        
        Args:
            source: Newspaper source (prothom_alo, jugantor, daily_star, dhaka_tribune, samakal)
            start_date: Start date for scraping
            end_date: End date for scraping
        
        Returns:
            List of scraped articles
        """
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        scraper_map = {
            "prothom_alo": ProthomAloScraper,
            "jugantor": JugantorScraper,
            "daily_star": DailyStarScraper,
            "dhaka_tribune": DhakaTribuneScraper,
            "samakal": SamakalScraper
        }
        
        scraper_class = scraper_map.get(source)
        if not scraper_class:
            logger.error(f"Unknown source: {source}")
            return []
        
        try:
            loop = asyncio.get_event_loop()
            scraper = scraper_class(start_str, end_str)
            articles = await loop.run_in_executor(None, scraper.scrape_articles)
            
            logger.info(f"Scraped {len(articles)} articles from {source}")
            return articles
            
        except Exception as e:
            logger.error(f"Scraping failed for {source}: {str(e)}")
            return []
