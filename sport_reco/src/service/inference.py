"""
模型推理服务

负责 ML 模型加载、实时分类预测和结果管理。
支持 SVM 和 RandomForest 两种模型，提供置信度评估。
"""

import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.config import config
from src.core.features import extract_feature_vector, get_feature_dimension
from src.core.logging_config import get_logger
from src.data.repository import InferenceRepository

logger = get_logger(__name__)


class InferenceEngine:
    """
    运动类型推理引擎

    加载训练好的分类模型并提供实时推理接口。
    包含：
    - 特征向量一致性检查
    - 置信度评估
    - 连续结果投票去抖动
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._feature_names: List[str] = []
        self._expected_dim: int = 0

        # 去抖动：连续 N 次相同结果才输出
        self._vote_buffer: List[str] = []
        self._vote_size: int = 3

        # 标签映射
        self._labels: List[str] = config.get("model.labels", [
            "walking", "running"
        ])

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> None:
        """
        加载训练好的模型

        Args:
            model_path: 模型文件路径（.pkl）
        """
        path = Path(model_path)
        if not path.exists():
            # 尝试从 artifacts/models/ 查找
            project_root = config.project_root
            alt_path = Path(project_root) / "artifacts" / "models" / path.name
            if alt_path.exists():
                path = alt_path
            else:
                logger.warning(f"模型文件不存在: {model_path}, {alt_path}")
                return

        with open(path, "rb") as f:
            model_data = pickle.load(f)

        if isinstance(model_data, dict):
            self._model = model_data.get("model")
            self._feature_names = model_data.get("feature_names", [])
            saved_labels = model_data.get("labels")
            if saved_labels:
                self._labels = saved_labels
            # 优先使用模型自身的 n_features_in_ 属性（最准确）
            if hasattr(self._model, "n_features_in_"):
                self._expected_dim = self._model.n_features_in_
            else:
                self._expected_dim = model_data.get("feature_dim", 0)
        else:
            self._model = model_data
            # 从模型推断特征维度
            if hasattr(self._model, "n_features_in_"):
                self._expected_dim = self._model.n_features_in_
            else:
                self._expected_dim = get_feature_dimension()

        logger.info(
            f"模型加载成功: {path.name}, "
            f"类型={type(self._model).__name__}, "
            f"特征维度={self._expected_dim}"
        )

    def predict(
        self, acc_window: np.ndarray, gyro_window: np.ndarray
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        对单窗口数据进行运动类型预测

        Args:
            acc_window: 加速度窗口 (N x 3)
            gyro_window: 角速度窗口 (N x 3)

        Returns:
            (predicted_label, confidence, all_probas)
            all_probas: {label: probability} 所有类别的概率分布
        """
        probas: Dict[str, float] = {}

        if self._model is None:
            return ("unknown", 0.0, probas)

        # 提取特征
        features, _ = extract_feature_vector(acc_window, gyro_window)
        features = features.reshape(1, -1)

        # 维度匹配
        if self._expected_dim > 0 and features.shape[1] != self._expected_dim:
            logger.warning(
                f"特征维度不匹配: 期望={self._expected_dim}, 实际={features.shape[1]}"
            )
            # 截断或填充
            if features.shape[1] > self._expected_dim:
                features = features[:, :self._expected_dim]
            else:
                padding = np.zeros((1, self._expected_dim - features.shape[1]))
                features = np.hstack([features, padding])

        # 预测
        label_idx = int(self._model.predict(features)[0])
        label = self._labels[label_idx] if label_idx < len(self._labels) else "unknown"

        # 置信度 & 全部分类概率
        confidence = 0.5
        if hasattr(self._model, "predict_proba"):
            proba_arr = self._model.predict_proba(features)[0]
            for i, p in enumerate(proba_arr):
                if i < len(self._labels):
                    probas[self._labels[i]] = float(p)
            confidence = float(proba_arr[label_idx])
        elif hasattr(self._model, "decision_function"):
            df = self._model.decision_function(features)
            if df.ndim > 1:
                # 多分类 SVM: softmax 归一化
                exp = np.exp(df[0] - np.max(df[0]))
                softmax = exp / exp.sum()
                for i, p in enumerate(softmax):
                    if i < len(self._labels):
                        probas[self._labels[i]] = float(p)
                confidence = float(softmax[label_idx])
            else:
                confidence = float(1.0 / (1.0 + np.exp(-abs(df[0]))))
                probas[label] = confidence

        # 去抖动
        label, _ = self._debounce(label, confidence)
        return label, confidence, probas

    def _debounce(self, label: str, confidence: float) -> Tuple[str, float]:
        """连续投票去抖动"""
        self._vote_buffer.append(label)
        if len(self._vote_buffer) > self._vote_size:
            self._vote_buffer.pop(0)

        # 统计最近 N 次中出现最多的标签
        if len(self._vote_buffer) < self._vote_size:
            return (label, confidence)

        from collections import Counter
        most_common = Counter(self._vote_buffer).most_common(1)[0]
        return (most_common[0], confidence)

    def classify_and_save(
        self,
        session_id: int,
        acc_window: np.ndarray,
        gyro_window: np.ndarray,
        timestamp: float,
    ) -> Dict:
        """
        推理并保存结果到数据库

        Returns:
            {"label": str, "confidence": float, "features": dict, "probas": dict}
        """
        import time
        label, confidence, probas = self.predict(acc_window, gyro_window)

        # 特征快照
        fv, fnames = extract_feature_vector(acc_window, gyro_window)
        feature_snapshot = {n: float(v) for n, v in zip(fnames, fv)}

        # 保存到数据库
        InferenceRepository.save(
            session_id=session_id,
            timestamp=timestamp,
            label=label,
            confidence=confidence,
            features=feature_snapshot,
        )

        return {
            "label": label,
            "confidence": confidence,
            "features": feature_snapshot,
            "probas": probas,
        }

    def manual_correct(self, session_id: int, timestamp: float, label: str) -> None:
        """
        人工纠正 — 将纠正确认结果作为标注数据存入数据库。

        ⚠️ 重要说明：此方法并**不会在线更新/重新训练模型**。

        当前模型是从 pickle 文件（artifacts/models/gait_classifier.pkl）
        加载的静态快照，推理过程中不会修改模型参数。manual_correct() 的实际行为是：
        1. 清空投票缓冲区（避免去抖动逻辑用旧结果覆盖新标签）
        2. 将 (session_id, timestamp, label) 作为人工标注样本写入 SQLite

        这些标注数据的用途：
        - 后续可导出为训练数据集（labeled training data）
        - 离线阶段重新训练或微调模型后，替换 pickle 文件即可生效
        - 设计上避免了在线训练的不确定性（概念漂移、模型退化）

        如果你希望模型持续改进，可以在积累一定量标注数据后，
        运行离线训练脚本重新生成 pickle 文件。
        """
        self._vote_buffer.clear()  # 清空投票缓冲
        InferenceRepository.save_manual_correction(session_id, timestamp, label)

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def labels(self) -> List[str]:
        return self._labels


# 全局推理引擎实例（延迟初始化）
_inference_engine: Optional[InferenceEngine] = None


def get_inference_engine() -> InferenceEngine:
    """获取全局推理引擎（懒加载）"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = InferenceEngine()
        # 尝试自动加载模型
        model_file = config.get("model.model_file", "gait_classifier.pkl")
        project_root = config.project_root
        model_path = Path(project_root) / "artifacts" / "models" / model_file
        if model_path.exists():
            _inference_engine.load_model(str(model_path))
    return _inference_engine
