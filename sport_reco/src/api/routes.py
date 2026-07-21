"""
REST API 路由

提供会话管理、数据查询、模型信息等 HTTP 接口。
"""

from flask import Blueprint, jsonify, render_template, request

from src.data.repository import InferenceRepository, SensorRepository, SessionRepository
from src.service.inference import get_inference_engine

api = Blueprint("api", __name__)


# ============================================================
#  页面路由
# ============================================================

@api.route("/")
def dashboard():
    """电脑端监控 Dashboard"""
    return render_template("index.html", page="dashboard")


@api.route("/mobile")
def mobile():
    """手机端传感器采集页面"""
    return render_template("mobile.html", page="mobile")


# ============================================================
#  REST 接口
# ============================================================

@api.route("/api/health", methods=["GET"])
def health_check():
    """健康检查"""
    engine = get_inference_engine()
    return jsonify({
        "status": "ok",
        "model_loaded": engine.is_loaded,
        "labels": engine.labels if engine.is_loaded else [],
    })


@api.route("/api/sessions", methods=["GET"])
def list_sessions():
    """获取会话列表"""
    limit = request.args.get("limit", 20, type=int)
    sessions = SessionRepository.get_recent(limit)
    return jsonify({"sessions": sessions, "count": len(sessions)})


@api.route("/api/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    """获取单个会话详情"""
    # 传感器数据
    sensor_data = SensorRepository.get_as_numpy(session_id)
    # 推理历史
    inferences = InferenceRepository.get_session_history(session_id)

    n_samples = len(sensor_data.get("timestamps", []))
    classification = {}
    if inferences:
        # 统计每类运动的持续比例
        from collections import Counter
        labels = [inf["predicted_label"] for inf in inferences]
        classification = dict(Counter(labels))
        classification["primary"] = Counter(labels).most_common(1)[0][0] if labels else "unknown"

    return jsonify({
        "session_id": session_id,
        "n_samples": n_samples,
        "n_inferences": len(inferences),
        "classification": classification,
        "inferences": inferences[-100:],  # 最近100条
    })


@api.route("/api/sessions/<int:session_id>/sensor_data", methods=["GET"])
def get_session_sensor_data(session_id):
    """获取会话的传感器数据（支持采样）"""
    downsample = request.args.get("downsample", 1, type=int)
    limit = request.args.get("limit", None, type=int)

    data = SensorRepository.get_as_numpy(session_id)
    if data["timestamps"].size == 0:
        return jsonify({"data": [], "count": 0})

    n = len(data["timestamps"])
    idx = slice(0, n, downsample)
    if limit and n // downsample > limit:
        idx = slice(0, min(n, limit * downsample), downsample)

    result = []
    for i in range(idx.start, min(idx.stop or n, n), idx.step or 1):
        point = {
            "timestamp": float(data["timestamps"][i]),
            "acc_x": float(data["acc"][i, 0]),
            "acc_y": float(data["acc"][i, 1]),
            "acc_z": float(data["acc"][i, 2]),
            "gyro_x": float(data["gyro"][i, 0]),
            "gyro_y": float(data["gyro"][i, 1]),
            "gyro_z": float(data["gyro"][i, 2]),
        }
        if data["gps"] is not None and i < len(data["gps"]):
            point["lat"] = float(data["gps"][i, 0])
            point["lng"] = float(data["gps"][i, 1])
        result.append(point)

    return jsonify({"data": result, "count": len(result)})


@api.route("/api/model/info", methods=["GET"])
def model_info():
    """获取模型信息"""
    engine = get_inference_engine()
    return jsonify({
        "loaded": engine.is_loaded,
        "labels": engine.labels,
        "model_type": type(engine._model).__name__ if engine._model else None,
    })


# ============================================================
#  错误处理
# ============================================================

@api.errorhandler(404)
def not_found(e):
    return jsonify({"error": "资源不存在"}), 404


@api.errorhandler(500)
def server_error(e):
    return jsonify({"error": "服务器内部错误"}), 500
