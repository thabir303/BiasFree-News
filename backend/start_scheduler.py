#!/usr/bin/env python3
"""
Manual scheduler startup script.
"""
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def start_scheduler():
    """Manually start the scheduler."""
    print("🚀 Starting BiasFree News Scheduler...")
    
    try:
        # Import required modules
        from app.services.scheduler import get_scheduler
        from app.config import settings
        
        print(f"📋 Environment: {settings.environment}")
        print(f"⏰ Current time: {datetime.now()}")
        print(f"📊 Rate limit: {settings.rate_limit_per_minute} requests/minute")
        
        # Get scheduler instance
        scheduler = get_scheduler()
        print(f"✅ Scheduler instance created: {scheduler is not None}")
        
        # Check if already running
        if scheduler._is_running:
            print("⚠️  Scheduler is already running")
            jobs = scheduler.scheduler.get_jobs()
            print(f"📋 Active jobs: {len(jobs)}")
            for job in jobs:
                print(f"   - {job.id}: {job.name} (Next: {job.next_run_time})")
            return
        
        # Start the scheduler
        print("🔄 Starting scheduler...")
        scheduler.start()
        
        # Verify it's running
        if scheduler._is_running:
            print("✅ Scheduler started successfully")
            jobs = scheduler.scheduler.get_jobs()
            print(f"📋 Active jobs: {len(jobs)}")
            for job in jobs:
                print(f"   - {job.id}: {job.name} (Next: {job.next_run_time})")
        else:
            print("❌ Failed to start scheduler")
            
    except Exception as e:
        print(f"❌ Error starting scheduler: {e}")
        import traceback
        traceback.print_exc()

def test_scraping():
    """Test manual scraping."""
    print("\n🧪 Testing Manual Scraping...")
    
    try:
        from datetime import date
        from app.services.enhanced_scraper import EnhancedNewsScraper
        from app.database.database import SessionLocal
        
        db = SessionLocal()
        scraper = EnhancedNewsScraper(db)
        
        today = date.today()
        print(f"📅 Testing scraping for today: {today}")
        
        # Test with a single newspaper
        result = asyncio.run(scraper.scrape_and_store(
            source="prothom_alo",
            start_date=today,
            end_date=today
        ))
        
        print(f"✅ Scraping test completed")
        print(f"📊 Results:")
        print(f"   - Total scraped: {result['total_scraped']}")
        print(f"   - New articles: {result['new_articles']}")
        print(f"   - Duplicates: {result['duplicates']}")
        print(f"   - Errors: {len(result['errors'])}")
        
        if result['errors']:
            print(f"⚠️  Errors encountered: {result['errors'][:2]}")
            
        db.close()
        
    except Exception as e:
        print(f"❌ Error during scraping test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function."""
    print("🔧 BiasFree News Manual Scheduler Control")
    print("=" * 50)
    
    # Start scheduler
    await start_scheduler()
    
    # Test scraping
    test_scraping()
    
    print("\n✅ Manual control completed")
    print("\n💡 Tips:")
    print("• Scheduler will run daily at 6 AM Bangladesh time")
    print("• Check logs for scraping activity")
    print("• Monitor database for new articles")
    print("• Use verify_scheduler.py for health checks")

if __name__ == "__main__":
    asyncio.run(main())