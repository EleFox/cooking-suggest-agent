"""应用入口启动逻辑测试。"""

from unittest.mock import patch

from app.main import run, settings


@patch("uvicorn.run")
def test_run_starts_with_settings(mock_run):
    """正向路径：run 按配置读取 host/port/reload 启动 uvicorn。"""
    run()

    mock_run.assert_called_once_with(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
    )


@patch("uvicorn.run")
def test_run_starts_multiple_times(mock_run):
    """边界情况：run 可重复调用，每次都启动新的 uvicorn。"""
    run()
    run()

    assert mock_run.call_count == 2


@patch("uvicorn.run")
def test_run_uses_app_main_as_entry(mock_run):
    """无效输入校验：启动目标固定指向 app.main 模块的应用对象。"""
    run()

    entry = mock_run.call_args.args[0]
    assert entry == "app.main:app"
