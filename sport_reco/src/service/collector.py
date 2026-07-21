"""
实时数据采集服务

管理实时数据流的接收、缓冲、校验与批量写入。
前端通过 WebSocket 推送传感器数据，此模块负责：
- 数据校验（范围检查、NaN 检测）
- 环形缓冲区管理（用于滑窗推理）
- 批量写入数据库（降低 I/O 压力）
"""

import time
from collections import deque
from typing import Deque, Dict, List, Optional

import numpy as np

from src.core.config import config
from src.core.logging_config import get_logger
from src.data.repository import SensorRepository

logger = get_logger(__name__)


class DataCollector:
    """
    单会话数据采集器

    管理一个运动会话的实时数据流，提供环形缓冲
    用于滑动窗口特征提取。
    """

    # 传感器有效范围
    VALID_RANGES = {
        "acc_x": (-40, 40),      # m/s² (正常运动 ±4g)
        "acc_y": (-40, 40),
        "acc_z": (-40, 40),
        "gyro_x": (-2000, 2000), # deg/s
        "gyro_y": (-2000, 2000),
        "gyro_z": (-2000, 2000),
        "lat": (-90, 90),
        "lng": (-180, 180),
    }

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.start_time = time.time()
        self.total_samples = 0
        self.dropped_samples = 0

        # 环形缓冲区配置
        sample_rate = config.get("preprocess.filter.sample_rate", 50.0)
        window_sec = config.get("preprocess.window.size_seconds", 2.0)
        buffer_sec = config.get("websocket.window_seconds", 2.0) * 3  # 3x 窗口做缓冲

        self.buffer_size = int(buffer_sec * sample_rate)
        self.window_samples = int(window_sec * sample_rate)

        # 6 通道环形缓冲区
        self._buffer: Deque[np.ndarray] = deque(maxlen=self.buffer_size)

        # 批量写入暂存
        self._write_batch: List[tuple] = []
        self._batch_size = 50  # 每 50 条批量写入一次
        self._last_write_time = time.time()
        self._write_interval = 2.0  # 最长 2 秒必须落盘

    def ingest(self, record: dict) -> bool:
        """
        接收并校验单条传感器记录

        Args:
            record: {"timestamp", "acc_x", "acc_y", "acc_z",
                      "gyro_x", "gyro_y", "gyro_z", "lat"?, "lng"?}

        Returns:
            是否成功接收
        """
        # 校验
        if not self._validate(record):
            self.dropped_samples += 1
            return False

        # 提取 6 通道数据写入环形缓冲
        sample = np.array([
            record.get("acc_x", 0),
            record.get("acc_y", 0),
            record.get("acc_z", 0),
            record.get("gyro_x", 0),
            record.get("gyro_y", 0),
            record.get("gyro_z", 0),
        ], dtype=np.float64)

        self._buffer.append(sample)
        self.total_samples += 1

        # 批量写入暂存
        self._write_batch.append((
            record.get("timestamp", time.time()),
            record.get("acc_x", 0), record.get("acc_y", 0), record.get("acc_z", 0),
            record.get("gyro_x", 0), record.get("gyro_y", 0), record.get("gyro_z", 0),
            record.get("lat"), record.get("lng"),
        ))

        # 触发批量写入
        if (len(self._write_batch) >= self._batch_size or
                time.time() - self._last_write_time >= self._write_interval):
            self._flush()

        return True

    def _validate(self, record: dict) -> bool:
        """校验数据有效性"""
        for field, (lo, hi) in self.VALID_RANGES.items():
            val = record.get(field)
            if val is None:
                continue
            if not isinstance(val, (int, float)):
                return False
            if np.isnan(val) or np.isinf(val):
                return False
            if val < lo or val > hi:
                return False
        return True

    def _flush(self) -> None:
        """批量写入数据库"""
        if not self._write_batch:
            return
        try:
            SensorRepository.save_batch(self.session_id, [
                {
                    "timestamp": r[0], "acc_x": r[1], "acc_y": r[2], "acc_z": r[3],
                    "gyro_x": r[4], "gyro_y": r[5], "gyro_z": r[6],
                    "lat": r[7], "lng": r[8],
                }
                for r in self._write_batch
            ])
        except Exception as e:
            logger.error(f"批量写入失败: {e}")
        finally:
            self._write_batch.clear()
            self._last_write_time = time.time()

    def get_window(self) -> Optional[Dict[str, np.ndarray]]:
        """
        获取当前滑动窗口数据（用于推理）

        Returns:
            {"acc": ndarray (N,3), "gyro": ndarray (N,3)} 或 None（数据不足）
        """
        if len(self._buffer) < self.window_samples // 4:
            return None  # 至少需要 1/4 窗口的数据

        # 取最近 window_samples 条
        recent = list(self._buffer)[-self.window_samples:]
        data = np.array(recent)

        return {
            "acc": data[:, :3],
            "gyro": data[:, 3:],
        }

    @property
    def is_buffer_ready(self) -> bool:
        """缓冲区是否有足够数据用于推理"""
        return len(self._buffer) >= self.window_samples // 2

    @property
    def stats(self) -> dict:
        """采集统计信息"""
        return {
            "session_id": self.session_id,
            "total_samples": self.total_samples,
            "dropped_samples": self.dropped_samples,
            "buffer_size": len(self._buffer),
            "elapsed_s": time.time() - self.start_time,
            "sample_rate_hz": (self.total_samples / max(time.time() - self.start_time, 0.1)),
        }

    def close(self) -> None:
        """关闭采集器，确保数据落盘"""
        self._flush()
