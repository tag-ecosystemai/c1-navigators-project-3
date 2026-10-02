from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_name: str = 'AI Credit-Risk Investigation Agent API'
    environment: str = 'development'
    database_url: str = 'postgresql+psycopg://postgres:postgres@localhost:5432/credit_risk_db'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
settings = Settings()
