"""
结构化日志配置

提供统一的日志记录功能，支持控制台输出 + 文件轮转。
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import config


def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称，默认使用根记录器

    Returns:
        配置好的 Logger 实例
    """
    logger_name = name or "sport_reco"
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger

    level_name = config.get("logging.level", "INFO")
    log_format = config.get(
        "logging.format",
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.setLevel(getattr(logging, level_name, logging.INFO))

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)

    # 文件轮转处理器
    log_file = config.get("logging.file", "logs/app.log")
    project_root = config.project_root
    if project_root:
        log_path = Path(project_root) / log_file
    else:
        log_path = Path(log_file)

    log_path.parent.mkdir(parents=True, exist_ok=True)

    max_bytes = config.get("logging.max_bytes", 10 * 1024 * 1024)
    backup_count = config.get("logging.backup_count", 5)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器"""
    return setup_logging(name)
