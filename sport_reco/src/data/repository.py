"""
仓库模式（Repository Pattern）封装

在 Database 原始操作之上提供面向业务的数据访问接口，
隔离业务逻辑与 SQL 细节。
"""

from typing import List, Optional

import numpy as np

from .database import db


class SensorRepository:
    """传感器数据仓库"""

    @staticmethod
    def save_batch(session_id: int, records: List[dict]) -> int:
        """
        批量保存传感器记录

        Args:
            session_id: 会话ID
            records: [{"timestamp": ts, "acc_x": ..., ...}, ...]

        Returns:
            保存的记录数
        """
        rows = []
        for r in records:
            rows.append((
                r.get("timestamp", 0),
                r.get("acc_x", 0), r.get("acc_y", 0), r.get("acc_z", 0),
                r.get("gyro_x", 0), r.get("gyro_y", 0), r.get("gyro_z", 0),
                r.get("lat"), r.get("lng"),
            ))
        if rows:
            db.insert_sensor_batch(session_id, rows)
        return len(rows)

    @staticmethod
    def get_as_numpy(session_id: int) -> dict:
        """
        获取会话数据并转换为 numpy 数组

        Returns:
            {
                "timestamps": ndarray,
                "acc": ndarray (N x 3),
                "gyro": ndarray (N x 3),
                "gps": ndarray (N x 2) or None
            }
        """
        rows = db.get_session_sensor_data(session_id)
        if not rows:
            return {
                "timestamps": np.array([]),
                "acc": np.array([]).reshape(0, 3),
                "gyro": np.array([]).reshape(0, 3),
                "gps": None,
            }

        n = len(rows)
        timestamps = np.zeros(n)
        acc = np.zeros((n, 3))
        gyro = np.zeros((n, 3))
        gps_data = []

        for i, r in enumerate(rows):
            timestamps[i] = r["timestamp"]
            acc[i] = [r["acc_x"] or 0, r["acc_y"] or 0, r["acc_z"] or 0]
            gyro[i] = [r["gyro_x"] or 0, r["gyro_y"] or 0, r["gyro_z"] or 0]
            if r["lat"] is not None and r["lng"] is not None:
                gps_data.append((r["lat"], r["lng"]))

        return {
            "timestamps": timestamps,
            "acc": acc,
            "gyro": gyro,
            "gps": np.array(gps_data) if gps_data else None,
        }


class SessionRepository:
    """会话仓库"""

    @staticmethod
    def create(label: str = "unknown") -> int:
        return db.create_session(label)

    @staticmethod
    def end(session_id: int) -> bool:
        return db.end_session(session_id)

    @staticmethod
    def get_recent(limit: int = 20) -> list:
        return db.get_sessions(limit)


class InferenceRepository:
    """推理结果仓库"""

    @staticmethod
    def save(
        session_id: int,
        timestamp: float,
        label: str,
        confidence: float,
        features: Optional[dict] = None,
    ) -> None:
        db.insert_inference(
            session_id=session_id,
            timestamp=timestamp,
            predicted_label=label,
            confidence=confidence,
            feature_snapshot=features,
        )

    @staticmethod
    def save_manual_correction(
        session_id: int, timestamp: float, corrected_label: str
    ) -> None:
        db.insert_manual_correction(session_id, timestamp, corrected_label)

    @staticmethod
    def get_session_history(session_id: int) -> list:
        return db.get_session_inferences(session_id)
