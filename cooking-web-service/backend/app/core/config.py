"""应用配置模块（通过环境变量驱动）。

使用 ``pydantic-settings``（Pydantic v2 / FastAPI 的标准配套库）将全部由
环境变量驱动的配置集中到一处。配置值的解析优先级从低到高为：

    1. ``Settings`` 模型上声明的默认值
    2. ``.env`` 文件中的值（若存在）
    3. 实际的环境变量

各模块必须通过 ``get_settings()`` 获取缓存实例，禁止直接读取
``os.environ``。

用法：:

    from app.core.config import get_settings

    settings = get_settings()
    logger.info("app name: %s", settings.app_name)
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用运行配置。

    集中声明所有由环境变量驱动的配置项；字段名即环境变量名（如
    ``database_path`` 对应 ``DATABASE_PATH``）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Cooking Web Service"
    debug: bool = False
    log_level: str = "INFO"

    # SQLite 数据库文件路径（相对于后端目录）。
    database_path: str = "datas/cooking.db"

    # Agent 服务集成地址。
    agent_service_url: str = "http://localhost:9000"

    # 调用 Agent 服务的超时上限（秒），超时由上层兜底显示。
    agent_service_timeout: float = 600.0

    # 决策链路专用线程池大小：隔离长耗时的 Agent 调用，避免占用默认请求
    # 线程池而阻塞反向数据面（Agent 反向调用的菜谱查询/详情 API）。
    decision_max_workers: int = 4

    @property
    def recipes_dir(self) -> str:
        """菜谱 MD 详情文件目录。

        复用数据库文件所在的数据目录，在其下单独建立 ``recipes`` 子目录，
        避免为文件存储额外引入环境变量。

        Returns:
            菜谱 MD 文件目录的字符串路径。
        """
        return str(Path(self.database_path).parent / "recipes")


@lru_cache
def get_settings() -> Settings:
    """返回缓存的应用配置实例。"""
    return Settings()
