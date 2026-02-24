"""
Celery configuration for distributed task scheduling with Redis.
"""
from celery import Celery
from celery.schedules import crontab
from app.config.settings import settings
import logging
import redis

logger = logging.getLogger(__name__)

# Use the centralized Redis URL from settings
redis_url = settings.effective_redis_url

celery_app = Celery(
    "biasfree_news",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Dhaka",  # BDT timezone
    enable_utc=False,
    task_track_started=True,
    task_time_limit=7200,  # 2 hours max
    task_soft_time_limit=6000,  # 100 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    result_expires=86400,  # Results expire after 24 hours
)

# Try to read schedule from Redis, fallback to default
try:
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True
    )
    stored_hour = redis_client.get("scheduler:hour")
    stored_minute = redis_client.get("scheduler:minute")
    
    if stored_hour and stored_minute:
        schedule_hour = int(stored_hour)
        schedule_minute = int(stored_minute)
        logger.info(f"📅 Loaded schedule from Redis: {schedule_hour:02d}:{schedule_minute:02d} BDT")
    else:
        schedule_hour = settings.scheduler_hour
        schedule_minute = settings.scheduler_minute
        logger.info(f"📅 Using default schedule: {schedule_hour:02d}:{schedule_minute:02d} BDT")
except Exception as e:
    logger.warning(f"Failed to read schedule from Redis: {str(e)}, using defaults")
    schedule_hour = settings.scheduler_hour
    schedule_minute = settings.scheduler_minute

# Periodic task schedule
celery_app.conf.beat_schedule = {
    "daily-news-scraping": {
        "task": "app.tasks.scheduled_scraping_task",
        "schedule": crontab(hour=schedule_hour, minute=schedule_minute),
        "options": {"expires": 3600}  # Task expires after 1 hour if not picked up
    },
}

logger.info("Celery app configured with Redis broker")
