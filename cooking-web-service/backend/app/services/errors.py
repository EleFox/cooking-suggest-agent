"""服务层业务异常。

服务层校验失败时抛出对应异常，由路由层捕获并转换为统一信封
（``code`` 与 HTTP 状态码一致）。``data`` 统一为 ``null``。
"""


class ApiError(Exception):
    """业务异常基类，携带状态码与可读错误描述。"""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ElementValidationError(ApiError):
    """偏好要素校验失败（不存在或类型不符），返回 422。"""

    def __init__(self, message: str = "偏好要素校验失败") -> None:
        super().__init__(422, message)


class SchemeValidationError(ApiError):
    """方案参数校验失败（如名称为空），返回 422。"""

    def __init__(self, message: str = "方案参数不合法") -> None:
        super().__init__(422, message)


class SchemeNotFoundError(ApiError):
    """目标方案不存在，返回 404。"""

    def __init__(self, message: str = "方案不存在") -> None:
        super().__init__(404, message)


class MemberValidationError(ApiError):
    """成员参数校验失败（如姓名为空、要素非法），返回 422。"""

    def __init__(self, message: str = "成员参数不合法") -> None:
        super().__init__(422, message)


class MemberNotFoundError(ApiError):
    """目标成员不存在，返回 404。"""

    def __init__(self, message: str = "成员不存在") -> None:
        super().__init__(404, message)


class RecipeValidationError(ApiError):
    """菜谱参数校验失败（如名称为空、要素非法、单值约束违反），返回 422。"""

    def __init__(self, message: str = "菜谱参数不合法") -> None:
        super().__init__(422, message)


class RecipeNotFoundError(ApiError):
    """目标菜谱不存在，返回 404。"""

    def __init__(self, message: str = "菜谱不存在") -> None:
        super().__init__(404, message)
