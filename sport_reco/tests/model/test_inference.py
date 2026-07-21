"""
模型推理回归测试

验证推理引擎能正确加载模型并输出合理结果。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from src.service.inference import InferenceEngine
from src.core.config import config


def test_inference_engine_load():
    """测试模型加载"""
    project_root = config.project_root
    model_path = Path(project_root) / "artifacts" / "models" / "gait_classifier.pkl"

    if not model_path.exists():
        print(f"[SKIP] 模型文件不存在: {model_path}")
        print("  请先运行: python -m ml.train")
        return

    engine = InferenceEngine(str(model_path))
    assert engine.is_loaded, "模型应成功加载"

    # 测试预测
    acc = np.random.randn(100, 3)
    gyro = np.random.randn(100, 3)
    label, confidence, probas = engine.predict(acc, gyro)

    assert label in engine.labels or label == "unknown", f"标签应在列表中: {label}"
    assert 0 <= confidence <= 1, f"置信度应在 [0,1]: {confidence}"
    assert isinstance(probas, dict), "应返回概率分布字典"

    print(f"  预测: label={label}, confidence={confidence:.2%}, probas={probas}")
    print("✓ 模型推理回归测试通过")


def test_empty_model():
    """测试空模型预测"""
    engine = InferenceEngine()
    acc = np.random.randn(100, 3)
    gyro = np.random.randn(100, 3)
    label, confidence, probas = engine.predict(acc, gyro)
    assert label == "unknown"
    assert confidence == 0.0
    assert probas == {}
    print("✓ 空模型回退测试通过")


if __name__ == "__main__":
    test_empty_model()
    test_inference_engine_load()
