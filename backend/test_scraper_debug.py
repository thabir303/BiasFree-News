"""
Quick test script to debug Prothom Alo and Jugantor scraping
"""
import sys
import logging
from datetime import datetime
from app.services.optimized_scraper import OptimizedProthomAloScraper, OptimizedJugantorScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_prothom_alo():
    """Test Prothom Alo scraping"""
    print("\n" + "="*80)
    print("TESTING PROTHOM ALO SCRAPER")
    print("="*80)
    
    today = datetime.now().strftime('%Y-%m-%d')
    scraper = OptimizedProthomAloScraper(start_date=today, end_date=today)
    
    # Test with single section
    print(f"\nScraping single section (22237 - Politics) for {today}...")
    articles = scraper.scrape_articles(section_ids=['22237'])
    
    print(f"\n✅ Results: {len(articles)} articles scraped")
    if articles:
        print(f"\nSample article:")
        article = articles[0]
        print(f"  Title: {article.title[:100]}...")
        print(f"  URL: {article.url}")
        print(f"  Content length: {len(article.content)} chars")
        print(f"  Content preview: {article.content[:200]}...")
    else:
        print("❌ No articles found!")
    
    return len(articles) > 0

def test_jugantor():
    """Test Jugantor scraping"""
    print("\n" + "="*80)
    print("TESTING JUGANTOR SCRAPER")
    print("="*80)
    
    today = datetime.now().strftime('%Y-%m-%d')
    scraper = OptimizedJugantorScraper(start_date=today, end_date=today)
    
    print(f"\nScraping Jugantor for {today}...")
    articles = scraper.scrape_articles()
    
    print(f"\n✅ Results: {len(articles)} articles scraped")
    if articles:
        print(f"\nSample article:")
        article = articles[0]
        print(f"  Title: {article.title[:100]}...")
        print(f"  URL: {article.url}")
        print(f"  Content length: {len(article.content)} chars")
        print(f"  Content preview: {article.content[:200]}...")
    else:
        print("❌ No articles found!")
    
    return len(articles) > 0

if __name__ == "__main__":
    print("\n🔍 SCRAPER DEBUG TEST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    pa_success = test_prothom_alo()
    jug_success = test_jugantor()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Prothom Alo: {'✅ SUCCESS' if pa_success else '❌ FAILED'}")
    print(f"Jugantor: {'✅ SUCCESS' if jug_success else '❌ FAILED'}")
    print("="*80 + "\n")
    
    sys.exit(0 if (pa_success and jug_success) else 1)
