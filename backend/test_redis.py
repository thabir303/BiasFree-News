import redis
from app.config.settings import settings

# Test Redis connection
try:
    r = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        username=settings.redis_username,
        password=settings.redis_password,
        db=settings.redis_db,
        decode_responses=True
    )
    
    # Test connection
    if r.ping():
        print("✅ Redis connection successful!")
        print(f"📍 Host: {settings.redis_host}")
        print(f"🔌 Port: {settings.redis_port}")
        print(f"👤 Username: {settings.redis_username}")
        
        # Test set/get
        r.set('test_key', 'Hello from BiasFree News!')
        value = r.get('test_key')
        print(f"✅ Test set/get: {value}")
        
        # Clean up
        r.delete('test_key')
        print("✅ All tests passed!")
    else:
        print("❌ Redis ping failed")
        
except Exception as e:
    print(f"❌ Redis connection failed: {str(e)}")
