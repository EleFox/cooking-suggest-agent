"""统一 API 信封。

所有业务接口都返回 ``design/agreement/api-conventions.md`` 定义的 JSON 信封：

    {"code": <int>, "data": <any>, "message": <str>}

``code`` 与 HTTP 状态码一致。健康检查接口是例外，不使用此信封。
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """统一响应信封结构。"""

    code: int
    data: T | None
    message: str


def ok(data, message: str = "ok") -> Envelope:
    """构造成功信封（code=200）。

    Args:
        data: 实际返回数据（可为任意类型，接口无结果时为空集合）。
        message: 状态解释，成功固定为 ``ok``。

    Returns:
        成功信封实例。
    """
    return Envelope(code=200, data=data, message=message)


def error(code: int, message: str) -> Envelope:
    """构造错误信封（data 为 None）。

    Args:
        code: 错误状态码，与 HTTP 状态码一致。
        message: 可读的错误描述文本。

    Returns:
        错误信封实例。
    """
    return Envelope(code=code, data=None, message=message)
