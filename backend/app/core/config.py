from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Meeting2Execution AI"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database Configuration
    DATABASE_URL: str
    
    # AI Config
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Storage Configuration
    STORAGE_DIR: str = "./storage_vault"
    
    # External integrations
    JIRA_API_URL: str = "https://your-domain.atlassian.net"
    JIRA_USER_EMAIL: str = "user@company.com"
    JIRA_API_TOKEN: str = "placeholder_token"
    SLACK_WEBHOOK_URL: str = "https://hooks.slack.com/services/xxx/yyy/zzz"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
