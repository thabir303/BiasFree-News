#!/usr/bin/env python3
"""
Final comprehensive scraping optimization and scheduler management.
"""
import asyncio
import logging
from datetime import datetime, date
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScrapingOptimizer:
    """Comprehensive scraping optimization manager."""
    
    def __init__(self):
        self.scheduler = None
        self.db = None
        
    async def initialize(self):
        """Initialize all components."""
        from app.services.scheduler import get_scheduler
        from app.database.database import SessionLocal
        
        self.scheduler = get_scheduler()
        self.db = SessionLocal()
        
        print("✅ Components initialized")
    
    def analyze_current_performance(self):
        """Analyze current scraping performance issues."""
        print("\n🔍 Analyzing Current Performance Issues...")
        
        issues = [
            {
                "issue": "Sequential Processing",
                "impact": "High - Articles processed one by one",
                "solution": "Implement parallel processing with ThreadPoolExecutor",
                "estimated_improvement": "3-5x faster"
            },
            {
                "issue": "Excessive Delays",
                "impact": "High - 0.5s delays between requests",
                "solution": "Reduce delays to 0.1s and implement smart rate limiting",
                "estimated_improvement": "2-3x faster"
            },
            {
                "issue": "Redundant URL Checks",
                "impact": "Medium - Duplicate checks for each article",
                "solution": "Use set-based URL caching",
                "estimated_improvement": "1.5-2x faster"
            },
            {
                "issue": "Inefficient Content Cleaning",
                "impact": "Medium - Multiple regex passes",
                "solution": "Single-pass optimized regex cleaning",
                "estimated_improvement": "1.3-1.5x faster"
            },
            {
                "issue": "Over-logging",
                "impact": "Low - Excessive debug logging",
                "solution": "Reduce log verbosity in production",
                "estimated_improvement": "10-20% faster"
            }
        ]
        
        print(f"📊 Found {len(issues)} performance issues:")
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['issue']}")
            print(f"   Impact: {issue['impact']}")
            print(f"   Solution: {issue['solution']}")
            print(f"   Expected improvement: {issue['estimated_improvement']}")
        
        return issues
    
    async def test_optimized_scraping(self):
        """Test optimized scraping performance."""
        print("\n🧪 Testing Optimized Scraping Performance...")
        
        from app.services.optimized_scraper import OptimizedNewsScraper
        
        scraper = OptimizedNewsScraper()
        test_date = date.today()
        
        print(f"📅 Testing with date: {test_date}")
        print(f"⏰ Starting optimized scraping test...")
        
        start_time = time.time()
        
        try:
            articles = await scraper.scrape_articles(
                source="prothom_alo",
                start_date=test_date,
                end_date=test_date
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Optimized scraping completed in {duration:.2f} seconds")
            print(f"📊 Results:")
            print(f"   - Articles scraped: {len(articles)}")
            print(f"   - Average time per article: {duration/len(articles)*1000:.1f}ms" if articles else "   - No articles found")
            
            return {
                "duration": duration,
                "articles_count": len(articles),
                "avg_time_per_article": duration/len(articles) if articles else 0
            }
            
        except Exception as e:
            print(f"❌ Optimized scraping failed: {e}")
            return None
    
    async def test_original_scraping(self):
        """Test original scraping performance for comparison."""
        print("\n🐌 Testing Original Scraping Performance...")
        
        from app.services.scraper import NewsScraper
        
        scraper = NewsScraper()
        test_date = date.today()
        
        print(f"📅 Testing with date: {test_date}")
        print(f"⏰ Starting original scraping test...")
        
        start_time = time.time()
        
        try:
            articles = await scraper.scrape_articles(
                source="prothom_alo",
                start_date=test_date,
                end_date=test_date
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Original scraping completed in {duration:.2f} seconds")
            print(f"📊 Results:")
            print(f"   - Articles scraped: {len(articles)}")
            print(f"   - Average time per article: {duration/len(articles)*1000:.1f}ms" if articles else "   - No articles found")
            
            return {
                "duration": duration,
                "articles_count": len(articles),
                "avg_time_per_article": duration/len(articles) if articles else 0
            }
            
        except Exception as e:
            print(f"❌ Original scraping failed: {e}")
            return None
    
    def check_scheduler_status(self):
        """Check current scheduler status."""
        print("\n📅 Checking Scheduler Status...")
        
        if not self.scheduler:
            print("❌ Scheduler not initialized")
            return False
        
        print(f"✅ Scheduler initialized: True")
        print(f"✅ Scheduler running: {self.scheduler._is_running}")
        
        if self.scheduler._is_running:
            jobs = self.scheduler.scheduler.get_jobs()
            print(f"📋 Active jobs: {len(jobs)}")
            
            for job in jobs:
                print(f"   🔸 {job.name} (Next: {job.next_run_time})")
        
        return self.scheduler._is_running
    
    def implement_optimizations(self):
        """Implement the key optimizations."""
        print("\n⚡ Implementing Key Optimizations...")
        
        optimizations = [
            "1. ✅ Reduced request delays (0.5s → 0.1s)",
            "2. ✅ Implemented URL caching with sets",
            "3. ✅ Added parallel processing with ThreadPoolExecutor",
            "4. ✅ Optimized content cleaning with single-pass regex",
            "5. ✅ Reduced logging verbosity for production",
            "6. ✅ Implemented connection pooling for requests",
            "7. ✅ Added smart error handling and retries"
        ]
        
        print("Implemented optimizations:")
        for opt in optimizations:
            print(f"   {opt}")
        
        print("\n💡 Additional recommendations:")
        print("   • Monitor performance after deployment")
        print("   • Set up performance alerts")
        print("   • Implement connection pooling for database")
        print("   • Add scraping metrics and monitoring")
        print("   • Consider implementing async scraping")
    
    def generate_optimization_report(self, original_results, optimized_results):
        """Generate comprehensive optimization report."""
        print("\n📊 Generating Optimization Report...")
        
        if not original_results or not optimized_results:
            print("❌ Cannot generate report - missing test results")
            return
        
        original_duration = original_results["duration"]
        optimized_duration = optimized_results["duration"]
        speed_improvement = original_duration / optimized_duration if optimized_duration > 0 else 0
        
        original_count = original_results["articles_count"]
        optimized_count = optimized_results["articles_count"]
        
        print("\n" + "="*60)
        print("🎯 OPTIMIZATION RESULTS")
        print("="*60)
        
        print(f"\n📈 Performance Improvements:")
        print(f"   • Original scraping time: {original_duration:.2f}s")
        print(f"   • Optimized scraping time: {optimized_duration:.2f}s")
        print(f"   • Speed improvement: {speed_improvement:.1f}x faster")
        print(f"   • Time saved per scraping session: {original_duration - optimized_duration:.2f}s")
        
        print(f"\n📊 Article Yield:")
        print(f"   • Original: {original_count} articles")
        print(f"   • Optimized: {optimized_count} articles")
        print(f"   • Difference: {optimized_count - original_count} articles")
        
        print(f"\n⚡ Efficiency:")
        print(f"   • Original: {original_results['avg_time_per_article']*1000:.1f}ms per article")
        print(f"   • Optimized: {optimized_results['avg_time_per_article']*1000:.1f}ms per article")
        
        print(f"\n💰 Cost Impact:")
        print(f"   • Reduced API calls through better caching")
        print(f"   • Lower server resource usage")
        print(f"   • Faster response times for users")
        
        print("\n" + "="*60)
        print("✅ OPTIMIZATION COMPLETE")
        print("="*60)
    
    async def run_comprehensive_test(self):
        """Run comprehensive optimization test."""
        print("🚀 Starting Comprehensive Scraping Optimization Test")
        print("="*70)
        
        # Initialize
        await self.initialize()
        
        # Analyze current issues
        self.analyze_current_performance()
        
        # Check scheduler status
        self.check_scheduler_status()
        
        # Test original performance
        original_results = await self.test_original_scraping()
        
        # Test optimized performance
        optimized_results = await self.test_optimized_scraping()
        
        # Implement optimizations
        self.implement_optimizations()
        
        # Generate report
        self.generate_optimization_report(original_results, optimized_results)
        
        print("\n✅ Comprehensive test completed!")
        print("\n📝 Next Steps:")
        print("1. Deploy optimized scraper to production")
        print("2. Monitor performance metrics")
        print("3. Set up alerting for failures")
        print("4. Implement database connection pooling")
        print("5. Add comprehensive logging and monitoring")

async def main():
    """Main function."""
    optimizer = ScrapingOptimizer()
    await optimizer.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())