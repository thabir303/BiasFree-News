"""
Redis-based scheduler service using Celery Beat.
Manages scheduled tasks for news scraping.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config.settings import settings
import redis

logger = logging.getLogger(__name__)


class RedisSchedulerService:
    """Service for managing scheduled tasks using Redis and Celery."""
    
    def __init__(self):
        """Initialize Redis connection."""
        redis_kwargs = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "decode_responses": True
        }
        
        # Add authentication if provided
        if settings.redis_username:
            redis_kwargs["username"] = settings.redis_username
        if settings.redis_password:
            redis_kwargs["password"] = settings.redis_password
            
        self.redis_client = redis.Redis(**redis_kwargs)
        self.scheduler_running_key = "scheduler:running"
        self.last_run_key = "scheduler:last_run"
        self.next_run_key = "scheduler:next_run"
        
    def start(self):
        """Mark scheduler as running."""
        try:
            self.redis_client.set(self.scheduler_running_key, "true")
            logger.info("Redis-based scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            
    def stop(self):
        """Mark scheduler as stopped."""
        try:
            self.redis_client.set(self.scheduler_running_key, "false")
            logger.info("Redis-based scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {str(e)}")
            
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        try:
            status = self.redis_client.get(self.scheduler_running_key)
            return status == "true"
        except Exception as e:
            logger.error(f"Failed to check scheduler status: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status including next run time and last run info."""
        try:
            running = self.is_running()
            
            # Get current schedule from Redis (or use defaults)
            stored_hour = self.redis_client.get("scheduler:hour")
            stored_minute = self.redis_client.get("scheduler:minute")
            
            if stored_hour and stored_minute:
                current_hour = int(stored_hour)
                current_minute = int(stored_minute)
            else:
                current_hour = settings.scheduler_hour
                current_minute = settings.scheduler_minute
            
            # Calculate next run time based on current schedule
            next_run = self._calculate_next_run()
            
            # Get last run info from Redis
            last_run_data = self.redis_client.get(self.last_run_key)
            last_run = eval(last_run_data) if last_run_data else None
            
            return {
                "running": running,
                "next_run": next_run.isoformat() if next_run else None,
                "last_run": last_run,
                "schedule": f"Daily at {current_hour:02d}:{current_minute:02d} BDT"
            }
        except Exception as e:
            logger.error(f"Failed to get scheduler status: {str(e)}")
            return {
                "running": False,
                "next_run": None,
                "last_run": None,
                "schedule": "Unknown"
            }
    
    def _calculate_next_run(self) -> Optional[datetime]:
        """Calculate next scheduled run time in BDT."""
        try:
            now = datetime.now()
            
            # Get current schedule from Redis (or use defaults)
            stored_hour = self.redis_client.get("scheduler:hour")
            stored_minute = self.redis_client.get("scheduler:minute")
            
            if stored_hour and stored_minute:
                schedule_hour = int(stored_hour)
                schedule_minute = int(stored_minute)
            else:
                schedule_hour = settings.scheduler_hour
                schedule_minute = settings.scheduler_minute
            
            # Create next run time for today
            next_run = now.replace(
                hour=schedule_hour,
                minute=schedule_minute,
                second=0,
                microsecond=0
            )
            
            # If time has passed today, schedule for tomorrow
            if next_run <= now:
                next_run += timedelta(days=1)
            
            return next_run
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {str(e)}")
            return None
    
    def update_schedule(self, hour: int, minute: int) -> bool:
        """
        Update the scheduler configuration.
        
        Args:
            hour: Hour (0-23) in BDT
            minute: Minute (0-59)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                logger.error(f"Invalid time: {hour}:{minute}")
                return False
            
            # Store in Redis for persistence (Celery Beat will read on restart)
            self.redis_client.set("scheduler:hour", str(hour))
            self.redis_client.set("scheduler:minute", str(minute))
            
            logger.info(f"Scheduler updated to run daily at {hour:02d}:{minute:02d} BDT")
            logger.info(f"⚠️ Restart Celery Beat to apply changes: celery -A app.celery_app beat --loglevel=info")
            return True
            
            logger.info(f"Scheduler updated to run daily at {hour:02d}:{minute:02d} BDT")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update schedule: {str(e)}")
            return False
    
    def record_run(self, status: str, articles_count: int = 0, error: str = None):
        """
        Record the last scraping run information.
        
        Args:
            status: 'success', 'failed', or 'partial'
            articles_count: Number of articles scraped
            error: Error message if failed
        """
        try:
            run_info = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "articles_count": articles_count,
                "error": error
            }
            self.redis_client.set(self.last_run_key, str(run_info))
            logger.info(f"Recorded scheduler run: {status}, {articles_count} articles")
        except Exception as e:
            logger.error(f"Failed to record run: {str(e)}")


# Global scheduler service instance
redis_scheduler_service = RedisSchedulerService()
