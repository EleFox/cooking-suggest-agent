"""统一 API 信封测试。"""

import pytest
from pydantic import ValidationError

from app.schemas.envelope import Envelope, error, ok


def test_ok_returns_success_envelope():
    """正向路径：ok 构造成功信封，code=200。"""
    result = ok({"status": "ok"})

    assert result.code == 200
    assert result.data == {"status": "ok"}
    assert result.message == "ok"


def test_ok_with_custom_message():
    """边界情况：ok 支持自定义 message（如业务提示）。"""
    result = ok([], message="没有合适的菜了")

    assert result.code == 200
    assert result.data == []
    assert result.message == "没有合适的菜了"


def test_error_returns_error_envelope():
    """正向路径：error 构造错误信封，data 为 None。"""
    result = error(500, "服务暂时不可用，请稍后重试")

    assert result.code == 500
    assert result.data is None
    assert result.message == "服务暂时不可用，请稍后重试"


def test_envelope_serializes_to_contract_shape():
    """边界情况：序列化结构与 api-conventions 定义一致。"""
    result = ok({"id": 1})

    assert result.model_dump() == {"code": 200, "data": {"id": 1}, "message": "ok"}


def test_envelope_missing_message_raises():
    """无效输入：缺少 message 字段时校验失败。"""
    with pytest.raises(ValidationError):
        Envelope(code=200, data=None)
