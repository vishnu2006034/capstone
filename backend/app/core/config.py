from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Meeting2Execution AI"
    ENV: str = "development"
    DATABASE_URL: str
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"
    STORAGE_DIR: str = "./storage_vault"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
