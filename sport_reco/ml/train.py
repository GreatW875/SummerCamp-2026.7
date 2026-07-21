#!/usr/bin/env python
"""
模型训练脚本

训练 SVM 和 RandomForest 分类器，保存最佳模型到 artifacts/models/。

用法:
    python -m ml.train                    # 使用合成数据训练
    python -m ml.train --csv data.csv     # 从 CSV 训练
    python -m ml.train --model svm        # 指定模型类型
"""

import argparse
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from src.core.config import config
from src.core.logging_config import get_logger

from .dataset import build_dataset, extract_features

logger = get_logger(__name__)


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_type: str = "random_forest",
) -> Any:
    """
    训练分类模型

    Args:
        X_train: 训练特征矩阵
        y_train: 训练标签
        model_type: "random_forest" 或 "svm"

    Returns:
        训练好的模型
    """
    logger.info(f"训练 {model_type} 模型, 数据: {X_train.shape}")

    if model_type == "random_forest":
        params = config.get("training.random_forest", {})
        model = RandomForestClassifier(
            n_estimators=params.get("n_estimators", 100),
            max_depth=params.get("max_depth", 15),
            min_samples_split=params.get("min_samples_split", 5),
            min_samples_leaf=params.get("min_samples_leaf", 2),
            class_weight=params.get("class_weight", "balanced"),
            random_state=params.get("random_state", 42),
            n_jobs=params.get("n_jobs", -1),
        )
    elif model_type == "svm":
        params = config.get("training.svm", {})
        model = SVC(
            kernel=params.get("kernel", "rbf"),
            C=params.get("C", 1.0),
            gamma=params.get("gamma", "scale"),
            class_weight=params.get("class_weight", "balanced"),
            probability=params.get("probability", True),
            random_state=params.get("random_state", 42),
        )
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

    model.fit(X_train, y_train)
    logger.info(f"模型训练完成: {type(model).__name__}")
    return model


def save_model(
    model: Any,
    label_names: list,
    feature_names: Optional[list] = None,
    output_path: Optional[str] = None,
    metrics: Optional[Dict] = None,
    n_features: int = 0,
) -> str:
    """
    保存模型及元数据到 artifacts/models/

    保存格式:
    {
        "model": trained_model,
        "labels": label_names,
        "feature_dim": n_features,
        "feature_names": [...],
        "trained_at": "iso_datetime",
        "metrics": {...}
    }
    """
    project_root = config.project_root
    artifacts_dir = Path(project_root) / "artifacts" / "models"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_type = type(model).__name__.lower().replace("classifier", "")
        output_path = str(artifacts_dir / f"gait_{model_type}_{timestamp}.pkl")

    # 同时保存一个 "latest" 副本
    latest_path = artifacts_dir / "gait_classifier.pkl"

    model_data = {
        "model": model,
        "labels": label_names,
        "feature_dim": n_features,
        "feature_names": feature_names or [],
        "trained_at": datetime.now().isoformat(),
        "model_type": type(model).__name__,
        "metrics": metrics or {},
    }

    for path in [output_path, str(latest_path)]:
        with open(path, "wb") as f:
            pickle.dump(model_data, f)
        logger.info(f"模型已保存: {path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="运动类型分类模型训练")
    parser.add_argument("--csv", type=str, default=None, help="CSV 数据文件路径")
    parser.add_argument("--model", type=str, default="random_forest",
                        choices=["random_forest", "svm"], help="模型类型")
    parser.add_argument("--samples", type=int, default=4000, help="合成数据样本数")
    parser.add_argument("--output", type=str, default=None, help="模型输出路径")
    parser.add_argument("--eval", action="store_true", default=True, help="训练后评估")

    args = parser.parse_args()

    # 1. 构建数据集
    logger.info("=" * 50)
    logger.info("  运动分类模型训练")
    logger.info("=" * 50)

    if args.csv:
        data_source = "csv"
        logger.info(f"数据源: CSV ({args.csv})")
    else:
        data_source = "synthetic"
        logger.info(f"数据源: 合成数据 ({args.samples} 样本)")

    data, label_names, n_features = build_dataset(
        data_source=data_source,
        csv_path=args.csv,
        n_samples=args.samples,
    )

    logger.info(f"特征维度: {n_features}")
    logger.info(f"类别: {label_names}")
    logger.info(f"训练集: {data['X_train'].shape[0]}, 测试集: {data['X_test'].shape[0]}")

    # 2. 训练模型
    model = train_model(data["X_train"], data["y_train"], args.model)

    # 3. 评估
    metrics = {}
    if args.eval:
        from .evaluate import evaluate_model
        metrics = evaluate_model(model, data["X_test"], data["y_test"], label_names)

    # 4. 保存
    saved_path = save_model(
        model=model,
        label_names=label_names,
        output_path=args.output,
        metrics=metrics,
        n_features=n_features,
    )

    logger.info(f"训练完成! 模型: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
