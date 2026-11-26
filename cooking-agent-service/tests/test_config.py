"""服务配置（Settings）测试。"""

import pytest
from pydantic import ValidationError

from common.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """每个用例前后清理缓存，避免环境变量相互污染。"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_server_defaults():
    """正向路径：服务启动配置使用默认值。"""
    settings = get_settings()

    assert settings.server_host == "0.0.0.0"
    assert settings.server_port == 9000
    assert settings.server_reload is False


def test_server_env_override(monkeypatch):
    """边界情况：环境变量可覆盖服务启动配置。"""
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", "9123")
    monkeypatch.setenv("SERVER_RELOAD", "true")

    settings = Settings()

    assert settings.server_host == "127.0.0.1"
    assert settings.server_port == 9123
    assert settings.server_reload is True


def test_server_port_invalid_type_raises(monkeypatch):
    """无效输入：端口为非数值时抛出校验错误。"""
    monkeypatch.setenv("SERVER_PORT", "not-a-number")

    with pytest.raises(ValidationError):
        Settings()


def test_llm_provider_default():
    """正向路径：未配置时默认使用自定义（OpenAI 兼容）模型。"""
    settings = get_settings()

    assert settings.llm_provider == "custom"


def test_llm_provider_env_override(monkeypatch):
    """边界情况：环境变量可切换到本地 Ollama。"""
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    settings = Settings()

    assert settings.llm_provider == "ollama"


def test_llm_provider_invalid_raises(monkeypatch):
    """无效输入：不在候选集合内的供应方抛出校验错误。"""
    monkeypatch.setenv("LLM_PROVIDER", "unknown")

    with pytest.raises(ValidationError):
        Settings()


def test_deepseek_defaults():
    """正向路径：DeepSeek 供应方使用默认接入地址与模型。"""
    settings = get_settings()

    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-chat"
    assert settings.deepseek_api_key == ""


def test_deepseek_env_override(monkeypatch):
    """边界情况：环境变量可覆盖 DeepSeek 接入配置。"""
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://custom.deepseek")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")

    settings = Settings()

    assert settings.deepseek_base_url == "https://custom.deepseek"
    assert settings.deepseek_model == "deepseek-reasoner"
    assert settings.deepseek_api_key == "secret"
