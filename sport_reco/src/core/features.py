"""
特征提取模块

从传感器窗口数据中提取时域和频域特征。
此模块是训练和推理的「唯一真源」，必须保持一致性。

特征维度（每窗口、每通道）：
- 时域：10 维
- 频域：5 + 3 (频带能量) = 8 维
- 总计：18维/通道 × 6通道 = 108 维 + 3 组合特征 = 111 维
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.fft import fft, fftfreq
from scipy.stats import iqr as scipy_iqr

from .config import config


# ============================================================
#  时域特征
# ============================================================

def extract_time_domain(signal: np.ndarray) -> Dict[str, float]:
    """
    提取时域特征

    Args:
        signal: 1D 信号数组

    Returns:
        特征字典
    """
    if len(signal) == 0:
        return {}

    features = {
        "mean": float(np.mean(signal)),
        "variance": float(np.var(signal)),
        "std": float(np.std(signal)),
        "min": float(np.min(signal)),
        "max": float(np.max(signal)),
        "range": float(np.max(signal) - np.min(signal)),
        "rms": float(np.sqrt(np.mean(np.square(signal)))),
        "sma": float(np.sum(np.abs(signal)) / len(signal)),  # Signal Magnitude Area
        "iqr": float(scipy_iqr(signal) if len(signal) > 3 else 0.0),
    }

    # 零交叉率
    zero_crossings = np.sum(np.abs(np.diff(np.signbit(signal)))) if len(signal) > 1 else 0
    features["zero_crossing_rate"] = float(zero_crossings / len(signal))

    return features


# ============================================================
#  频域特征
# ============================================================

def extract_freq_domain(
    signal: np.ndarray,
    fs: float = 50.0,
    freq_bands: Optional[List[Tuple[float, float]]] = None,
) -> Dict[str, float]:
    """
    提取频域特征

    Args:
        signal: 1D 信号数组
        fs: 采样频率 (Hz)
        freq_bands: 自定义频带列表 [(low, high), ...]

    Returns:
        特征字典
    """
    if len(signal) < 4:
        return {}

    n = len(signal)
    fft_vals = fft(signal)
    fft_magnitude = np.abs(fft_vals[: n // 2])
    freqs = fftfreq(n, 1.0 / fs)[: n // 2]

    if len(fft_magnitude) == 0:
        return {}

    # 总谱能量
    total_energy = float(np.sum(fft_magnitude**2))
    if total_energy < 1e-10:
        total_energy = 1.0

    # 主导频率
    dominant_idx = int(np.argmax(fft_magnitude))
    dominant_freq = float(freqs[dominant_idx]) if dominant_idx < len(freqs) else 0.0

    # 谱熵
    power_spectrum = fft_magnitude**2 / total_energy
    power_spectrum = power_spectrum[power_spectrum > 1e-12]
    spectral_entropy = float(-np.sum(power_spectrum * np.log2(power_spectrum)))

    # 平均频率（加权）
    mean_freq = float(np.sum(freqs * (fft_magnitude**2)) / total_energy)

    features = {
        "dominant_frequency": dominant_freq,
        "spectral_energy": total_energy,
        "spectral_entropy": spectral_entropy,
        "mean_frequency": mean_freq,
    }

    # 频带能量比
    if freq_bands is None:
        freq_bands = [(0.5, 3.0), (3.0, 6.0), (6.0, 15.0)]

    for i, (low, high) in enumerate(freq_bands):
        mask = (freqs >= low) & (freqs <= high)
        band_energy = float(np.sum(fft_magnitude[mask] ** 2))
        features[f"band_{i}_energy_ratio"] = band_energy / total_energy

    return features


# ============================================================
#  组合特征
# ============================================================

def extract_composite_features(acc: np.ndarray, gyro: np.ndarray) -> Dict[str, float]:
    """
    提取跨轴组合特征

    Args:
        acc: 加速度窗口 (N x 3)
        gyro: 角速度窗口 (N x 3)

    Returns:
        组合特征字典
    """
    features = {}

    # 加速度合成量均值
    acc_magnitude = np.sqrt(np.sum(acc**2, axis=1))
    features["acc_magnitude_mean"] = float(np.mean(acc_magnitude))
    features["acc_magnitude_std"] = float(np.std(acc_magnitude))

    # 角速度合成量均值
    gyro_magnitude = np.sqrt(np.sum(gyro**2, axis=1))
    features["gyro_magnitude_mean"] = float(np.mean(gyro_magnitude))
    features["gyro_magnitude_std"] = float(np.std(gyro_magnitude))

    return features


# ============================================================
#  完整特征向量提取
# ============================================================

CHANNEL_NAMES = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]


def extract_feature_vector(
    acc_window: np.ndarray,
    gyro_window: np.ndarray,
    fs: float = 50.0,
) -> Tuple[np.ndarray, List[str]]:
    """
    从加速度和角速度窗口中提取完整特征向量

    Args:
        acc_window: 加速度窗口 (N x 3)
        gyro_window: 角速度窗口 (N x 3)
        fs: 采样频率

    Returns:
        (features_array, feature_names)
    """
    all_features = {}
    feature_names = []

    # 合并6通道数据
    channels = np.column_stack([acc_window, gyro_window])  # (N, 6)

    for i, ch_name in enumerate(CHANNEL_NAMES):
        signal = channels[:, i]

        # 时域特征
        td = extract_time_domain(signal)
        for feat_name, feat_val in td.items():
            key = f"{ch_name}_{feat_name}"
            all_features[key] = feat_val
            feature_names.append(key)

        # 频域特征
        fd = extract_freq_domain(signal, fs=fs)
        for feat_name, feat_val in fd.items():
            key = f"{ch_name}_{feat_name}"
            all_features[key] = feat_val
            feature_names.append(key)

    # 组合特征
    composite = extract_composite_features(acc_window, gyro_window)
    for feat_name, feat_val in composite.items():
        all_features[feat_name] = feat_val
        feature_names.append(feat_name)

    return np.array([all_features[n] for n in feature_names], dtype=np.float64), feature_names


def extract_features_from_windows(
    acc_windows: List[np.ndarray],
    gyro_windows: List[np.ndarray],
    fs: float = 50.0,
) -> np.ndarray:
    """
    批量从窗口列表提取特征矩阵

    Args:
        acc_windows: 加速度窗口列表
        gyro_windows: 角速度窗口列表
        fs: 采样频率

    Returns:
        特征矩阵 (n_windows, n_features)
    """
    feature_matrix = []
    for acc_w, gyr_w in zip(acc_windows, gyro_windows):
        if len(acc_w) < 4 or len(gyr_w) < 4:
            continue
        fv, _ = extract_feature_vector(acc_w, gyr_w, fs)
        feature_matrix.append(fv)

    if not feature_matrix:
        return np.array([]).reshape(0, 0)

    return np.vstack(feature_matrix)


def get_feature_dimension() -> int:
    """返回特征向量的维度"""
    # 每通道: 10 时域 + 8 频域 = 18 × 6 = 108
    # 组合: 4 = 112
    return len(CHANNEL_NAMES) * 18 + 4
