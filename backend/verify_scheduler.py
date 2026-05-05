#!/usr/bin/env python3
"""
Comprehensive scheduler verification and management tool.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from app.database.database import SessionLocal
from app.database.models import SchedulerLog, Article
from app.services.scheduler import get_scheduler
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerManager:
    """Scheduler management and verification utility."""
    
    def __init__(self):
        self.scheduler = get_scheduler()
        self.db = SessionLocal()
    
    def check_scheduler_dependencies(self):
        """Check if all scheduler dependencies are properly installed."""
        print("🔍 Checking Scheduler Dependencies...")
        
        dependencies = {
            'apscheduler': 'APScheduler for task scheduling',
            'sqlalchemy': 'SQLAlchemy for database operations',
            'asyncio': 'AsyncIO for async operations',
            'datetime': 'DateTime for time management'
        }
        
        missing_deps = []
        
        for dep, description in dependencies.items():
            try:
                if dep == 'apscheduler':
                    import apscheduler
                    from apscheduler.schedulers.asyncio import AsyncIOScheduler
                    from apscheduler.triggers.cron import CronTrigger
                    print(f"✅ {dep}: {description} - Available")
                elif dep == 'sqlalchemy':
                    import sqlalchemy
                    from sqlalchemy.orm import Session
                    print(f"✅ {dep}: {description} - Available")
                else:
                    __import__(dep)
                    print(f"✅ {dep}: {description} - Available")
            except ImportError:
                print(f"❌ {dep}: {description} - Missing")
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"\n⚠️  Missing dependencies: {missing_deps}")
            return False
        
        print("✅ All dependencies are available!")
        return True
    
    def check_scheduler_status(self):
        """Check current scheduler status."""
        print("\n📊 Checking Scheduler Status...")
        
        if not self.scheduler:
            print("❌ Scheduler not initialized")
            return False
        
        print(f"✅ Scheduler initialized: True")
        print(f"✅ Scheduler running: {self.scheduler._is_running}")
        
        if hasattr(self.scheduler, 'scheduler'):
            print(f"✅ APScheduler instance: Available")
            print(f"✅ APScheduler running: {self.scheduler.scheduler.running}")
            
            jobs = self.scheduler.scheduler.get_jobs()
            print(f"📋 Active jobs: {len(jobs)}")
            
            if jobs:
                print("\n📅 Scheduled Jobs:")
                for job in jobs:
                    print(f"   🔸 Job ID: {job.id}")
                    print(f"   🔸 Name: {job.name}")
                    print(f"   🔸 Next run: {job.next_run_time}")
                    print(f"   🔸 Trigger: {job.trigger}")
                    print(f"   🔸 Coalesce: {getattr(job, 'coalesce', 'N/A')}")
                    print(f"   🔸 Max instances: {getattr(job, 'max_instances', 'N/A')}")
                    print()
            else:
                print("⚠️  No scheduled jobs found")
        else:
            print("❌ APScheduler instance not available")
            return False
        
        return True
    
    def check_database_tables(self):
        """Check if required database tables exist."""
        print("\n🗄️  Checking Database Tables...")
        
        try:
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(self.db.bind)
            
            tables = inspector.get_table_names()
            print(f"📋 Available tables: {tables}")
            
            required_tables = ['articles', 'scheduler_logs']
            missing_tables = []
            
            for table in required_tables:
                if table in tables:
                    print(f"✅ {table} table: Available")
                    
                    # Check row count
                    if table == 'articles':
                        count = self.db.query(Article).count()
                        print(f"   📊 Row count: {count}")
                    elif table == 'scheduler_logs':
                        count = self.db.query(SchedulerLog).count()
                        print(f"   📊 Row count: {count}")
                else:
                    print(f"❌ {table} table: Missing")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"\n⚠️  Missing tables: {missing_tables}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            return False
    
    def check_recent_scheduler_activity(self, days: int = 7):
        """Check recent scheduler activity and performance."""
        print(f"\n📈 Checking Recent Scheduler Activity (Last {days} days)...")
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent logs
            recent_logs = self.db.query(SchedulerLog).filter(
                SchedulerLog.started_at >= cutoff_date
            ).order_by(SchedulerLog.started_at.desc()).all()
            
            if not recent_logs:
                print("⚠️  No recent scheduler activity found")
                return False
            
            print(f"📊 Found {len(recent_logs)} scheduler runs in last {days} days")
            
            # Analyze performance
            total_articles_scraped = sum(log.articles_scraped or 0 for log in recent_logs)
            total_articles_processed = sum(log.articles_processed or 0 for log in recent_logs)
            successful_runs = sum(1 for log in recent_logs if log.status == 'success')
            failed_runs = sum(1 for log in recent_logs if log.status == 'failed')
            
            print(f"✅ Successful runs: {successful_runs}")
            print(f"❌ Failed runs: {failed_runs}")
            print(f"📚 Total articles scraped: {total_articles_scraped}")
            print(f"⚡ Total articles processed: {total_articles_processed}")
            
            if successful_runs > 0:
                avg_scraped = total_articles_scraped / successful_runs
                avg_processed = total_articles_processed / successful_runs
                print(f"📊 Average per successful run:")
                print(f"   - Articles scraped: {avg_scraped:.1f}")
                print(f"   - Articles processed: {avg_processed:.1f}")
            
            # Show recent runs
            print(f"\n📅 Recent Scheduler Runs:")
            for log in recent_logs[:5]:  # Show last 5 runs
                duration = "N/A"
                if log.completed_at and log.started_at:
                    duration = f"{(log.completed_at - log.started_at).total_seconds() / 60:.1f}min"
                
                print(f"   📋 {log.started_at.strftime('%Y-%m-%d %H:%M:%S')} - {log.job_name}")
                print(f"      Status: {log.status} | Duration: {duration}")
                print(f"      Scraped: {log.articles_scraped or 0} | Processed: {log.articles_processed or 0}")
                if log.errors:
                    print(f"      Errors: {len(log.errors)} items")
                print()
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking recent activity: {e}")
            return False
    
    def test_manual_scheduler_run(self):
        """Test manual scheduler execution."""
        print("\n🧪 Testing Manual Scheduler Run...")
        
        try:
            # Run manual scraping for today
            from datetime import date
            
            print("🔄 Starting manual scheduler test...")
            start_time = datetime.utcnow()
            
            # Trigger manual scraping
            result = asyncio.run(self.scheduler.run_manual_scraping(
                sources=None,  # All enabled sources
                start_date=date.today(),
                end_date=date.today()
            ))
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Manual scheduler test completed in {duration:.1f} seconds")
            print(f"📊 Results:")
            print(f"   - Total scraped: {result.get('total_scraped', 0)}")
            print(f"   - Total processed: {result.get('total_processed', 0)}")
            
            if result.get('errors'):
                print(f"   ⚠️  Errors: {len(result.get('errors', []))}")
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"      - {error}")
            
            return True
            
        except Exception as e:
            print(f"❌ Manual scheduler test failed: {e}")
            return False
    
    def verify_scheduler_configuration(self):
        """Verify scheduler configuration."""
        print("\n⚙️  Verifying Scheduler Configuration...")
        
        # Check timezone configuration
        print(f"🌍 Environment: {settings.environment}")
        print(f"🕐 Current UTC time: {datetime.utcnow()}")
        print(f"🕐 Current local time: {datetime.now()}")
        
        # Check scheduled time
        scheduled_utc_hour = 0  # 12 AM UTC
        scheduled_utc_minute = 0
        
        # Convert to Bangladesh time (UTC+6)
        bangladesh_hour = (scheduled_utc_hour + 6) % 24
        print(f"⏰ Scheduled scraping time: {bangladesh_hour:02d}:{scheduled_utc_minute:02d} Bangladesh Time")
        print(f"⏰ Scheduled scraping time: {scheduled_utc_hour:02d}:{scheduled_utc_minute:02d} UTC")
        
        # Check if scheduler should be running
        if settings.environment == "production":
            print("✅ Production environment: Scheduler should be running")
        else:
            print("⚠️  Development environment: Scheduler may not be running")
        
        return True
    
    def start_scheduler(self):
        """Start the scheduler if not running."""
        print("\n🚀 Starting Scheduler...")
        
        if self.scheduler._is_running:
            print("⚠️  Scheduler is already running")
            return True
        
        try:
            self.scheduler.start()
            print("✅ Scheduler started successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to start scheduler: {e}")
            return False
    
    def stop_scheduler(self):
        """Stop the scheduler if running."""
        print("\n⏹️  Stopping Scheduler...")
        
        if not self.scheduler._is_running:
            print("⚠️  Scheduler is not running")
            return True
        
        try:
            self.scheduler.stop()
            print("✅ Scheduler stopped successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to stop scheduler: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        self.db.close()

def main():
    """Main function to run scheduler verification."""
    print("🚀 BiasFree News Scheduler Verification Tool")
    print("=" * 60)
    
    manager = SchedulerManager()
    
    try:
        # Run comprehensive checks
        checks = [
            ("Dependencies", manager.check_scheduler_dependencies),
            ("Status", manager.check_scheduler_status),
            ("Database Tables", manager.check_database_tables),
            ("Recent Activity", manager.check_recent_scheduler_activity),
            ("Configuration", manager.verify_scheduler_configuration),
        ]
        
        results = {}
        for check_name, check_func in checks:
            try:
                results[check_name] = check_func()
            except Exception as e:
                print(f"❌ {check_name} check failed: {e}")
                results[check_name] = False
        
        # Summary
        print("\n📋 Verification Summary:")
        print("-" * 40)
        for check_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{check_name}: {status}")
        
        # Overall status
        all_passed = all(results.values())
        print(f"\n🎯 Overall Status: {'✅ ALL CHECKS PASSED' if all_passed else '❌ SOME CHECKS FAILED'}")
        
        # Recommendations
        if not all_passed:
            print("\n💡 Recommendations:")
            if not results.get("Dependencies", True):
                print("• Install missing dependencies: pip install apscheduler sqlalchemy")
            if not results.get("Status", True):
                print("• Start the scheduler: python -c \"from app.services.scheduler import get_scheduler; get_scheduler().start()\"")
            if not results.get("Database Tables", True):
                print("• Initialize database: Run database migrations")
            if not results.get("Recent Activity", True):
                print("• Check scheduler logs for errors")
                print("• Verify scheduler is running in production")
        
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during verification: {e}")
    finally:
        manager.close()
        print("\n✅ Verification complete!")

if __name__ == "__main__":
    main()