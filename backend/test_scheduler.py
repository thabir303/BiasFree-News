#!/usr/bin/env python3
"""
Scheduler diagnostic tool to check status and performance issues.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.database.models import Article, SchedulerLog, Base
from app.services.scheduler import get_scheduler
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_scheduler_status():
    """Check if scheduler is running and working correctly."""
    print("🔍 Checking Scheduler Status...")
    
    # Get scheduler instance
    scheduler = get_scheduler()
    
    print(f"✅ Scheduler initialized: {scheduler is not None}")
    print(f"✅ Scheduler running: {scheduler._is_running}")
    
    if scheduler.scheduler.running:
        print(f"✅ APScheduler running: True")
        jobs = scheduler.scheduler.get_jobs()
        print(f"📋 Active jobs: {len(jobs)}")
        
        for job in jobs:
            print(f"   - Job ID: {job.id}")
            print(f"   - Next run: {job.next_run_time}")
            print(f"   - Trigger: {job.trigger}")
    else:
        print("❌ APScheduler not running")
    
    return scheduler

async def check_recent_scheduler_logs():
    """Check recent scheduler execution logs."""
    print("\n📊 Checking Recent Scheduler Logs...")
    
    # Create database session
    from app.database.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get logs from last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_logs = db.query(SchedulerLog).filter(
            SchedulerLog.started_at >= seven_days_ago
        ).order_by(SchedulerLog.started_at.desc()).limit(10).all()
        
        if recent_logs:
            print(f"📈 Found {len(recent_logs)} recent scheduler logs:")
            for log in recent_logs:
                print(f"   📅 {log.started_at.strftime('%Y-%m-%d %H:%M:%S')} - {log.job_name}")
                print(f"      Status: {log.status}")
                print(f"      Articles scraped: {log.articles_scraped or 0}")
                print(f"      Articles processed: {log.articles_processed or 0}")
                if log.errors:
                    print(f"      Errors: {len(log.errors)} items")
                print()
        else:
            print("⚠️  No recent scheduler logs found")
            
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
    finally:
        db.close()

async def check_article_statistics():
    """Check article scraping and processing statistics."""
    print("📈 Checking Article Statistics...")
    
    from app.database.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Total articles
        total_articles = db.query(Article).count()
        print(f"📚 Total articles in database: {total_articles}")
        
        # Articles by source
        from sqlalchemy import func
        source_stats = db.query(
            Article.source,
            func.count(Article.id).label('count')
        ).group_by(Article.source).all()
        
        print("📰 Articles by source:")
        for source, count in source_stats:
            print(f"   - {source}: {count} articles")
        
        # Processing status
        processed_count = db.query(Article).filter(Article.processed == True).count()
        unprocessed_count = db.query(Article).filter(Article.processed == False).count()
        
        print(f"✅ Processed articles: {processed_count}")
        print(f"⏳ Unprocessed articles: {unprocessed_count}")
        
        # Recent articles (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_articles = db.query(Article).filter(
            Article.scraped_at >= seven_days_ago
        ).count()
        
        print(f"📅 Articles scraped in last 7 days: {recent_articles}")
        
    except Exception as e:
        print(f"❌ Error checking statistics: {e}")
    finally:
        db.close()

async def test_manual_scraping():
    """Test manual scraping for a single day to check performance."""
    print("\n🧪 Testing Manual Scraping Performance...")
    
    from app.services.enhanced_scraper import EnhancedNewsScraper
    from app.database.database import SessionLocal
    from datetime import date
    
    db = SessionLocal()
    
    try:
        scraper = EnhancedNewsScraper(db)
        today = date.today()
        
        # Test scraping for a single source
        start_time = datetime.now()
        
        stats = await scraper.scrape_and_store(
            source="prothom_alo",
            start_date=today,
            end_date=today
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"⏱️  Prothom Alo scraping took: {duration:.2f} seconds")
        print(f"📊 Results:")
        print(f"   - Total scraped: {stats['total_scraped']}")
        print(f"   - New articles: {stats['new_articles']}")
        print(f"   - Duplicates: {stats['duplicates']}")
        print(f"   - Errors: {len(stats['errors'])}")
        
        if stats['errors']:
            print(f"   ❌ Errors: {stats['errors'][:3]}...")  # Show first 3 errors
            
    except Exception as e:
        print(f"❌ Error during test scraping: {e}")
    finally:
        db.close()

def analyze_performance_bottlenecks():
    """Analyze common performance bottlenecks in scraping."""
    print("\n🔍 Analyzing Performance Bottlenecks...")
    
    print("\n⚠️  Common Issues Identified:")
    print("1. 🐌 Sequential processing instead of parallel")
    print("2. 🕰️  Excessive delays between requests")
    print("3. 📄 Too many unnecessary HTTP requests")
    print("4. 🧹 Inefficient content cleaning")
    print("5. 🔄 Redundant database queries")
    print("6. 📝 Over-logging during scraping")
    
    print("\n💡 Optimization Suggestions:")
    print("• Use asyncio.gather() for parallel scraping")
    print("• Reduce time.sleep() delays (0.5s → 0.1s)")
    print("• Cache duplicate URL checks")
    print("• Batch database operations")
    print("• Implement request session pooling")
    print("• Use connection pooling for database")

async def main():
    """Main diagnostic function."""
    print("🚀 BiasFree News Scheduler & Performance Diagnostic")
    print("=" * 60)
    
    # Check scheduler status
    scheduler = await check_scheduler_status()
    
    # Check recent logs
    await check_recent_scheduler_logs()
    
    # Check article statistics
    await check_article_statistics()
    
    # Test manual scraping (optional - uncomment if needed)
    # await test_manual_scraping()
    
    # Analyze performance bottlenecks
    analyze_performance_bottlenecks()
    
    print("\n✅ Diagnostic complete!")
    print("\n📝 Next Steps:")
    print("1. Check the optimization suggestions above")
    print("2. Review scheduler logs for specific errors")
    print("3. Consider implementing parallel scraping")
    print("4. Monitor performance after optimizations")

if __name__ == "__main__":
    asyncio.run(main())