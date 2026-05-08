from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency exists in normal setup
    pass
else:
    load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    return float(value)


def _env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    use_real_llm: bool
    anthropic_api_key: str | None
    openai_api_key: str | None
    claude_model: str
    openai_model: str
    llm_temperature: float
    llm_max_tokens: int
    llm_max_retries: int
    inconsistency_max_group_size: int
    max_csv_size_mb: int
    backend_host: str
    backend_port: int
    cors_origins: list[str]
    log_level: str
    log_raw_llm_responses: bool
    log_dir: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        use_real_llm=_env_bool("USE_REAL_LLM", False),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        llm_temperature=_env_float("LLM_TEMPERATURE", 0.1),
        llm_max_tokens=_env_int("LLM_MAX_TOKENS", 2048),
        llm_max_retries=_env_int("LLM_MAX_RETRIES", 3),
        inconsistency_max_group_size=_env_int("INCONSISTENCY_MAX_GROUP_SIZE", 20),
        max_csv_size_mb=_env_int("MAX_CSV_SIZE_MB", 10),
        backend_host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        backend_port=_env_int("BACKEND_PORT", 8000),
        cors_origins=_env_list(
            "CORS_ORIGINS",
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_raw_llm_responses=_env_bool("LOG_RAW_LLM_RESPONSES", True),
        log_dir=os.getenv("LOG_DIR", "logs"),
    )
