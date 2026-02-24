"""
Application configuration using pydantic-settings.
Loads environment variables from .env file for local development
and from environment for production deployment.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with validation and type safety."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-nano", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=4096, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    
    # Application Configuration
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],
        env="CORS_ORIGINS"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=5, env="RATE_LIMIT_PER_MINUTE")
    
    # Article Processing Limits
    max_article_length: int = Field(default=3000, env="MAX_ARTICLE_LENGTH")
    max_scrape_articles: int = Field(default=10, env="MAX_SCRAPE_ARTICLES")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production-minimum-32-characters-long",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_days: int = Field(default=7, env="JWT_EXPIRATION_DAYS")
    
    # Admin User Configuration
    admin_username: str = Field(default="admin", env="ADMIN_USERNAME")
    admin_email: str = Field(default="adminuser@admin.com", env="ADMIN_EMAIL")
    admin_password: str = Field(default="platformadmin@123", env="ADMIN_PASSWORD")
    
    # Database Configuration (PostgreSQL for production)
    database_url: str = Field(default="", env="DATABASE_URL")
    
    # SMTP Email Configuration
    mail_username: str = Field(default="", env="MAIL_USERNAME")
    mail_password: str = Field(default="", env="MAIL_PASSWORD")
    mail_from: str = Field(default="", env="MAIL_FROM")
    mail_server: str = Field(default="smtp.gmail.com", env="MAIL_SERVER")
    mail_from_name: str = Field(default="BiasFree News", env="MAIL_FROM_NAME")
    mail_port: int = Field(default=587, env="MAIL_PORT")
    
    # Frontend URL Configuration
    frontend_url: str = Field(default="http://localhost:5174", env="FRONTEND_URL")
    
    # Token Expiration Configuration
    verification_token_expiration_minutes: int = Field(default=1, env="VERIFICATION_TOKEN_EXPIRATION_MINUTES")
    
    # Redis Configuration for Celery
    redis_url: str = Field(default="", env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_username: str = Field(default="default", env="REDIS_USERNAME")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    
    @property
    def effective_redis_url(self) -> str:
        """Build Redis URL with explicit var taking priority."""
        if self.redis_url:
            return self.redis_url
        if self.redis_password:
            if self.redis_username:
                return f"redis://{self.redis_username}:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Scheduler Configuration
    scheduler_hour: int = Field(default=6, env="SCHEDULER_HOUR")
    scheduler_minute: int = Field(default=0, env="SCHEDULER_MINUTE")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()
