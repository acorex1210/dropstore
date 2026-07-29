from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dropstore"

    meli_access_token: str = ""
    meli_public_key: str = ""
    meli_webhook_secret: str = ""

    dropi_base_url: str = "https://api.dropi.co/api/v1"
    dropi_email: str = ""
    dropi_password: str = ""
    dropi_white_brand_id: str = ""
    dropi_integration_token: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from_email: str = ""

    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""

    cors_origins: str = "http://localhost:3000"
    default_margin_percentage: float = 30.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
