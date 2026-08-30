from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    app_name: str = "AI Database Chat"
    secret_key: str = "jwt_secret_key"
    database_url: str = "postgresql://app:app@localhost:5432/ai_database_chat"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
