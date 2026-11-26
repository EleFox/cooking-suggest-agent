"""并发隔离回归测试。

验证决策链路不会独占事件循环：决策的长时间阻塞调用在**专用线程池**中执行，
反向数据面（GET /api/recipes 等同步路由）仍可被正常调度。
"""

import asyncio
import threading
import time

from app.api.routes import decisions as decisions_route


async def test_decision_runs_in_dedicated_executor_thread(client, monkeypatch):
    """决策业务须在非事件循环线程、且属于 decision 专用线程池中执行。"""
    seen = {}

    def _capture(request):
        seen["thread"] = threading.current_thread()
        return []

    monkeypatch.setattr(decisions_route, "decide", _capture)

    response = await client.post(
        "/api/decisions",
        json={"count": 1, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 200
    thread = seen["thread"]
    assert thread is not threading.main_thread()
    assert thread.name.startswith("decision")


async def test_event_loop_stays_responsive_while_decision_blocks(client, monkeypatch):
    """决策在飞行期间事件循环必须保持可用（心跳不被长时间冻结）。"""
    started = threading.Event()
    release = threading.Event()

    def _blocking(request):
        started.set()
        release.wait(timeout=5)
        return []

    monkeypatch.setattr(decisions_route, "decide", _blocking)

    # 心跳：由事件循环自身持续刷新时间戳；用一个独立线程观测时间戳的最大停滞。
    state = {"t": time.perf_counter(), "worst_gap": 0.0}
    stop = threading.Event()

    def _monitor():
        while not stop.is_set():
            gap = time.perf_counter() - state["t"]
            state["worst_gap"] = max(state["worst_gap"], gap)
            time.sleep(0.005)

    async def _heartbeat():
        while True:
            state["t"] = time.perf_counter()
            await asyncio.sleep(0.005)

    monitor = threading.Thread(target=_monitor, daemon=True)
    monitor.start()
    heartbeat = asyncio.create_task(_heartbeat())

    decision = asyncio.create_task(
        client.post(
            "/api/decisions",
            json={"count": 1, "dedup_ids": [], "elements": []},
        )
    )

    for _ in range(1000):
        if started.is_set():
            break
        await asyncio.sleep(0.005)
    assert started.is_set()

    # 决策仍阻塞时，事件循环应继续刷新心跳。
    await asyncio.sleep(0.2)
    release.set()
    await asyncio.wait_for(decision, timeout=5)

    stop.set()
    heartbeat.cancel()
    monitor.join(timeout=1)

    # 事件循环被独占时心跳会停滞到决策结束（秒级）；阈值 0.5s 足以区分。
    assert state["worst_gap"] < 0.5
