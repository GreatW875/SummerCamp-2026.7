"""
SQLite 数据库操作封装

使用 sqlite3 原生模块，提供连接管理、表初始化、
CRUD 操作和连接池能力。所有写操作自动提交，读操作
使用 WAL 模式提升并发性能。
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.config import config
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class Database:
    """SQLite 数据库管理器（线程安全）"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = config.get("database.path", "sport_reco.db")

        # 支持相对于项目根目录的路径
        project_root = config.project_root
        if project_root and not Path(db_path).is_absolute():
            db_path = str(Path(project_root) / db_path)

        self.db_path = db_path
        self._local = threading.local()
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # 写前日志，提升并发
            conn.execute("PRAGMA foreign_keys=ON")  # 启用外键
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def _cursor(self):
        """获取游标的上下文管理器（自动提交）"""
        conn = self._get_connection()
        try:
            yield conn.cursor()
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_tables(self) -> None:
        """初始化数据库表结构"""
        ddl = """
        -- 运动会话表
        CREATE TABLE IF NOT EXISTS sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            label         TEXT NOT NULL DEFAULT 'unknown',
            manual_label  TEXT,
            start_time    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            end_time      TIMESTAMP,
            duration_s    REAL,
            total_samples INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'active'  -- active / completed / error
        );

        -- 传感器数据表（原始采集记录）
        CREATE TABLE IF NOT EXISTS sensor_data (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            timestamp  REAL NOT NULL,   -- Unix 时间戳（秒）
            acc_x      REAL,
            acc_y      REAL,
            acc_z      REAL,
            gyro_x     REAL,
            gyro_y     REAL,
            gyro_z     REAL,
            lat        REAL,
            lng        REAL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        -- 推理结果表
        CREATE TABLE IF NOT EXISTS inference_results (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   INTEGER NOT NULL,
            timestamp    REAL NOT NULL,
            predicted_label TEXT NOT NULL,
            confidence   REAL,
            is_manual    INTEGER DEFAULT 0,
            feature_snapshot TEXT,  -- JSON 格式特征向量快照
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_sensor_session
            ON sensor_data(session_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_inference_session
            ON inference_results(session_id, timestamp);
        """
        conn = self._get_connection()
        conn.executescript(ddl)
        conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    # ---- 会话操作 ----

    def create_session(self, label: str = "unknown") -> int:
        """创建新的运动会话"""
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (label, start_time, status) VALUES (?, ?, 'active')",
                (label, datetime.now().isoformat()),
            )
            session_id = cur.lastrowid
        logger.info(f"会话创建: id={session_id}, label={label}")
        return session_id

    def end_session(self, session_id: int) -> bool:
        """结束运动会话"""
        with self._cursor() as cur:
            # 计算时长和样本数
            row = cur.execute(
                "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) "
                "FROM sensor_data WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            duration = (row[1] - row[0]) if row and row[0] and row[1] else 0

            cur.execute(
                "UPDATE sessions SET end_time=?, duration_s=?, "
                "total_samples=?, status='completed' WHERE id=?",
                (datetime.now().isoformat(), duration, row[2] if row else 0, session_id),
            )
        logger.info(f"会话结束: id={session_id}, duration={duration:.1f}s")
        return True

    def get_sessions(self, limit: int = 20) -> list:
        """获取最近的会话列表"""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT id, label, manual_label, start_time, end_time, "
            "duration_s, total_samples, status "
            "FROM sessions ORDER BY start_time DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 传感器数据操作 ----

    def insert_sensor_data(
        self,
        session_id: int,
        timestamp: float,
        acc_x: float, acc_y: float, acc_z: float,
        gyro_x: float, gyro_y: float, gyro_z: float,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> None:
        """插入单条传感器数据"""
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO sensor_data "
                "(session_id, timestamp, acc_x, acc_y, acc_z, "
                "gyro_x, gyro_y, gyro_z, lat, lng) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, timestamp, acc_x, acc_y, acc_z,
                 gyro_x, gyro_y, gyro_z, lat, lng),
            )

    def insert_sensor_batch(
        self, session_id: int, rows: list
    ) -> None:
        """批量插入传感器数据"""
        with self._cursor() as cur:
            cur.executemany(
                "INSERT INTO sensor_data "
                "(session_id, timestamp, acc_x, acc_y, acc_z, "
                "gyro_x, gyro_y, gyro_z, lat, lng) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(session_id, *row) for row in rows],
            )

    def get_session_sensor_data(
        self, session_id: int, limit: Optional[int] = None
    ) -> list:
        """获取会话的传感器数据"""
        conn = self._get_connection()
        query = (
            "SELECT timestamp, acc_x, acc_y, acc_z, "
            "gyro_x, gyro_y, gyro_z, lat, lng "
            "FROM sensor_data WHERE session_id = ? ORDER BY timestamp"
        )
        if limit:
            query += f" LIMIT {int(limit)}"
        rows = conn.execute(query, (session_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- 推理结果操作 ----

    def insert_inference(
        self,
        session_id: int,
        timestamp: float,
        predicted_label: str,
        confidence: float,
        is_manual: bool = False,
        feature_snapshot: Optional[dict] = None,
    ) -> None:
        """插入推理结果"""
        snapshot_str = json.dumps(feature_snapshot) if feature_snapshot else None
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO inference_results "
                "(session_id, timestamp, predicted_label, confidence, "
                "is_manual, feature_snapshot) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, timestamp, predicted_label, confidence,
                 int(is_manual), snapshot_str),
            )

    def get_session_inferences(self, session_id: int) -> list:
        """获取会话的推理结果"""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT timestamp, predicted_label, confidence, is_manual "
            "FROM inference_results WHERE session_id = ? "
            "ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def insert_manual_correction(
        self,
        session_id: int,
        timestamp: float,
        corrected_label: str,
    ) -> None:
        """插入人工纠正记录（作为标注数据源）"""
        self.insert_inference(
            session_id=session_id,
            timestamp=timestamp,
            predicted_label=corrected_label,
            confidence=1.0,
            is_manual=True,
        )

    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# 全局数据库实例
db = Database()
