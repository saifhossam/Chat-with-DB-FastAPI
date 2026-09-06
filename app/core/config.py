from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    app_name: str = "AI Database Chat"
    secret_key: str = "jwt_secret_key"
    database_url: str = "postgresql://app:app@localhost:5432/ai_database_chat"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    
    # Security: Input validation
    max_input_length: int = 5000
    
    # Security: Rate limiting
    rate_limit_requests: int = 10
    rate_limit_period_seconds: int = 60
    
    # Security: Streaming throttle (seconds between chunks)
    stream_throttle_seconds: float = 0.01
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
