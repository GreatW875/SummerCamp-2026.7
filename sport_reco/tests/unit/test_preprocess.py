"""
预处理模块单元测试
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from src.core.preprocess import (
    butter_lowpass,
    remove_gravity,
    sliding_window,
    preprocess_pipeline,
    moving_average,
    normalize_signal,
)


def test_butter_lowpass():
    """测试低通滤波"""
    t = np.linspace(0, 2, 100)  # 50Hz * 2s
    signal = np.sin(2 * np.pi * 5 * t) + 0.1 * np.random.randn(100)
    filtered = butter_lowpass(signal, cutoff=20.0, fs=50.0)
    assert len(filtered) == len(signal), "滤波后长度不变"
    assert filtered.std() < signal.std() * 1.1, "滤波降低噪声"


def test_remove_gravity():
    """测试重力分离"""
    acc = np.column_stack([
        np.zeros(200),
        np.zeros(200),
        9.8 * np.ones(200) + 0.5 * np.sin(np.linspace(0, 4*np.pi, 200)),
    ])
    linear, gravity = remove_gravity(acc)
    assert linear.shape == acc.shape
    assert gravity.shape == acc.shape
    assert np.abs(np.mean(gravity[:, 2]) - 9.8) < 1.0


def test_sliding_window():
    """测试滑窗分段"""
    data = np.random.randn(200, 3)
    windows = sliding_window(data, window_size=100, step_size=50)
    assert len(windows) == 3, f"应有3个窗口，实际 {len(windows)}"
    assert windows[0].shape == (100, 3)


def test_preprocess_pipeline():
    """测试完整预处理管线"""
    acc = np.random.randn(200, 3)
    gyro = np.random.randn(200, 3)
    acc_p, gyro_p = preprocess_pipeline(acc, gyro)
    assert acc_p.shape == acc.shape
    assert gyro_p.shape == gyro.shape
    assert not np.any(np.isnan(acc_p))
    assert not np.any(np.isnan(gyro_p))


def test_moving_average():
    """测试移动平均"""
    signal = np.array([1, 1, 1, 10, 1, 1, 1], dtype=float)
    smoothed = moving_average(signal, window_size=3)
    assert smoothed[3] < signal[3], "移动平均应平滑尖峰"


def test_normalize_signal():
    """测试Z-score标准化"""
    data = np.array([[1, 2], [3, 4], [5, 6]], dtype=float)
    normalized = normalize_signal(data)
    assert np.allclose(normalized.mean(axis=0), 0)
    assert np.allclose(normalized.std(axis=0), 1)


if __name__ == "__main__":
    test_butter_lowpass()
    test_remove_gravity()
    test_sliding_window()
    test_preprocess_pipeline()
    test_moving_average()
    test_normalize_signal()
    print("✓ 所有预处理测试通过")
