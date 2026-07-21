#!/usr/bin/env python
"""
开源数据集下载与转换脚本

从公开 HAR 数据集下载原始 IMU 数据，转换为项目 CSV 格式供训练使用。

支持的数据集:
  - UCI HAR Dataset (50Hz, acc+gyro, 30 subjects, 6 activities)
    https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones

用法:
    python -m ml.download_datasets                    # 下载并转换所有数据集
    python -m ml.download_datasets --dataset uci_har  # 仅下载 UCI HAR
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from src.core.logging_config import get_logger

logger = get_logger(__name__)

# 数据集输出目录
DATA_DIR = _project_root / "artifacts" / "datasets"

# ============================================================
#  UCI HAR Dataset
# ============================================================

UCI_HAR_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/"
    "00240/UCI%20HAR%20Dataset.zip"
)

# UCI → 项目标签映射
UCI_LABEL_MAP = {
    1: "walking",             # WALKING
    2: "walking",             # WALKING_UPSTAIRS → 合并为 walking
    3: "walking",             # WALKING_DOWNSTAIRS → 合并为 walking
    4: "static",              # SITTING
    5: "static",              # STANDING
    6: "static",              # LAYING
}


def download_file(url: str, dest: Path) -> None:
    """下载文件并显示进度（优先使用 requests，降级 wget）"""
    dest.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"下载: {url}")
    logger.info(f"目标: {dest}")

    # 方案 A: requests (流式下载，支持进度)
    try:
        import requests
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; sport_reco/1.0)"},
            stream=True,
            timeout=(30, 600),  # (connect, read)
        )
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))

        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = min(100, downloaded * 100 / total)
                        print(f"\r  下载中... {pct:.0f}% ({downloaded/1024/1024:.1f}MB)", end="", flush=True)
        print()
        logger.info(f"已保存: {dest} ({downloaded/1024/1024:.1f} MB)")
        return
    except Exception as e:
        logger.warning(f"requests 下载失败: {e}")

    # 方案 B: wget 降级
    import subprocess
    logger.info("降级使用 wget...")
    result = subprocess.run(
        ["wget", "-q", "--show-progress", "-O", str(dest), url],
        timeout=900,  # 15分钟
    )
    if result.returncode != 0:
        raise RuntimeError(f"wget 下载失败，返回码: {result.returncode}")
    logger.info(f"已保存: {dest}")


def load_uci_inertial_signals(folder: Path, prefix: str) -> np.ndarray:
    """
    加载 UCI HAR 惯性信号文件并展平为时序数据

    UCI HAR 文件格式: 每行 = 一个 128-sample 窗口的样本值（空格分隔）

    Returns:
        (N, 6) 形状的数组，列: acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z
    """
    # 使用 total_acc（含重力）而非 body_acc
    acc_x = np.loadtxt(folder / f"total_acc_x_{prefix}.txt")
    acc_y = np.loadtxt(folder / f"total_acc_y_{prefix}.txt")
    acc_z = np.loadtxt(folder / f"total_acc_z_{prefix}.txt")

    gyro_x = np.loadtxt(folder / f"body_gyro_x_{prefix}.txt")
    gyro_y = np.loadtxt(folder / f"body_gyro_y_{prefix}.txt")
    gyro_z = np.loadtxt(folder / f"body_gyro_z_{prefix}.txt")

    # UCI HAR 数据已归一化到 [-1, 1]，恢复为物理单位
    # 加速度 × 9.8 → m/s²；角速度 × 2000 → deg/s（UCI 文档值）
    acc_x *= 9.8
    acc_y *= 9.8
    acc_z *= 9.8
    gyro_x *= 2000
    gyro_y *= 2000
    gyro_z *= 2000

    n_windows, n_steps = acc_x.shape

    records = []
    for w in range(n_windows):
        for t in range(n_steps):
            records.append([
                acc_x[w, t], acc_y[w, t], acc_z[w, t],
                gyro_x[w, t], gyro_y[w, t], gyro_z[w, t],
            ])
    return np.array(records, dtype=np.float32)


def load_uci_labels(folder: Path, prefix: str) -> np.ndarray:
    """加载 UCI HAR 标签并重复到每样本"""
    raw = np.loadtxt(folder / f"y_{prefix}.txt").astype(int)
    n_steps = 128  # UCI HAR 固定窗口 128 样本
    return np.repeat(raw, n_steps)


def download_uci_har() -> Path:
    """下载并转换 UCI HAR Dataset → CSV"""
    logger.info("=" * 50)
    logger.info("  UCI HAR Dataset")
    logger.info("=" * 50)

    zip_path = DATA_DIR / "UCI_HAR_Dataset.zip"
    extract_dir = DATA_DIR / "raw" / "UCI HAR Dataset"

    # 下载
    if not zip_path.exists():
        download_file(UCI_HAR_URL, zip_path)

    # 解压
    if not extract_dir.exists():
        logger.info(f"解压: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(DATA_DIR / "raw")
        logger.info("解压完成")

    # 查找惯性信号目录
    uci_root = extract_dir
    if not uci_root.exists():
        # 某些解压后路径不同
        candidates = list((DATA_DIR / "raw").glob("**/train/Inertial Signals"))
        if candidates:
            uci_root = candidates[0].parent.parent
        else:
            raise FileNotFoundError("找不到 UCI HAR 数据目录")

    # 加载训练集和测试集
    parts = []
    for subset in ["train", "test"]:
        signals_dir = uci_root / subset / "Inertial Signals"
        if not signals_dir.exists():
            logger.warning(f"跳过 {subset}: 目录不存在 {signals_dir}")
            continue
        logger.info(f"加载 {subset} 数据...")

        X = load_uci_inertial_signals(signals_dir, subset)
        y_raw = load_uci_labels(uci_root / subset, subset)
        y = np.array([UCI_LABEL_MAP.get(l, "unknown") for l in y_raw])

        df = pd.DataFrame(X, columns=["acc_x", "acc_y", "acc_z",
                                       "gyro_x", "gyro_y", "gyro_z"])
        df["label"] = y
        parts.append(df)

    full = pd.concat(parts, ignore_index=True)
    csv_path = DATA_DIR / "uci_har.csv"
    full.to_csv(csv_path, index=False)

    logger.info(f"UCI HAR 转换完成:")
    logger.info(f"  总样本: {len(full):,}")
    logger.info(f"  特征: acc_x/y/z, gyro_x/y/z, label")
    logger.info(f"  标签分布: {dict(full['label'].value_counts())}")
    logger.info(f"  输出: {csv_path}")
    return csv_path


# ============================================================
#  MotionSense Dataset
# ============================================================

# MotionSense 活动 → 项目标签映射
MOTIONSENSE_LABEL_MAP = {
    "dws": "walking",       # downstairs → walking
    "ups": "walking",       # upstairs → walking
    "wlk": "walking",       # walking
    "jog": "running",       # jogging → running  ← 补充 running 类别！
    "sit": "static",        # sitting
    "std": "static",        # standing
}


def download_motionsense() -> Path:
    """
    下载 MotionSense 数据集
    https://github.com/mmalekzadeh/motion-sense

    该数据集补充了 UCI HAR 缺少的 jogging(→running) 类别。
    数据格式: 每个 subject 一个 CSV 文件夹，包含 attitude/gravity/userAcc/rotationRate
    """
    import json

    logger.info("=" * 50)
    logger.info("  MotionSense Dataset")
    logger.info("=" * 50)

    # MotionSense 数据文件在 GitHub Release 中
    ms_url = (
        "https://github.com/mmalekzadeh/motion-sense/raw/master/data/"
        "A_DeviceMotion_data.zip"
    )
    ms_label_url = (
        "https://raw.githubusercontent.com/mmalekzadeh/motion-sense/"
        "master/data/A_DeviceMotion_data/annotations.json"
    )

    zip_path = DATA_DIR / "motionsense.zip"
    extract_dir = DATA_DIR / "raw" / "motionsense"

    # 下载
    if not zip_path.exists():
        try:
            download_file(ms_url, zip_path)
        except Exception as e:
            logger.warning(f"MotionSense 下载失败: {e}")
            logger.warning("跳过 MotionSense，仅使用 UCI HAR")
            return None

    # 下载标注
    label_path = DATA_DIR / "raw" / "motionsense_labels.json"
    if not label_path.exists():
        try:
            download_file(ms_label_url, label_path)
        except Exception as e:
            logger.warning(f"MotionSense 标注下载失败: {e}")
            return None

    # 解压
    if not extract_dir.exists():
        logger.info(f"解压: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

    # 加载标注
    with open(label_path, "r") as f:
        annotations = json.load(f)

    # 遍历 subjects
    all_records = []
    subjects_dir = extract_dir / "A_DeviceMotion_data"
    if not subjects_dir.exists():
        subjects_dir = extract_dir

    for subj_dir in sorted(subjects_dir.iterdir()):
        if not subj_dir.is_dir():
            continue

        # 查找该 subject 的标注
        subj_annotation = annotations.get(subj_dir.name, {})
        label_intervals = subj_annotation.get("annotations", [])

        # 读取 userAcceleration 和 rotationRate 文件
        ua_file = subj_dir / "userAcceleration.csv"
        rr_file = subj_dir / "rotationRate.csv"

        if not (ua_file.exists() and rr_file.exists()):
            continue

        try:
            ua = pd.read_csv(ua_file)
            rr = pd.read_csv(rr_file)
        except Exception:
            continue

        min_len = min(len(ua), len(rr))
        ua = ua.iloc[:min_len]
        rr = rr.iloc[:min_len]

        # 根据标注区间赋标签
        labels = np.array(["static"] * min_len, dtype=object)
        for interval in label_intervals:
            start = interval.get("start", 0)
            end = interval.get("end", min_len)
            act = interval.get("label", "unknown")
            mapped = MOTIONSENSE_LABEL_MAP.get(act, "unknown")
            labels[start:end] = mapped

        for i in range(min_len):
            all_records.append({
                "acc_x": ua.iloc[i, 0] if ua.shape[1] > 0 else 0,
                "acc_y": ua.iloc[i, 1] if ua.shape[1] > 1 else 0,
                "acc_z": ua.iloc[i, 2] if ua.shape[1] > 2 else 0,
                "gyro_x": rr.iloc[i, 0] if rr.shape[1] > 0 else 0,
                "gyro_y": rr.iloc[i, 1] if rr.shape[1] > 1 else 0,
                "gyro_z": rr.iloc[i, 2] if rr.shape[1] > 2 else 0,
                "label": labels[i],
            })

    if not all_records:
        logger.warning("MotionSense: 未找到有效数据")
        return None

    df = pd.DataFrame(all_records)
    csv_path = DATA_DIR / "motionsense.csv"
    df.to_csv(csv_path, index=False)

    logger.info(f"MotionSense 转换完成:")
    logger.info(f"  总样本: {len(df):,}")
    logger.info(f"  标签分布: {dict(df['label'].value_counts())}")
    logger.info(f"  输出: {csv_path}")
    return csv_path


# ============================================================
#  合并数据集
# ============================================================

def merge_datasets(csv_paths: List[Path]) -> Path:
    """合并多个 CSV 为一个"""
    parts = []
    for p in csv_paths:
        if p and p.exists():
            parts.append(pd.read_csv(p))
    if not parts:
        return None

    merged = pd.concat(parts, ignore_index=True)
    # 打乱顺序
    merged = merged.sample(frac=1, random_state=42).reset_index(drop=True)

    out = DATA_DIR / "merged_har.csv"
    merged.to_csv(out, index=False)

    logger.info(f"合并数据集:")
    logger.info(f"  总样本: {len(merged):,}")
    logger.info(f"  标签分布: {dict(merged['label'].value_counts())}")
    logger.info(f"  输出: {out}")
    return out


# ============================================================
#  主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="下载开源 HAR 数据集")
    parser.add_argument(
        "--dataset", type=str, default="all",
        choices=["all", "uci_har", "motionsense", "merge"],
        help="指定数据集"
    )
    parser.add_argument(
        "--merge", action="store_true", default=True,
        help="合并所有数据集 (默认: True)"
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    csv_paths = []

    if args.dataset in ("all", "uci_har"):
        p = download_uci_har()
        csv_paths.append(p)

    if args.dataset in ("all", "motionsense"):
        p = download_motionsense()
        if p:
            csv_paths.append(p)

    if args.merge and len(csv_paths) > 1:
        merge_datasets(csv_paths)

    # 提示下一步
    print()
    logger.info("=" * 50)
    logger.info("  下载完成！下一步训练:")
    logger.info("=" * 50)
    print(f"  # 使用 UCI HAR 训练")
    print(f"  python -m ml.train --csv {DATA_DIR / 'uci_har.csv'}")
    if len(csv_paths) > 1:
        print(f"  # 使用合并数据集训练")
        print(f"  python -m ml.train --csv {DATA_DIR / 'merged_har.csv'}")
    print(f"  # 使用合成数据 + CSV 混合训练（需自行合并 CSV）")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
