from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LLimit Gateway"
    app_version: str = "0.1.0"
    api_key: str = "dev-api-key-12345"
    db_path: str = "data/llimit.db"
    uploads_path: str = "uploads"
    preserve_old_db: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
