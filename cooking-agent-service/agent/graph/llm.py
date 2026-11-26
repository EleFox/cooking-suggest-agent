"""主模型（LLM）初始化与选择。

根据 ``Settings.llm_provider`` 在以下供应方中选择其一，作为工作流统一使用的
``main_llm``，供 ``agent/graph/nodes.py`` 装配决策链：

- ``custom``：OpenAI 兼容的自定义服务（默认）；
- ``ollama``：本地 Ollama；
- ``deepseek``：DeepSeek 官方接口。

供应方由配置（``.env`` / 环境变量 ``LLM_PROVIDER``）驱动，禁止在此硬编码。
"""

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.tools.recipes import recipes_tools
from common.config import Settings, get_settings
from common.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# 自定义 OpenAI 兼容服务附带的路由标识头（供服务端区分调用来源）。
_CUSTOM_HEADERS = {"x-opencode-session": "cooking-agent-test"}


def _build_llm(settings: Settings):
    """按 ``llm_provider`` 构造主模型实例。

    仅实例化被选中的供应方，避免未配置密钥的备用供应方在导入期抛出凭据错误。

    Args:
        settings: 应用配置。

    Returns:
        与供应方对应的 LangChain Chat 模型实例。
    """
    if settings.llm_provider == "ollama":
        logger.info("using ollama llm: model=%s", settings.ollama_model)
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )

    if settings.llm_provider == "deepseek":
        logger.info("using deepseek llm: model=%s", settings.deepseek_model)
        return ChatOpenAI(
            model=settings.deepseek_model,
            base_url=settings.deepseek_base_url,
            api_key=SecretStr(settings.deepseek_api_key),
        )

    logger.info("using custom llm: model=%s", settings.custom_model)
    return ChatOpenAI(
        model=settings.custom_model,
        base_url=settings.custom_base_url,
        api_key=SecretStr(settings.custom_api_key),
        default_headers=_CUSTOM_HEADERS,
    )


# 工作流统一使用的主模型，供应方由 LLM_PROVIDER 决定。
main_llm = _build_llm(settings)

main_llm.bind_tools(recipes_tools)
