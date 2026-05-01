from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LLimit Gateway"
    app_version: str = "0.1.0"
    api_key: str = "dev-api-key-12345"
    db_path: str = "data/llimit.db"
    uploads_path: str = "uploads"
    preserve_old_db: bool = False
    model_selection_api_base_url: str = "http://localhost:8888"
    model_selection_api_scoring_model: str | None = "dn_embedding/dn-embedding-scoring"
    model_selection_api_length_prediction_model: str | None = "dn_embedding_length_prediction/dn-embedding-length-prediction"
    model_selection_api_batch_size: int = 128
    override_step_model_id: str | None = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
