"""
ReviewGuard — Configuration module.
Loads environment variables and defines project-wide settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment via pydantic-settings."""

    groq_api_key: str = ""
    gmail_credentials_path: str = "credentials.json"
    google_sheets_id: str
    google_credentials_path: str = "service_account.json"
    google_review_link: str
    form_url: str
    restaurant_name: str = "Aqua Whiteladies"
    owner_name: str = "Ben Smithson"
    owner_email: str
    dry_run: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
