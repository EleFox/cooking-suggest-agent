"""应用配置模块（本服务唯一配置入口）。

本项目（web-service 与 agent-service）属于同一系统的两个服务/进程，统一由
本模块存放全部配置。配置值的解析优先级从低到高为：

    1. ``Settings`` 模型上声明的默认值
    2. ``.env`` 文件中的值（若存在）
    3. 实际的环境变量

禁止在应用代码中直接读取 ``os.environ``，一律通过 ``get_settings()`` 获取。

用法：:

    from common.config import get_settings

    settings = get_settings()
    logger.info("app name: %s", settings.app_name)
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用运行配置。

    集中声明所有由环境变量驱动的配置项；字段名即环境变量名（如
    ``ollama_base_url`` 对应 ``OLLAMA_BASE_URL``）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 通用配置。
    app_name: str = "Cooking Service"
    debug: bool = False
    log_level: str = "INFO"

    # 服务启动配置（host/port 由本配置驱动，见 app/main.py 的 uvicorn 启动）。
    server_host: str = "0.0.0.0"
    server_port: int = 9000
    server_reload: bool = False

    # 主模型供应方：custom（OpenAI 兼容自定义服务）/ ollama（本地）/ deepseek（官方）。
    # 由 agent/graph/llm.py 依据该值选择并实例化 main_llm。
    llm_provider: Literal["custom", "ollama", "deepseek"] = "custom"

    # 本地 Ollama 服务地址与默认模型。
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"

    # OpenAI 兼容的自定义服务端接入地址、模型与 API Key。
    custom_base_url: str = ""
    custom_model: str = ""
    custom_api_key: str = ""

    # DeepSeek 官方接口接入地址、模型与 API Key（密钥请勿提交到仓库）。
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_api_key: str = ""

    # 菜谱对接接口
    api_recipes_query: str = "http://localhost:8000/api/recipes"
    api_recipe_detail_query: str = "http://localhost:8000/api/recipes/detail"

    # 反向调用 web-service 菜谱接口的超时时间（秒）。
    api_timeout: float = 30.0


@lru_cache
def get_settings() -> Settings:
    """返回缓存的应用配置实例。"""
    return Settings()
