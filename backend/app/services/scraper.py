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
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__(start_date, end_date)
        self._lock = threading.Lock()
        self._seen_urls = set()
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from Prothom Alo using search API."""
        logger.info("Starting Prothom Alo scraping (All sections)...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        date_chunks = self.split_date_range_by_month()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_chunk = {
                executor.submit(self.scrape_articles_for_date_range, start, end): (start, end) 
                for start, end in date_chunks
            }
            
            for future in as_completed(future_to_chunk):
                start, end = future_to_chunk[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(f"Completed {start} to {end}: {len(articles)} articles")
                except Exception as e:
                    logger.error(f"Failed {start} to {end}: {str(e)}")
        
        logger.info(f"Prothom Alo: Scraped {len(all_articles)} total articles")
        return all_articles
    
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
    """Scraper for Jugantor (Bangla) - All categories using archive system."""
    
    BASE_URL = "https://www.jugantor.com"
    ARCHIVE_BASE_URL = "https://www.jugantor.com/archive"
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__(start_date, end_date)
        self._lock = threading.Lock()
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from Jugantor archive for all categories."""
        logger.info("Starting Jugantor archive scraping (All categories)...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        dates_to_scrape = []
        current_date = self.start_date
        
        while current_date <= self.end_date:
            dates_to_scrape.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        logger.info(f"Total dates to scrape: {len(dates_to_scrape)}")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_date = {
                executor.submit(self.scrape_articles_for_date, date): date 
                for date in dates_to_scrape
            }
            
            for future in as_completed(future_to_date):
                date = future_to_date[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(f"Completed {date}: {len(articles)} articles")
                except Exception as e:
                    logger.error(f"Failed {date}: {str(e)}")
        
        logger.info(f"Jugantor: Scraped {len(all_articles)} total articles")
        return all_articles
    
    def get_archive_url(self, date: str, page: int = None) -> str:
        """Generate archive URL for a specific date and page."""
        # Jugantor archive format: /archive?date=YYYY-MM-DD
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
            
            # Look for article links in archive
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
                    # Avoid duplicate and non-article links
                    if '/archive' not in full_url and full_url not in article_links:
                        article_links.append(full_url)
            
            return list(set(article_links))
            
        except Exception as e:
            logger.error(f"Failed to extract links from {archive_url}: {str(e)}")
            return []
    
    def scrape_articles_for_date(self, date: str) -> List[ScrapedArticle]:
        """Scrape all articles for a specific date."""
        all_articles = []
        page = 1
        max_pages = 50
        
        all_article_urls = []
        
        while page <= max_pages:
            archive_url = self.get_archive_url(date, page)
            article_urls = self.extract_article_links(archive_url)
            
            if not article_urls:
                break
            
            all_article_urls.extend(article_urls)
            page += 1
            time.sleep(0.5)
        
        if not all_article_urls:
            return []
        
        logger.info(f"  Total article URLs for {date}: {len(all_article_urls)}")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
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
                    logger.error(f"Failed to scrape article: {str(e)}")
        
        return all_articles
    
    def clean_content(self, content: str) -> str:
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
            r'যুগান্তর.*?হোয়াটসঅ্যাপ.*?মেসেঞ্জার',
        ]
        
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        if "মেসেঞ্জার" in content[:200]:
            parts = content.split("মেসেঞ্জার", 1)
            if len(parts) > 1:
                content = parts[1]
        
        if "সম্পর্কিত খবর" in content:
            content = content.split("সম্পর্কিত খবর")[0]
        
        content = re.sub(r'\n+', '\n', content)
        content = re.sub(r' +', ' ', content)
        
        return content.strip()
    
    def scrape_article(self, url: str, date: str) -> Optional[ScrapedArticle]:
        """Scrape individual article from Jugantor."""
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try multiple selectors for title
            title = None
            title_selectors = ['h1', 'h1.title', '.headline h1', '.news-title', '.article-title']
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
                'div.news-element-text',
                'div.content',
                'div.details',
                'div.article-content',
                'div.news-content',
                'article .content',
                '.story-content',
                '.news-details'
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
            
            # Fallback: get all paragraphs from main article area
            if not content_parts:
                article_tag = soup.find('article') or soup.find('main') or soup.find('div', id='content')
                if article_tag:
                    for p in article_tag.find_all('p'):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            content_parts.append(text)
            
            content = ' '.join(content_parts)
            content = self.clean_content(content)
            
            if not content or len(content) < 50:
                logger.debug(f"Content too short for {url}: {len(content) if content else 0} chars")
                return None
            
            return ScrapedArticle(
                title=title,
                content=content,
                url=url,
                published_date=date,
                source="jugantor"
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape article {url}: {str(e)}")
            return None


class DailyStarScraper(NewspaperScraper):
    """Scraper for The Daily Star (English) - All sections."""
    
    BASE_URL = "https://www.thedailystar.net"
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from The Daily Star using archive."""
        logger.info("Starting Daily Star scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        
        # Scrape from archive for each date
        current_date = self.start_date
        while current_date <= self.end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            articles = self.scrape_archive_for_date(date_str)
            all_articles.extend(articles)
            logger.info(f"Completed {date_str}: {len(articles)} articles")
            current_date += timedelta(days=1)
            time.sleep(0.5)
        
        # Also scrape from category pages for more articles
        category_urls = [
            f"{self.BASE_URL}/news/bangladesh",
            f"{self.BASE_URL}/news/politics",
            f"{self.BASE_URL}/opinion",
            f"{self.BASE_URL}/business",
        ]
        
        for category_url in category_urls:
            try:
                response = self.make_request(category_url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'lxml')
                article_links = []
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href and ('/news/' in href or '/opinion/' in href or '/business/' in href):
                        full_url = urljoin(self.BASE_URL, href)
                        if full_url not in [a.url for a in all_articles]:
                            article_links.append(full_url)
                
                article_links = list(set(article_links))[:30]
                
                for url in article_links:
                    article = self.scrape_article(url)
                    if article:
                        all_articles.append(article)
                    time.sleep(0.3)
                    
            except Exception as e:
                logger.error(f"Failed to scrape {category_url}: {str(e)}")
        
        logger.info(f"Daily Star: Scraped {len(all_articles)} articles")
        return all_articles
    
    def scrape_archive_for_date(self, date_str: str) -> List[ScrapedArticle]:
        """Scrape articles from archive for a specific date."""
        articles = []
        
        # Daily Star archive URL format
        archive_url = f"{self.BASE_URL}/todays-news?date={date_str}"
        
        try:
            response = self.make_request(archive_url)
            if not response:
                return articles
            
            soup = BeautifulSoup(response.content, 'lxml')
            article_links = []
            
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and '/news/' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    article_links.append(full_url)
            
            article_links = list(set(article_links))[:50]
            
            for url in article_links:
                article = self.scrape_article(url)
                if article:
                    articles.append(article)
                time.sleep(0.3)
                
        except Exception as e:
            logger.error(f"Failed to scrape Daily Star archive for {date_str}: {str(e)}")
        
        return articles
    
    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Scrape individual article from Daily Star."""
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
            
            # Try to get published date
            date_tag = soup.find('time')
            published_date = None
            
            if date_tag:
                published_date = date_tag.get('datetime')
            
            if not published_date:
                # Try meta tag
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
                source="daily_star"
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
    """Scraper for Samakal (Bangla) - All sections."""
    
    BASE_URL = "https://samakal.com"
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__(start_date, end_date)
        self._lock = threading.Lock()
    
    def scrape_articles(self) -> List[ScrapedArticle]:
        """Scrape articles from Samakal."""
        logger.info("Starting Samakal scraping...")
        logger.info(f"Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_articles = []
        
        # Scrape from main category pages
        categories = [
            'bangladesh', 'politics', 'economics', 'international',
            'sports', 'entertainment', 'opinion', 'lifestyle'
        ]
        
        for category in categories:
            try:
                articles = self.scrape_category(category)
                all_articles.extend(articles)
                logger.info(f"Category {category}: {len(articles)} articles")
            except Exception as e:
                logger.error(f"Failed to scrape Samakal category {category}: {str(e)}")
        
        logger.info(f"Samakal: Scraped {len(all_articles)} total articles")
        return all_articles
    
    def scrape_category(self, category: str) -> List[ScrapedArticle]:
        """Scrape articles from a category."""
        articles = []
        
        try:
            url = f"{self.BASE_URL}/{category}"
            response = self.make_request(url)
            if not response:
                return articles
            
            soup = BeautifulSoup(response.content, 'lxml')
            article_links = []
            
            # Find article links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and f'/{category}/' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in article_links and '/page/' not in full_url:
                        article_links.append(full_url)
            
            # Also look for general news links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and '/news/' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in article_links:
                        article_links.append(full_url)
            
            article_links = list(set(article_links))[:30]
            
            for url in article_links:
                article = self.scrape_article(url)
                if article:
                    articles.append(article)
                time.sleep(0.3)
                
        except Exception as e:
            logger.error(f"Failed to scrape Samakal category {category}: {str(e)}")
        
        return articles
    
    def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Scrape individual article from Samakal."""
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
            
            # Fallback: try finding paragraphs in main content area
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
            
            # Try to extract date from article
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
                source="samakal"
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
