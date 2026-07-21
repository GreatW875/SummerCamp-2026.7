"""
特征提取模块单元测试
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from src.core.features import (
    extract_time_domain,
    extract_freq_domain,
    extract_composite_features,
    extract_feature_vector,
    get_feature_dimension,
    CHANNEL_NAMES,
)


def test_time_domain():
    """测试时域特征提取"""
    signal = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    feats = extract_time_domain(signal)
    assert feats["mean"] == 5.5
    assert feats["min"] == 1.0
    assert feats["max"] == 10.0
    assert feats["range"] == 9.0
    assert "rms" in feats
    assert "zero_crossing_rate" in feats
    assert feats["zero_crossing_rate"] == 0.0  # 无过零


def test_freq_domain():
    """测试频域特征提取"""
    t = np.linspace(0, 2, 100)
    signal = np.sin(2 * np.pi * 3 * t)
    feats = extract_freq_domain(signal, fs=50.0)
    assert "dominant_frequency" in feats
    assert "spectral_energy" in feats
    assert "spectral_entropy" in feats
    assert "band_0_energy_ratio" in feats
    assert 2.5 < feats["dominant_frequency"] < 3.5, \
        f"主导频率应为~3Hz，实际{feats['dominant_frequency']}"


def test_composite_features():
    """测试组合特征"""
    acc = np.random.randn(100, 3)
    gyro = np.random.randn(100, 3)
    feats = extract_composite_features(acc, gyro)
    assert "acc_magnitude_mean" in feats
    assert "gyro_magnitude_mean" in feats
    assert len(feats) == 4


def test_feature_vector():
    """测试完整特征向量提取"""
    acc = np.random.randn(100, 3)
    gyro = np.random.randn(100, 3)
    fv, names = extract_feature_vector(acc, gyro)
    assert len(fv) > 0, "特征向量非空"
    assert len(names) == len(fv)
    assert not np.any(np.isnan(fv)), "无NaN"
    assert not np.any(np.isinf(fv)), "无Inf"

    dim = get_feature_dimension()
    assert dim > 0


def test_channel_count():
    """测试通道数"""
    assert len(CHANNEL_NAMES) == 6


if __name__ == "__main__":
    test_time_domain()
    test_freq_domain()
    test_composite_features()
    test_feature_vector()
    test_channel_count()
    print("✓ 所有特征提取测试通过")
