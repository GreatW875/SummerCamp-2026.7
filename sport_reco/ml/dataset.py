"""
数据集加载与划分模块

支持:
- 从CSV文件加载真实数据
- 合成数据生成（用于原型测试）
- 特征提取管线（使用 core 层的唯一真源）
- 训练/验证/测试集划分
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# 确保项目根在 path 中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.core.config import config
from src.core.features import (
    CHANNEL_NAMES,
    extract_feature_vector,
    get_feature_dimension,
)
from src.core.preprocess import preprocess_pipeline, sliding_window
from src.core.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================
#  合成数据生成
# ============================================================

def generate_synthetic_data(
    n_samples: int = 4000,
    fs: float = 50.0,
    noise_std: float = 0.1,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    生成合成 IMU 数据用于运动分类识别

    每类运动的 IMU 模式特征:
    - walking:  规律低频 1.5-2Hz, 小振幅加速度
    - running:  较高频率 2.5-3Hz, 中等振幅

    Returns:
        (acc_windows, gyro_windows, labels, label_names, feature_matrix)
    """
    rng = np.random.RandomState(random_state)
    window_size = int(2.0 * fs)  # 2秒窗口

    patterns = {
        "walking": {
            "freq": (1.5, 2.0),
            "acc_amp": (0.5, 1.5),
            "gyro_amp": (20, 50),
            "acc_z_base": 9.8,
            "duty_cycle": 1.0,
        },
        "running": {
            "freq": (2.5, 3.0),
            "acc_amp": (1.5, 4.0),
            "gyro_amp": (50, 120),
            "acc_z_base": 9.8,
            "duty_cycle": 1.0,
        },
    }

    label_names = list(patterns.keys())
    acc_windows = []
    gyro_windows = []
    labels = []

    n_per_class = n_samples // len(label_names)

    for class_idx, (label, params) in enumerate(patterns.items()):
        for _ in range(n_per_class):
            freq = rng.uniform(*params["freq"])
            acc_amp = rng.uniform(*params["acc_amp"])
            gyro_amp = rng.uniform(*params["gyro_amp"])
            acc_z_base = params["acc_z_base"]
            duty = params["duty_cycle"]

            # 生成 2秒窗口的数据
            t = np.arange(0, 2.0, 1.0 / fs)
            n = len(t)

            # 基础波形
            base_x = np.sin(2 * np.pi * freq * t)
            base_y = np.cos(2 * np.pi * freq * t) * 0.6
            base_z = np.abs(np.sin(2 * np.pi * freq * t))

            # 连续运动
            active = np.ones(n)
            if duty < 1.0:
                cycle_period = int(fs / freq)
                for j in range(0, n, cycle_period):
                    active_end = min(j + int(cycle_period * duty), n)
                    if active_end > j:
                        active[active_end:] = 0
                        if j + cycle_period < n:
                            active[j + cycle_period:] = 1

            acc_w = np.column_stack([
                base_x * acc_amp * active + rng.randn(n) * noise_std,
                base_y * acc_amp * 0.5 * active + rng.randn(n) * noise_std,
                base_z * acc_amp * 0.7 * active + acc_z_base + rng.randn(n) * noise_std,
            ])

            gyro_w = np.column_stack([
                base_x * gyro_amp * 0.7 + rng.randn(n) * noise_std * 5,
                base_y * gyro_amp * 0.5 + rng.randn(n) * noise_std * 5,
                base_z * gyro_amp * 0.3 + rng.randn(n) * noise_std * 3,
            ])

            acc_windows.append(acc_w)
            gyro_windows.append(gyro_w)
            labels.append(class_idx)

    logger.info(
        f"合成数据生成完成: {len(acc_windows)} 窗口, "
        f"类别分布={dict(zip(label_names, [labels.count(i) for i in range(len(label_names))]))}"
    )
    return acc_windows, gyro_windows, np.array(labels), label_names, None


# ============================================================
#  数据加载与特征提取
# ============================================================

def load_from_csv(
    csv_path: str,
    label_col: str = "label",
    window_size: Optional[int] = None,
    step_size: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    从 CSV 文件加载传感器数据并提取特征

    期望 CSV 列: acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, label

    Returns:
        (acc_w, gyro_w, labels_idx, label_names, feature_matrix)
    """
    df = pd.read_csv(csv_path)

    required_cols = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少必要列: {missing}")

    # 提取标签
    if label_col in df.columns:
        le = LabelEncoder()
        labels_idx = le.fit_transform(df[label_col])
        label_names = list(le.classes_)
    else:
        labels_idx = np.zeros(len(df), dtype=int)
        label_names = ["unknown"]

    acc = df[["acc_x", "acc_y", "acc_z"]].values.astype(np.float64)
    gyro = df[["gyro_x", "gyro_y", "gyro_z"]].values.astype(np.float64)

    # 预处理
    acc_p, gyro_p = preprocess_pipeline(acc, gyro, apply_filter=True)

    # 滑窗
    ws = window_size or config.get("preprocess.window.size", 100)
    ss = step_size or config.get("preprocess.window.step", 50)

    acc_windows = sliding_window(acc_p, ws, ss)
    gyro_windows = sliding_window(gyro_p, ws, ss)

    # 标签也做同样的滑窗（取众数）
    window_labels = []
    for start in range(0, len(labels_idx) - ws + 1, ss):
        wl = labels_idx[start:start + ws]
        # 取众数
        counts = np.bincount(wl)
        window_labels.append(int(np.argmax(counts)))

    # 对齐窗口数
    min_len = min(len(acc_windows), len(gyro_windows), len(window_labels))
    acc_windows = acc_windows[:min_len]
    gyro_windows = gyro_windows[:min_len]
    window_labels = window_labels[:min_len]

    logger.info(
        f"CSV数据加载: {len(df)} 行 → {min_len} 窗口, "
        f"类别={label_names}"
    )
    return acc_windows, gyro_windows, np.array(window_labels), label_names, None


def extract_features(
    acc_windows: List[np.ndarray],
    gyro_windows: List[np.ndarray],
) -> np.ndarray:
    """
    从窗口列表批量提取特征矩阵
    """
    features = []
    n = min(len(acc_windows), len(gyro_windows))

    for i in range(n):
        try:
            fv, _ = extract_feature_vector(acc_windows[i], gyro_windows[i])
            features.append(fv)
        except Exception as e:
            logger.warning(f"窗口 {i} 特征提取失败: {e}")
            continue

    if not features:
        raise ValueError("没有成功提取任何特征向量")

    feature_matrix = np.vstack(features)
    logger.info(f"特征提取完成: {feature_matrix.shape}")
    return feature_matrix


# ============================================================
#  数据集划分
# ============================================================

def split_data(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float = 0.2,
    val_size: float = 0.0,
    random_state: int = 42,
    stratify: bool = True,
) -> Dict[str, np.ndarray]:
    """
    划分训练/验证/测试集

    Returns:
        {"X_train", "X_val", "X_test", "y_train", "y_val", "y_test"}
    """
    result = {}

    # 先分出测试集
    stratify_y = y if stratify else None
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify_y
    )

    if val_size > 0:
        val_ratio = val_size / (1 - test_size)
        stratify_temp = y_temp if stratify else None
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_ratio,
            random_state=random_state, stratify=stratify_temp,
        )
        result["X_val"] = X_val
        result["y_val"] = y_val
    else:
        X_train, y_train = X_temp, y_temp

    result.update({
        "X_train": X_train, "y_train": y_train,
        "X_test": X_test, "y_test": y_test,
    })

    logger.info(
        f"数据划分: train={X_train.shape[0]}, "
        f"test={X_test.shape[0]}"
        + (f", val={X_val.shape[0]}" if val_size > 0 else "")
    )
    return result


def build_dataset(
    data_source: str = "synthetic",
    csv_path: Optional[str] = None,
    n_samples: int = 4000,
    test_size: float = 0.2,
) -> Tuple[Dict, List[str], int]:
    """
    一站式数据集构建

    Args:
        data_source: "synthetic" 或 "csv"
        csv_path: CSV 文件路径 (data_source="csv" 时需要)
        n_samples: 合成数据样本数

    Returns:
        (split_data_dict, label_names, n_features)
    """
    # 1. 加载数据
    if data_source == "csv" and csv_path:
        acc_w, gyro_w, labels, label_names, _ = load_from_csv(csv_path)
    else:
        acc_w, gyro_w, labels, label_names, _ = generate_synthetic_data(n_samples)

    # 2. 特征提取
    X = extract_features(acc_w, gyro_w)

    # 3. 划分
    split = split_data(X, labels, test_size=test_size)

    logger.info(f"数据集构建完成: 特征维度={X.shape[1]}, 类别={label_names}")
    return split, label_names, X.shape[1]
