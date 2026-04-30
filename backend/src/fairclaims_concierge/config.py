"""Environment-based configuration via pydantic-settings.

All env vars use the `FAIRCLAIMS_` prefix. The config surface is small
on purpose — settings here are the only knobs the deploy turns.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "FAIRCLAIMS_"}

    # LLM
    llm_backend: Literal["mock", "api"] = "mock"
    llm_timeout: float = 15.0
    llm_api_base: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"

    # Database (SQLite — FAQ store + questions log)
    db_path: str = "./data/fairclaims.db"

    # Privacy
    pii_backend: Literal["regex"] = "regex"

    # Admin endpoints — empty token blocks every admin request.
    admin_token: str = ""

    # Visitor analytics (weekly-rotated; not for re-identification).
    visitor_hash_salt: str = ""

    # Kill switch — when false, /concierge/ask returns 503.
    concierge_enabled: bool = True

    # Static site root — Docker sets this to /app at deploy.
    static_dir: str = "."

    # CORS — empty means same-origin only (default for prod).
    cors_origins: List[str] = []

    # Logging
    log_renderer: Literal["json", "console"] = "json"
