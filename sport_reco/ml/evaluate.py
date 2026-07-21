#!/usr/bin/env python
"""
模型评估模块

评估指标: 准确率、精确率、召回率、F1、混淆矩阵
支持交叉验证和混淆矩阵可视化。
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from src.core.logging_config import get_logger

logger = get_logger(__name__)


def evaluate_model(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    label_names: List[str],
) -> Dict:
    """
    全面评估模型性能

    Args:
        model: 训练好的分类器
        X_test: 测试特征矩阵
        y_test: 测试标签
        label_names: 标签名称列表

    Returns:
        评估指标字典
    """
    y_pred = model.predict(X_test)

    # 基础指标
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred)

    # 逐类指标
    per_class = {}
    for i, name in enumerate(label_names):
        tp = cm[i, i] if i < cm.shape[0] else 0
        fp = cm[:, i].sum() - tp if i < cm.shape[0] else 0
        fn = cm[i, :].sum() - tp if i < cm.shape[0] else 0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_cls = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        per_class[name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1_cls, 4),
            "support": int(cm[i, :].sum()) if i < cm.shape[0] else 0,
        }

    metrics = {
        "accuracy": round(float(accuracy), 4),
        "precision_weighted": round(float(precision), 4),
        "recall_weighted": round(float(recall), 4),
        "f1_weighted": round(float(f1), 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "test_size": len(y_test),
    }

    # 打印报告
    print("\n" + "=" * 60)
    print("  模型评估报告")
    print("=" * 60)
    print(f"  准确率 (Accuracy):  {accuracy:.2%}")
    print(f"  精确率 (Precision): {precision:.2%}")
    print(f"  召回率 (Recall):    {recall:.2%}")
    print(f"  F1 分数:            {f1:.2%}")
    print(f"  测试样本数:         {len(y_test)}")
    print()
    print("  逐类指标:")
    print(f"  {'类别':<12} {'精确率':>8} {'召回率':>8} {'F1':>8} {'样本':>6}")
    print("  " + "-" * 48)
    for name, metrics_cls in per_class.items():
        print(
            f"  {name:<12} {metrics_cls['precision']:>8.4f} "
            f"{metrics_cls['recall']:>8.4f} {metrics_cls['f1']:>8.4f} "
            f"{metrics_cls['support']:>6}"
        )

    print("\n  混淆矩阵:")
    print("  " + " " * 12 + "".join(f"{n:>8}" for n in label_names))
    for i, row in enumerate(cm):
        name = label_names[i] if i < len(label_names) else f"C{i}"
        print(f"  {name:<12}" + "".join(f"{v:>8}" for v in row))
    print("=" * 60 + "\n")

    # 生成分类报告字符串（使用 labels 参数覆盖实际出现的类别）
    report = classification_report(
        y_test, y_pred, target_names=label_names, zero_division=0,
        labels=list(range(len(label_names))),
    )
    logger.info(f"分类报告:\n{report}")

    return metrics


def plot_confusion_matrix(
    cm: np.ndarray,
    label_names: List[str],
    save_path: Optional[str] = None,
) -> None:
    """绘制混淆矩阵（使用 matplotlib）"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)

    ax.set(
        xticks=np.arange(len(label_names)),
        yticks=np.arange(len(label_names)),
        xticklabels=label_names,
        yticklabels=label_names,
        ylabel="真实标签",
        xlabel="预测标签",
        title="混淆矩阵",
    )

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # 标注数值
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j, i, format(cm[i, j], "d"),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
            )

    fig.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"混淆矩阵图已保存: {save_path}")
    else:
        plt.show()

    plt.close()


def cross_validate(
    model_class,
    X: np.ndarray,
    y: np.ndarray,
    cv: int = 5,
    **model_kwargs,
) -> Dict:
    """K 折交叉验证"""
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    model = model_class(**model_kwargs)

    scores = cross_val_score(model, X, y, cv=skf, scoring="accuracy")

    result = {
        "cv_folds": cv,
        "accuracy_mean": round(float(scores.mean()), 4),
        "accuracy_std": round(float(scores.std()), 4),
        "accuracy_per_fold": scores.tolist(),
    }

    logger.info(
        f"交叉验证 (cv={cv}): accuracy={scores.mean():.2%} ± {scores.std():.2%}"
    )
    return result
