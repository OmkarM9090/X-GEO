"""Settings tests: list parsing, the shipped example env file, hardening rules.

Regression guard for ``.env.example``: the documented onboarding flow is
``cp .env.example .env`` (``make env``), so every line of that file must load
through the flexible sources — including comma-separated lists, which
pydantic-settings would otherwise try to JSON-decode.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import FlexibleDotEnvSettingsSource, Settings

EXAMPLE_ENV = Path(__file__).resolve().parents[2] / ".env.example"


def test_comma_separated_env_value_becomes_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example, https://b.example ")
    settings = Settings()

    assert settings.ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]


def test_json_list_env_value_is_still_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://a.example", "https://b.example"]')

    assert Settings().ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]


def test_empty_list_env_value_is_an_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "")

    assert Settings().ALLOWED_ORIGINS == []


def test_dotenv_source_splits_comma_separated_lists(tmp_path: Path) -> None:
    """The `.env` source itself (not only os.environ) accepts comma lists."""
    env_file = tmp_path / ".env"
    env_file.write_text("ALLOWED_ORIGINS=https://a.example,https://b.example\n", encoding="utf-8")
    source = FlexibleDotEnvSettingsSource(Settings, env_file=env_file)

    value = source.prepare_field_value(
        "ALLOWED_ORIGINS",
        Settings.model_fields["ALLOWED_ORIGINS"],
        "https://a.example,https://b.example",
        False,  # pydantic-settings reports False for plain list fields
    )

    assert value == ["https://a.example", "https://b.example"]


def test_shipped_example_env_file_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    """`cp .env.example .env` must produce a loadable configuration."""
    assert EXAMPLE_ENV.is_file(), "backend/.env.example is part of the developer experience"
    source = FlexibleDotEnvSettingsSource(Settings, env_file=EXAMPLE_ENV)

    values = source()

    # Comma-separated list, JSON list and inline comments all parse correctly.
    assert values["ALLOWED_ORIGINS"] == ["http://localhost:5173", "http://localhost:3000"]
    assert values["SUPABASE_JWT_ALGORITHMS"] == ["HS256", "ES256", "RS256"]
    assert values["CRAWLER_ENGINE"] == "scrapy"

    # …and the file drives a full Settings load (env vars win, as documented).
    monkeypatch.setitem(Settings.model_config, "env_file", str(EXAMPLE_ENV))
    settings = Settings()

    assert settings.ALLOWED_ORIGINS == ["http://localhost:5173", "http://localhost:3000"]
    assert not settings._looks_like_placeholder(settings.SUPABASE_JWT_SECRET)


def test_production_rejects_debug_and_placeholder_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("AUTH_DEV_TOKEN_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://your-project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "your-anon-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "your-jwt-secret")

    with pytest.raises(ValidationError) as excinfo:
        Settings()

    message = str(excinfo.value)
    assert "DEBUG must be false" in message
    assert "SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_JWT_SECRET are required" in message


def test_api_prefix_is_normalised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_V1_PREFIX", "api/v2/")

    assert Settings().API_V1_PREFIX == "/api/v2"
