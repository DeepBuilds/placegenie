from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """All configuration comes from environment variables / backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PlaceGenie AI"
    app_env: str = "development"
    app_version: str = "0.1.0"

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "placegenie"
    db_password: str = ""
    db_name: str = "placegenie"

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # Failed logins allowed within the window before further attempts get 429 (slows password guessing)
    login_max_failures_per_email: int = 5
    login_max_failures_per_ip: int = 30
    login_window_minutes: int = 15

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Resume uploads (relative paths are resolved against the backend/ folder)
    upload_dir: str = "uploads"
    resume_max_mb: int = 5
    resume_max_pages: int = 10

    # Chatbot. LLM_PROVIDER: none | anthropic | openai (openai also covers OpenAI-compatible servers
    # via LLM_BASE_URL). With "none" or a missing key the built-in placement guide answers instead.
    llm_provider: str = "none"
    llm_api_key: str = ""
    llm_model: str = ""  # empty = a sensible default for the chosen provider
    llm_base_url: str = ""  # empty = the provider's public endpoint
    llm_timeout_seconds: float = 20.0
    llm_max_tokens: int = 600
    llm_share_profile: bool = True  # send a small, contact-free profile summary to the LLM for personalised answers

    chat_rate_limit_per_minute: int = 15
    chat_max_message_chars: int = 1000
    chat_max_messages_per_conversation: int = 200
    chat_history_turns: int = 10  # earlier messages given to the LLM as context

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters in the password safely.
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        return path if path.is_absolute() else Path(__file__).resolve().parents[2] / path

    @property
    def resume_max_bytes(self) -> int:
        return self.resume_max_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
