"""
传感器数据预处理模块

功能：
- 巴特沃斯低通滤波
- 滑动窗口分段
- 信号去噪与平滑
- 重力分离（加速度）
"""

from typing import List, Optional, Tuple

import numpy as np
from scipy.signal import butter, filtfilt

from .config import config


# ============================================================
#  滤波器
# ============================================================

def butter_lowpass(
    data: np.ndarray,
    cutoff: Optional[float] = None,
    fs: Optional[float] = None,
    order: Optional[int] = None,
) -> np.ndarray:
    """
    巴特沃斯低通滤波器

    Args:
        data: 输入信号 (1D 数组)
        cutoff: 截止频率 (Hz)，默认从配置读取
        fs: 采样频率 (Hz)，默认从配置读取
        order: 滤波器阶数，默认从配置读取

    Returns:
        滤波后的信号
    """
    if cutoff is None:
        cutoff = config.get("preprocess.filter.cutoff_freq", 20.0)
    if fs is None:
        fs = config.get("preprocess.filter.sample_rate", 50.0)
    if order is None:
        order = config.get("preprocess.filter.order", 4)

    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    if normal_cutoff >= 1.0:
        return data  # 截止频率超过奈奎斯特频率，无需滤波

    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    if len(data) < 3 * order:
        return data  # 数据太短无法滤波

    try:
        return filtfilt(b, a, data)
    except ValueError:
        return data


def remove_gravity(acc_data: np.ndarray, alpha: float = 0.8) -> Tuple[np.ndarray, np.ndarray]:
    """
    使用高通滤波器（一阶 IIR）分离重力分量和线性加速度

    Args:
        acc_data: 加速度信号 (N x 3)，三轴 [x, y, z]
        alpha: 平滑系数 (0~1)，越接近1滤波越弱

    Returns:
        (linear_acceleration, gravity) 元组
    """
    if acc_data.ndim == 1:
        acc_data = acc_data.reshape(-1, 1)

    gravity = np.zeros_like(acc_data, dtype=np.float64)
    linear = np.zeros_like(acc_data, dtype=np.float64)

    # 第一帧初始化重力为初始值
    gravity[0] = acc_data[0]

    for i in range(1, len(acc_data)):
        gravity[i] = alpha * gravity[i - 1] + (1 - alpha) * acc_data[i]
        linear[i] = acc_data[i] - gravity[i]

    return linear, gravity


# ============================================================
#  滑动窗口
# ============================================================

def sliding_window(
    data: np.ndarray,
    window_size: Optional[int] = None,
    step_size: Optional[int] = None,
) -> List[np.ndarray]:
    """
    滑动窗口分段

    Args:
        data: 输入数据 (N x M)，N 为时间步，M 为通道数
        window_size: 窗口大小（样本数），默认从配置读取
        step_size: 步长（样本数），默认 window_size/2

    Returns:
        窗口片段列表，每个片段 shape=(window_size, M)
    """
    if window_size is None:
        sample_rate = config.get("preprocess.filter.sample_rate", 50.0)
        win_sec = config.get("preprocess.window.size_seconds", 2.0)
        window_size = int(win_sec * sample_rate)

    if step_size is None:
        step_size = window_size // 2

    if data.ndim == 1:
        data = data.reshape(-1, 1)

    n_samples = data.shape[0]
    if n_samples < window_size:
        # 数据不足一个窗口时，零填充
        padded = np.zeros((window_size, data.shape[1]), dtype=data.dtype)
        padded[:n_samples] = data
        return [padded]

    windows = []
    for start in range(0, n_samples - window_size + 1, step_size):
        windows.append(data[start : start + window_size].copy())

    # 确保最后一段不被遗漏
    if n_samples > window_size and (n_samples - window_size) % step_size != 0:
        windows.append(data[-window_size:].copy())

    return windows if windows else [data.copy()]


# ============================================================
#  信号去噪
# ============================================================

def moving_average(data: np.ndarray, window_size: int = 5) -> np.ndarray:
    """
    移动平均平滑

    Args:
        data: 输入信号 (1D)
        window_size: 平滑窗口大小

    Returns:
        平滑后的信号
    """
    if len(data) < window_size:
        return data
    kernel = np.ones(window_size) / window_size
    return np.convolve(data, kernel, mode="same")


def normalize_signal(data: np.ndarray) -> np.ndarray:
    """
    Z-score 标准化（对每个通道独立处理）

    Args:
        data: 输入数据 (N x M)

    Returns:
        标准化后的数据
    """
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0)
    std[std < 1e-10] = 1.0

    return (data - mean) / std


# ============================================================
#  批量预处理管线
# ============================================================

def preprocess_pipeline(
    acc: np.ndarray,
    gyro: np.ndarray,
    apply_filter: bool = True,
    remove_g: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    完整的预处理管线

    Args:
        acc: 加速度数据 (N x 3)
        gyro: 角速度数据 (N x 3)
        apply_filter: 是否应用巴特沃斯滤波
        remove_g: 是否移除重力分量

    Returns:
        (processed_acc, processed_gyro)
    """
    # 1. 低通滤波
    if apply_filter:
        acc_filtered = np.column_stack(
            [butter_lowpass(acc[:, i]) for i in range(acc.shape[1])]
        )
        gyro_filtered = np.column_stack(
            [butter_lowpass(gyro[:, i]) for i in range(gyro.shape[1])]
        )
    else:
        acc_filtered = acc.copy()
        gyro_filtered = gyro.copy()

    # 2. 重力分离（仅加速度）
    if remove_g:
        acc_filtered, _ = remove_gravity(acc_filtered)

    return acc_filtered, gyro_filtered
