"""
运动分析 Web 应用 - Flask 主入口

启动命令:
    python -m src.app --host 0.0.0.0 --port 5000 --cert ssl/cert.pem --key ssl/key.pem
"""

# ════════════════════════════════════════════════════════════════
# Bug1 修复: 必须在所有 import 之前执行 monkey-patch，
# 确保 socket、threading、ssl 等 stdlib 模块被正确 patch，
# 避免一个连接的阻塞操作影响其他连接（手机/电脑互斥问题）。
# ════════════════════════════════════════════════════════════════
from gevent import monkey
monkey.patch_all()

import argparse
import logging
import os
import signal
import ssl
import sys
import threading
from pathlib import Path

import gevent

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from flask import Flask
from flask_socketio import SocketIO

from src.core.config import config
from src.core.logging_config import setup_logging
from src.api.routes import api
from src.api.socket_handlers import (
    register_handlers,
    cleanup_all,
    disconnect_all_clients,
)
from src.data.database import db

# 初始化日志
logger = setup_logging("sport_reco")

# ════════════════════════════════════════════════════════════════
# Bug2 修复: 用 threading.Event 作为信号标志，
# 避免在 os._exit(0) 硬杀进程前丢失子资源清理。
# ════════════════════════════════════════════════════════════════
_shutdown_event = threading.Event()
# 保存 socketio 实例引用，供 _graceful_shutdown() 使用
_socketio_instance = None


def create_app() -> Flask:
    """创建 Flask 应用（工厂模式）"""
    app = Flask(
        __name__,
        template_folder=str(_project_root / "src" / "frontend" / "templates"),
        static_folder=str(_project_root / "src" / "frontend" / "static"),
    )

    # 基础配置
    secret_key = os.environ.get("FLASK_SECRET_KEY", "sport-reco-dev-key-change-me")
    app.config.update(
        SECRET_KEY=secret_key,
        DEBUG=config.debug,
    )

    # 注册蓝图
    app.register_blueprint(api)

    logger.debug(f"应用初始化完成 (debug={config.debug})")
    return app


def create_socketio(app: Flask) -> SocketIO:
    """创建 SocketIO 实例"""
    # 屏蔽 Flask/werkzeug 的 HTTP 访问日志（减少终端噪音）
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="gevent",
        ping_timeout=30,
        ping_interval=10,
        logger=False,
        engineio_logger=False,
    )

    register_handlers(socketio)
    return socketio


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="运动分析 Web 应用")
    parser.add_argument("--host", type=str, default=config.host)
    parser.add_argument("--port", type=int, default=config.port)
    parser.add_argument("--cert", type=str, default=None, help="SSL 证书路径")
    parser.add_argument("--key", type=str, default=None, help="SSL 私钥路径")
    parser.add_argument("--debug", action="store_true", default=config.debug)
    return parser.parse_args()


def _graceful_shutdown() -> None:
    """
    Bug2 修复: Ctrl+C / SIGTERM 安全关闭流程。

    原实现使用 os._exit(0) 直接硬杀进程，导致以下问题：
    1. Python atexit 钩子、__del__ 方法全部跳过
    2. SQLite 连接可能未正常关闭，WAL 日志残留
    3. 子 greenlet 被强制终止，无法释放资源

    新实现采用有序关闭流程：
    1. 设置关闭标志，防止重复执行
    2. 通知所有 WebSocket 客户端服务器即将关闭
    3. 断开所有客户端连接
    4. 刷新并关闭所有活跃采集器（确保传感器数据落盘）
    5. 关闭数据库连接
    6. 停止 gevent 事件循环（让 socketio.run() 正常返回）
    7. 等待短暂超时后若仍未退出，再 fallback 强制退出
    """
    # 防止重复关闭
    if _shutdown_event.is_set():
        logger.warning("关闭流程已在进行中，忽略重复信号")
        return
    _shutdown_event.set()

    logger.info("收到终止信号 (SIGINT/SIGTERM)，正在安全关闭...")

    def _do_shutdown():
        # 1. 断开所有 WebSocket 客户端连接
        if _socketio_instance is not None:
            n = disconnect_all_clients(_socketio_instance)
            if n > 0:
                logger.info(f"已断开 {n} 个 WebSocket 客户端")

        # 2. 清理采集器
        cleanup_all()

        # 3. 关闭数据库
        try:
            db.close()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库失败: {e}")

        # 4. 停止 gevent 事件循环
        hub = gevent.get_hub()
        if hub is not None:
            hub.loop.stop()
            logger.info("事件循环已停止")

        logger.info("服务器已安全关闭")

    # 在后台 greenlet 执行清理，然后停止事件循环
    gevent.spawn(_do_shutdown)

    # 兜底保护: 5 秒后若进程仍未退出，强制终止
    def _force_exit():
        gevent.sleep(5)
        if not _shutdown_event.is_set():
            return  # 已经完成正常退出
        logger.warning("安全关闭超时 (5s)，执行强制退出")
        os._exit(1)

    gevent.spawn(_force_exit)


def main():
    """主函数"""
    global _socketio_instance

    args = parse_args()

    # ════════════════════════════════════════════════════════════
    # Bug2 修复: 注册信号处理器
    # 使用 gevent.signal_handler 而非 signal.signal，
    # 确保信号在 gevent 事件循环中正确处理。
    # ════════════════════════════════════════════════════════════
    gevent.signal_handler(signal.SIGINT, _graceful_shutdown)
    gevent.signal_handler(signal.SIGTERM, _graceful_shutdown)

    app = create_app()
    socketio = create_socketio(app)
    _socketio_instance = socketio

    # 确定 SSL 上下文
    ssl_context = None
    cert_file = args.cert or os.environ.get("SSL_CERT")
    key_file = args.key or os.environ.get("SSL_KEY")

    if cert_file and key_file:
        cert_path = Path(cert_file)
        key_path = Path(key_file)

        # 解析为绝对路径
        abs_cert = str(_project_root / cert_path) if not cert_path.is_absolute() else str(cert_path)
        abs_key = str(_project_root / key_path) if not key_path.is_absolute() else str(key_path)

        for p in [abs_cert, abs_key]:
            if not os.path.exists(p):
                logger.error(f"SSL 文件不存在: {p}")
                sys.exit(1)

        # gevent 26.x+ 的 WSGIServer 要求 ssl.SSLContext 对象
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=abs_cert, keyfile=abs_key)
        logger.info(f"HTTPS 模式: cert={abs_cert}")

    logger.info(f"服务器启动: https://{args.host}:{args.port}")
    logger.info(
        "=" * 50 + "\n"
        f"  运动分析平台 v{config.get('app.version', '0.1.0')}\n"
        f"  Dashboard: https://{args.host}:{args.port}/\n"
        f"  Mobile:    https://{args.host}:{args.port}/mobile\n"
        f"  模型标签:  {', '.join(config.get('model.labels', []))}\n"
        f"  日志级别:  {config.get('logging.level', 'INFO')}\n"
        "=" * 50
    )

    try:
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            ssl_context=ssl_context,
            debug=args.debug,
            use_reloader=False,  # Bug1: gevent 下禁用 reloader，避免 fork 导致连接冲突
            allow_unsafe_werkzeug=True,
        )
    except KeyboardInterrupt:
        # socketio.run() 可能不会捕获 gevent-context 中的 KeyboardInterrupt，
        # 这里作为兜底处理
        logger.info("收到 KeyboardInterrupt")
        _graceful_shutdown()
    finally:
        logger.info("服务器已停止")
        # 确保事件被设置，以便 _force_exit 知道已完成
        _shutdown_event.set()


if __name__ == "__main__":
    main()
