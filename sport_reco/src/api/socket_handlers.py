"""
WebSocket 事件处理

处理手机端与电脑端的双向实时通信：
- 手机端：传感器数据上传、会话控制
- 电脑端：实时推理结果推送、状态同步

════════════════════════════════════════════════════════════
Bug1 修复: 使用 Socket.IO 房间隔离移动端与桌面端，
避免 broadcast=True 在高频数据流下导致事件循环饥饿。
同时在高频 handler 中插入 gevent.sleep(0) 主动让出
执行权，确保其他 greenlet（如另一客户端连接）不被饿死。
════════════════════════════════════════════════════════════
"""

import time
from typing import Dict, Optional

import gevent
from flask import request
from flask_socketio import emit, join_room

from src.core.config import config
from src.core.logging_config import get_logger
from src.data.repository import SessionRepository
from src.service.collector import DataCollector
from src.service.inference import get_inference_engine

logger = get_logger(__name__)

# 活跃的采集器实例（按 session_id）
_active_collectors: Dict[int, DataCollector] = {}

# 全局推理间隔计时器
_last_inference_times: Dict[int, float] = {}

# Socket.IO 房间名常量
ROOM_DASHBOARD = "dashboard"
ROOM_MOBILE = "mobile"

# ── 高频事件计数器（用于自适应 yield） ──
_event_batch_counter: Dict[str, int] = {}
_EVENT_YIELD_THRESHOLD = 20  # 每处理 N 个高频事件后主动 yield


def _maybe_yield(event_name: str) -> None:
    """
    高频事件处理中主动让出 gevent 执行权。

    当大量传感器数据涌入时，如果不主动 yield，当前 greenlet
    可能长时间占用 CPU，导致其他客户端（如 Dashboard）的
    Socket.IO 心跳/事件得不到处理，出现"互斥"症状。
    """
    cnt = _event_batch_counter.get(event_name, 0) + 1
    _event_batch_counter[event_name] = cnt
    if cnt % _EVENT_YIELD_THRESHOLD == 0:
        gevent.sleep(0)


def register_handlers(socketio) -> None:
    """注册所有 WebSocket 事件处理器"""

    @socketio.on("connect")
    def handle_connect():
        """
        客户端连接 — 按 URL 来源自动分配到对应房间。

        通过 HTTP Referer 或 User-Agent 推断客户端类型：
        - 来自 /mobile 的请求 → mobile 房间
        - 其他（/ 首页）→ dashboard 房间
        """
        client_ip = request.remote_addr
        referer = request.headers.get("Referer", "")
        user_agent = request.headers.get("User-Agent", "").lower()

        # 判断客户端类型
        if "/mobile" in referer or "mobile" in user_agent:
            client_type = "mobile"
            room = ROOM_MOBILE
        else:
            client_type = "dashboard"
            room = ROOM_DASHBOARD

        join_room(room)
        logger.debug(
            f"客户端连接: {client_ip} "
            f"(类型={client_type}, 房间={room})"
        )

        emit("server_status", {
            "status": "connected",
            "server_time": time.time(),
            "active_sessions": len(_active_collectors),
            "client_type": client_type,
        })

    @socketio.on("disconnect")
    def handle_disconnect():
        """客户端断开"""
        logger.debug(f"客户端断开: {request.remote_addr}")

    # =====================================================
    #  手机端事件
    # =====================================================

    @socketio.on("mobile:start_session")
    def handle_start_session(data: dict):
        """
        手机端开始运动会话

        data: {"label": "walking" | "running" | ... }
        """
        label = data.get("label", "unknown") if data else "unknown"
        session_id = SessionRepository.create(label)
        collector = DataCollector(session_id)
        _active_collectors[session_id] = collector

        logger.debug(f"会话开始: id={session_id}, label={label}")
        emit("mobile:session_started", {
            "session_id": session_id,
            "label": label,
            "start_time": time.time(),
        })
        # 通知电脑端 Dashboard 房间有新会话
        emit("dashboard:new_session", {
            "session_id": session_id,
            "label": label,
            "start_time": time.time(),
            "status": "active",
        }, room=ROOM_DASHBOARD)

    @socketio.on("mobile:sensor_data")
    def handle_sensor_data(data: dict):
        """
        手机端上传传感器数据（高频，可达 30-50Hz）

        data: {
            "session_id": int,
            "timestamp": float,
            "acc_x/y/z": float,
            "gyro_x/y/z": float,
            "lat"?: float, "lng"?: float
        }

        Bug1 关键修复点：
        1. 高频循环中主动 gevent.sleep(0) 让出执行权
        2. 使用 room 定向广播代替 broadcast=True
        """
        # ── 高频事件主动 yield ──
        _maybe_yield("mobile:sensor_data")

        session_id = data.get("session_id")
        if session_id not in _active_collectors:
            logger.warning(f"未知会话: {session_id}")
            return

        collector = _active_collectors[session_id]
        ok = collector.ingest(data)
        if not ok:
            return  # 数据校验不通过

        # 推理节流控制
        now = time.time()
        interval = config.get("websocket.inference_interval", 1.0)
        last_time = _last_inference_times.get(session_id, 0)

        if now - last_time >= interval and collector.is_buffer_ready:
            window = collector.get_window()
            if window:
                engine = get_inference_engine()
                if engine.is_loaded:
                    result = engine.classify_and_save(
                        session_id=session_id,
                        acc_window=window["acc"],
                        gyro_window=window["gyro"],
                        timestamp=now,
                    )
                    # ── Bug1 修复: 定向推送到 dashboard + mobile 两个房间 ──
                    inference_payload = {
                        "session_id": session_id,
                        "timestamp": now,
                        **result,
                    }
                    # Dashboard 房间：电脑端实时分类展示
                    emit("dashboard:inference_result", inference_payload,
                         room=ROOM_DASHBOARD)
                    # Mobile 房间：手机端同步显示当前识别结果
                    emit("dashboard:inference_result", inference_payload,
                         room=ROOM_MOBILE)

                _last_inference_times[session_id] = now

        # 波形数据 + GPS 坐标转发给电脑端 — 定向推送到 dashboard 房间
        emit("dashboard:sensor_stream", {
            "session_id": session_id,
            "timestamp": data.get("timestamp"),
            "acc_x": data.get("acc_x"),
            "acc_y": data.get("acc_y"),
            "acc_z": data.get("acc_z"),
            "gyro_x": data.get("gyro_x"),
            "gyro_y": data.get("gyro_y"),
            "gyro_z": data.get("gyro_z"),
            "lat": data.get("lat"),
            "lng": data.get("lng"),
        }, room=ROOM_DASHBOARD)

    @socketio.on("mobile:gait_params")
    def handle_gait_params(data: dict):
        """
        手机端定时上报步态参数（步频/速度/距离/步数）
        服务端不做计算，直接透传到 Dashboard 确保两端数据一致

        data: {
            "session_id": int,
            "cadence": float (步/分),
            "speed": float (km/h),
            "distance": float (米),
            "steps": int,
            "duration_s": int,
            "is_static": bool,
        }
        """
        _maybe_yield("mobile:gait_params")
        session_id = data.get("session_id")
        if session_id not in _active_collectors:
            return

        emit("dashboard:gait_params", {
            "session_id": session_id,
            "cadence": data.get("cadence", 0),
            "speed": data.get("speed", 0),
            "distance": data.get("distance", 0),
            "steps": data.get("steps", 0),
            "duration_s": data.get("duration_s", 0),
            "is_static": data.get("is_static", False),
        }, room=ROOM_DASHBOARD)

    @socketio.on("mobile:end_session")
    def handle_end_session(data: dict):
        """
        手机端结束运动会话

        data: {"session_id": int}
        """
        session_id = data.get("session_id") if data else None
        if not session_id:
            return

        collector = _active_collectors.pop(session_id, None)
        if collector:
            collector.close()

        SessionRepository.end(session_id)
        _last_inference_times.pop(session_id, None)

        logger.debug(f"会话结束: id={session_id}")
        emit("mobile:session_ended", {"session_id": session_id})
        emit("dashboard:session_ended", {
            "session_id": session_id,
            "end_time": time.time(),
        }, room=ROOM_DASHBOARD)

    # =====================================================
    #  电脑端 Dashboard 事件
    # =====================================================

    @socketio.on("dashboard:request_history")
    def handle_request_history(data: dict):
        """Dashboard 请求历史会话列表"""
        sessions = SessionRepository.get_recent(20)
        emit("dashboard:history", {"sessions": sessions})

    @socketio.on("dashboard:manual_correction")
    def handle_manual_correction(data: dict):
        """
        Dashboard 手动纠正运动类型

        data: {"session_id": int, "label": str}
        """
        session_id = data.get("session_id")
        label = data.get("label")
        if not session_id or not label:
            return

        engine = get_inference_engine()
        if engine.is_loaded:
            engine.manual_correct(session_id, time.time(), label)

        logger.debug(f"人工纠正: session={session_id}, label={label}")
        emit("dashboard:correction_saved", {
            "session_id": session_id,
            "label": label,
            "timestamp": time.time(),
        })

    logger.info("WebSocket 事件处理器已就绪")


def cleanup_all() -> None:
    """安全关闭所有活跃采集器，释放资源（供信号处理器调用）"""
    closed = 0
    for sid, collector in list(_active_collectors.items()):
        try:
            collector.close()
            closed += 1
        except Exception as e:
            logger.error(f"关闭采集器 {sid} 失败: {e}")

    _active_collectors.clear()
    _last_inference_times.clear()
    if closed > 0:
        logger.info(f"已安全关闭 {closed} 个活跃采集器")


def disconnect_all_clients(socketio) -> int:
    """
    断开所有已连接客户端（优雅关闭用）。

    遍历当前所有连接的 sid，逐个发送断开通知并关闭连接。
    返回断开的客户端数量。
    """
    try:
        # 通过 engineio 内部的 _server 或 socketio.server 获取连接
        # gevent-socketio / flask-socketio 中可以通过 get_all_sids() 等方式
        if hasattr(socketio, 'server') and hasattr(socketio.server, 'manager'):
            rooms = socketio.server.manager.get_rooms()
            if rooms:
                sids = set()
                for room, clients in rooms.items():
                    sids.update(clients)
                for sid in sids:
                    try:
                        emit("server_shutdown", {"message": "服务器正在关闭"},
                             room=sid)
                    except Exception:
                        pass
                    try:
                        socketio.server.disconnect(sid)
                    except Exception:
                        pass
                return len(sids)
    except Exception as e:
        logger.warning(f"断开客户端时出错（可忽略）: {e}")
    return 0
