"""Application settings.

A single, cached :class:`Settings` instance is the source of truth for every
tunable in the service. Values come from (highest priority first):

1. explicit constructor arguments (used heavily by the test suite),
2. real environment variables,
3. `backend/.env`,
4. the defaults declared below.

List-typed settings accept **either** a JSON array (`["a","b"]`) **or** a plain
comma separated string (`a,b`) so operators are never surprised by
`pydantic-settings`' JSON-only parsing of complex types.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

Environment = Literal["development", "staging", "production", "test"]
LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]
CrawlerEngine = Literal["scrapy", "httpx", "playwright"]

#: Values shipped in .env.example. Treated as "not configured" so that a
#: placeholder never accidentally counts as a real production credential.
_PLACEHOLDER_MARKERS = (
    "your-project",
    "your-anon-key",
    "your-jwt-secret",
    "your-service-role-key",
    "changeme",
)

_ORIGIN_RE = re.compile(r"^https?://[^\s/]+$")


def _is_list_annotation(annotation: Any) -> bool:
    """True when a field annotation is `list[...]` (possibly wrapped in Annotated)."""
    from typing import get_args, get_origin

    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        return _is_list_annotation(args[0]) if args else False
    return origin is list or annotation is list


class _FlexibleListSourceMixin:
    """Allow comma separated values for list-typed settings."""

    def prepare_field_value(
        self, field_name: str, field: FieldInfo | None, value: Any, value_is_complex: bool
    ) -> Any:
        if value_is_complex and isinstance(value, str):
            annotation = getattr(field, "annotation", None)
            if _is_list_annotation(annotation):
                stripped = value.strip()
                if stripped and not stripped.startswith("["):
                    return [item.strip() for item in stripped.split(",") if item.strip()]
        return super().prepare_field_value(field_name, field, value, value_is_complex)  # type: ignore[misc]


class FlexibleEnvSettingsSource(_FlexibleListSourceMixin, EnvSettingsSource):
    """Environment-variable source with comma-separated list support."""


class FlexibleDotEnvSettingsSource(_FlexibleListSourceMixin, DotEnvSettingsSource):
    """`.env` file source with comma-separated list support."""


class Settings(BaseSettings):
    """Typed, validated application configuration."""

    # -- Application ---------------------------------------------------------
    APP_NAME: str = "X-GEO"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    AUTO_CREATE_TABLES: bool = True
    ACCESS_LOG_ENABLED: bool = True
    REQUEST_ID_HEADER: str = "X-Request-ID"

    # -- Observability -------------------------------------------------------
    LOG_LEVEL: LogLevel = "INFO"
    LOG_JSON: bool = True

    # -- Database ------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://xgeo:xgeo_dev@localhost:5432/xgeo_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT_SECONDS: int = 30
    DATABASE_POOL_RECYCLE_SECONDS: int = 1800
    DATABASE_ECHO: bool = False

    # -- Redis / Celery ------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    TASK_ALWAYS_EAGER: bool = False
    TASK_TIME_LIMIT_SECONDS: int = 300
    TASK_SOFT_TIME_LIMIT_SECONDS: int = 240
    TASK_MAX_RETRIES: int = 3
    TASK_RESULT_EXPIRES_SECONDS: int = 3600

    # -- Supabase Auth -------------------------------------------------------
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_JWT_ALGORITHMS: list[str] = ["HS256", "ES256", "RS256"]
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_TIMEOUT_SECONDS: float = 10.0
    SUPABASE_JWKS_CACHE_SECONDS: int = 3600
    AUTH_AUTO_PROVISION_USERS: bool = True
    #: Development-only escape hatch: mint a local JWT without Supabase.
    AUTH_DEV_TOKEN_ENABLED: bool = False
    AUTH_DEV_TOKEN_TTL_SECONDS: int = 60 * 60 * 12

    # -- OpenAI (embeddings / simulations) -----------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    EMBEDDING_DIMENSIONS: int = 1536
    OPENAI_TIMEOUT_SECONDS: float = 60.0

    # -- Crawler -------------------------------------------------------------
    CRAWLER_ENGINE: CrawlerEngine = "scrapy"
    CRAWLER_USER_AGENT: str = "X-GEO-Bot/1.0 (+https://x-geo.dev/bot)"
    CRAWLER_TIMEOUT_SECONDS: int = 10
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_RESPECT_ROBOTS_TXT: bool = True
    CRAWLER_MAX_RESPONSE_BYTES: int = 5_000_000
    MAX_PAGES_PER_AUDIT: int = 25
    PLAYWRIGHT_TIMEOUT_MS: int = 15000
    PLAYWRIGHT_HEADLESS: bool = True

    # -- Chunking ------------------------------------------------------------
    CHUNK_SIZE_TOKENS: int = 256
    CHUNK_OVERLAP_TOKENS: int = 32
    CHUNK_MIN_TOKENS: int = 16

    # -- Scoring -------------------------------------------------------------
    #: Weights of the four PCS sub-scores; must sum to 1.0.
    PCS_WEIGHTS: dict[str, float] = {
        "technical": 0.35,
        "semantic": 0.30,
        "evidentiary": 0.20,
        "machine_readability": 0.15,
    }

    # -- Plans ---------------------------------------------------------------
    PLAN_CREDIT_LIMITS: dict[str, int] = {
        "free": 10,
        "pro": 200,
        "agency": 1_000,
        "enterprise": 100_000,
    }

    # -- Security ------------------------------------------------------------
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    ALLOWED_ORIGIN_REGEX: str | None = None
    ALLOWED_HOSTS: list[str] = ["*"]
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10
    SSRF_BLOCKED_RANGES: list[str] = [
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
    ]
    #: Hostnames or CIDRs allowed to resolve to private addresses
    #: (self-hosted/staging targets you own). Empty in production.
    SSRF_ALLOWLIST: list[str] = []
    #: When True every non-globally-routable address is blocked, even if it is
    #: not listed in SSRF_BLOCKED_RANGES.
    SSRF_STRICT_MODE: bool = True
    #: Connect to the exact IP that passed validation (defeats DNS rebinding).
    SSRF_PIN_RESOLVED_IP: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_assignment=False,
    )

    # -- Custom sources ------------------------------------------------------
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            FlexibleEnvSettingsSource(settings_cls),
            FlexibleDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )

    # -- Validators ----------------------------------------------------------
    @field_validator("DATABASE_URL")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the async driver, e.g. "
                "'postgresql+asyncpg://user:pass@host:5432/db'"
            )
        return value

    @field_validator("API_V1_PREFIX")
    @classmethod
    def _normalise_prefix(cls, value: str) -> str:
        return "/" + value.strip("/")

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def _validate_origins(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for origin in value:
            origin = origin.strip().rstrip("/")
            if not origin:
                continue
            if origin != "*" and not _ORIGIN_RE.match(origin):
                raise ValueError(
                    f"Invalid CORS origin '{origin}': expected scheme://host[:port] or '*'"
                )
            cleaned.append(origin)
        return cleaned

    @field_validator("PCS_WEIGHTS")
    @classmethod
    def _validate_weights(cls, value: dict[str, float]) -> dict[str, float]:
        required = {"technical", "semantic", "evidentiary", "machine_readability"}
        missing = required - set(value)
        if missing:
            raise ValueError(f"PCS_WEIGHTS is missing weights for: {sorted(missing)}")
        total = sum(value[key] for key in required)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"PCS_WEIGHTS must sum to 1.0 (got {total:.4f})")
        return value

    @field_validator("CHUNK_OVERLAP_TOKENS")
    @classmethod
    def _validate_overlap(cls, value: int, info: Any) -> int:
        chunk_size = (info.data or {}).get("CHUNK_SIZE_TOKENS")
        if chunk_size is not None and value >= chunk_size:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be smaller than CHUNK_SIZE_TOKENS")
        return value

    @model_validator(mode="after")
    def _enforce_production_hardening(self) -> Settings:
        if self.ENVIRONMENT not in {"staging", "production"}:
            return self

        problems: list[str] = []
        if self.DEBUG:
            problems.append("DEBUG must be false outside development")
        if not self.supabase_auth_configured:
            problems.append("SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_JWT_SECRET are required")
        if self.AUTH_DEV_TOKEN_ENABLED:
            problems.append("AUTH_DEV_TOKEN_ENABLED is a development-only feature")
        if "*" in self.ALLOWED_ORIGINS:
            problems.append("ALLOWED_ORIGINS must not contain '*' outside development")
        if self.SSRF_ALLOWLIST:
            problems.append("SSRF_ALLOWLIST must be empty outside development")
        if problems:
            raise ValueError(
                "Unsafe configuration for ENVIRONMENT="
                + self.ENVIRONMENT
                + ": "
                + "; ".join(problems)
            )
        return self

    # -- Derived helpers -----------------------------------------------------
    @staticmethod
    def _looks_like_placeholder(value: str) -> bool:
        lowered = (value or "").strip().lower()
        if not lowered:
            return True
        return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT in {"development", "test"}

    @property
    def supabase_url_normalised(self) -> str:
        return (self.SUPABASE_URL or "").rstrip("/")

    @property
    def supabase_auth_configured(self) -> bool:
        """True when real Supabase credentials are present."""
        return not (
            self._looks_like_placeholder(self.SUPABASE_URL)
            or self._looks_like_placeholder(self.SUPABASE_ANON_KEY)
            or self._looks_like_placeholder(self.SUPABASE_JWT_SECRET)
        )

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url_normalised}/auth/v1/.well-known/jwks.json"

    @property
    def embeddings_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY) and not self._looks_like_placeholder(self.OPENAI_API_KEY)

    @property
    def auth_issuer(self) -> str | None:
        """Expected `iss` claim for Supabase-issued access tokens."""
        if not self.supabase_url_normalised:
            return None
        return f"{self.supabase_url_normalised}/auth/v1"

    @property
    def database_host(self) -> str:
        """Host part of DATABASE_URL (used for startup diagnostics only)."""
        try:
            return urlparse(self.DATABASE_URL).hostname or "unknown"
        except ValueError:  # pragma: no cover - defensive
            return "unknown"

    @property
    def cors_origin_regex(self) -> str | None:
        """Effective CORS regex: preview/sandbox friendly in development."""
        if self.ALLOWED_ORIGIN_REGEX:
            return self.ALLOWED_ORIGIN_REGEX
        if self.DEBUG or self.is_development:
            # Sandbox previews are served from generated hostnames.
            return r"https?://[A-Za-z0-9.\-]+(:\d+)?"
        return None

    def plan_credit_limit(self, plan_tier: str) -> int:
        """Monthly credit allowance for a plan tier (falls back to `free`)."""
        return self.PLAN_CREDIT_LIMITS.get(plan_tier, self.PLAN_CREDIT_LIMITS["free"])


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached)."""
    return Settings()


def reload_settings() -> Settings:
    """Clear the cache and rebuild settings (used by tests and scripts)."""
    get_settings.cache_clear()
    return get_settings()
