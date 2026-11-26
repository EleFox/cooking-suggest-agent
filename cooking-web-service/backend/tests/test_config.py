import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_settings_defaults():
    settings = Settings(_env_file=None)

    assert settings.app_name == "Cooking Web Service"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.agent_service_url == "http://localhost:9000"
    assert settings.agent_service_timeout == 600.0


def test_settings_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Service")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent:8080")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Service"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.agent_service_url == "http://agent:8080"


def test_settings_loaded_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "test.env"
    env_file.write_text(
        "APP_NAME=EnvFile Service\nDEBUG=1\nLOG_LEVEL=WARNING\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "EnvFile Service"
    assert settings.debug is True
    assert settings.log_level == "WARNING"


def test_settings_environment_takes_precedence_over_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "test.env"
    env_file.write_text("APP_NAME=FromEnvFile\nDEBUG=0\n", encoding="utf-8")
    monkeypatch.setenv("APP_NAME", "FromEnvironment")
    monkeypatch.setenv("DEBUG", "true")

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "FromEnvironment"
    assert settings.debug is True


def test_settings_invalid_bool_raises(monkeypatch):
    monkeypatch.setenv("DEBUG", "not-a-bool")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_unknown_env_vars_are_ignored(monkeypatch):
    monkeypatch.setenv("UNRELATED_VAR", "something")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Cooking Web Service"


def test_get_settings_returns_cached_instance():
    first = get_settings()
    second = get_settings()

    assert first is second


def test_get_settings_cache_clear(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_NAME", "Cached Name")

    settings = get_settings()

    assert settings.app_name == "Cached Name"
    get_settings.cache_clear()
