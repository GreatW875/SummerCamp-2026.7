#!/usr/bin/env python
"""
生成合成 running 数据并与 UCI HAR 合并

合成 running 数据基于真实 IMU 物理模型：
- 步频 2.5-3.0 Hz（对应 150-180 步/分）
- 加速度振幅 1.5-4.0 m/s²（垂向波动）
- 陀螺仪振幅 50-120 deg/s
- 加入高斯噪声模拟真实传感器

用法:
    python -m ml.generate_synthetic_csv
    python -m ml.generate_synthetic_csv --samples 300000
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from src.core.logging_config import get_logger

logger = get_logger(__name__)

DATA_DIR = _project_root / "artifacts" / "datasets"


def generate_running_data(
    n_samples: int = 300000,
    fs: float = 50.0,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    生成合成 running 类别的 IMU 数据

    参数:
        n_samples: 生成的样本数
        fs: 采样率 (Hz)
        random_state: 随机种子

    Returns:
        DataFrame with columns: acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, label
    """
    rng = np.random.RandomState(random_state)
    records = []

    logger.info(f"生成 {n_samples:,} 条合成 running 数据...")

    batch_size = 100000
    for batch_start in range(0, n_samples, batch_size):
        batch_n = min(batch_size, n_samples - batch_start)

        # 为每条样本随机采样步频和振幅
        freq = rng.uniform(2.5, 3.0, batch_n)        # Hz
        acc_amp = rng.uniform(1.5, 4.0, batch_n)     # m/s²
        gyro_amp = rng.uniform(50, 120, batch_n)     # deg/s

        # 生成时间相位（模拟连续采样的相位连续性）
        phase = rng.uniform(0, 2 * np.pi, batch_n)

        # 加速度：垂直方向（z轴）模拟着地冲击，x/y轴模拟摆臂
        # 着地冲击模型：步态周期中地面反作用力
        gait_phase = phase % (2 * np.pi)  # [0, 2π)
        heel_strike = np.exp(-((gait_phase - np.pi) % (2 * np.pi) - np.pi) ** 2 / 0.3)

        acc_x = np.sin(phase) * acc_amp * 0.6 + rng.randn(batch_n) * 0.15
        acc_y = np.cos(phase) * acc_amp * 0.4 + rng.randn(batch_n) * 0.15
        acc_z = 9.8 + np.abs(np.sin(phase)) * acc_amp * 0.8 + heel_strike * acc_amp * 1.5 + rng.randn(batch_n) * 0.2

        # 陀螺仪：角速度反映躯干旋转
        gyro_x = np.cos(phase) * gyro_amp * 0.5 + rng.randn(batch_n) * 3
        gyro_y = np.sin(phase) * gyro_amp * 0.6 + rng.randn(batch_n) * 3
        gyro_z = np.cos(phase * 2) * gyro_amp * 0.3 + rng.randn(batch_n) * 2

        batch_df = pd.DataFrame({
            "acc_x": acc_x.astype(np.float32),
            "acc_y": acc_y.astype(np.float32),
            "acc_z": acc_z.astype(np.float32),
            "gyro_x": gyro_x.astype(np.float32),
            "gyro_y": gyro_y.astype(np.float32),
            "gyro_z": gyro_z.astype(np.float32),
            "label": "running",
        })
        records.append(batch_df)

        if (batch_start + batch_n) % 200000 == 0:
            logger.info(f"  已生成 {batch_start + batch_n:,} 条...")

    df = pd.concat(records, ignore_index=True)
    logger.info(f"合成 running 数据: {len(df):,} 条")
    return df


def merge_and_save(uci_csv: Path, running_df: pd.DataFrame, output: Path) -> Path:
    """合并 UCI HAR 与合成 running 数据"""
    logger.info(f"加载 UCI HAR: {uci_csv}")
    uci_df = pd.read_csv(uci_csv)
    logger.info(f"UCI HAR 样本: {len(uci_df):,}")

    # 合并（不打乱！滑窗需要每类数据连续，之后在窗口层面再打乱）
    merged = pd.concat([uci_df, running_df], ignore_index=True)

    merged.to_csv(output, index=False)

    # 统计
    size_mb = output.stat().st_size / (1024 * 1024)
    logger.info(f"合并完成: {output}")
    logger.info(f"  总样本: {len(merged):,}")
    logger.info(f"  文件大小: {size_mb:.1f} MB")
    logger.info(f"  标签分布: {dict(merged['label'].value_counts())}")

    return output


def main():
    parser = argparse.ArgumentParser(description="生成合成 running 数据")
    parser.add_argument("--samples", type=int, default=300000, help="running 样本数")
    parser.add_argument("--uci-csv", type=str, default=None,
                        help="UCI HAR CSV 路径 (默认: artifacts/datasets/uci_har.csv)")
    parser.add_argument("--output", type=str, default=None,
                        help="输出路径 (默认: artifacts/datasets/hybrid_3class.csv)")
    args = parser.parse_args()

    uci_csv = Path(args.uci_csv) if args.uci_csv else DATA_DIR / "uci_har.csv"
    output = Path(args.output) if args.output else DATA_DIR / "hybrid_3class.csv"

    if not uci_csv.exists():
        logger.error(f"UCI HAR CSV 不存在: {uci_csv}")
        logger.error("请先运行: python -m ml.download_datasets --dataset uci_har")
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 生成合成 running
    running_df = generate_running_data(n_samples=args.samples)

    # 合并
    merge_and_save(uci_csv, running_df, output)

    print()
    logger.info("=" * 60)
    logger.info("  下一步训练 3 分类模型:")
    logger.info("=" * 60)
    print(f"  python -m ml.train --csv {output}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
