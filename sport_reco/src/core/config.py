"""
统一配置加载器

从 YAML 配置文件加载配置，支持多环境覆盖。
加载优先级：default.yaml -> {env}.yaml -> 环境变量
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """应用配置管理器（单例模式）"""

    _instance: Optional["Config"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._config:
            self._load()

    def _load(self) -> None:
        """加载配置文件"""
        project_root = Path(__file__).resolve().parent.parent.parent
        config_dir = project_root / "configs"

        # 1. 加载默认配置
        default_path = config_dir / "default.yaml"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

        # 2. 加载模型子配置
        model_configs = ["preprocess.yaml", "features.yaml", "training.yaml"]
        for cfg_file in model_configs:
            cfg_path = config_dir / "model" / cfg_file
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    sub_cfg = yaml.safe_load(f) or {}
                    key = cfg_file.replace(".yaml", "")
                    if key not in self._config:
                        self._config[key] = {}
                    self._config[key].update(sub_cfg)

        # 3. 加载环境覆盖配置
        env = os.environ.get("SPORT_RECO_ENV", "dev")
        env_path = config_dir / f"{env}.yaml"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                env_config = yaml.safe_load(f) or {}
                self._deep_update(self._config, env_config)

        # 4. 注入项目根路径
        self._config["_project_root"] = str(project_root)

    @staticmethod
    def _deep_update(base: Dict, override: Dict) -> None:
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_update(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持点号分隔的路径"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def get_all(self) -> Dict[str, Any]:
        """获取全部配置"""
        return self._config.copy()

    @property
    def project_root(self) -> str:
        return self._config.get("_project_root", "")

    @property
    def debug(self) -> bool:
        return self.get("app.debug", False)

    @property
    def host(self) -> str:
        return self.get("app.host", "0.0.0.0")

    @property
    def port(self) -> int:
        return self.get("app.port", 5000)


# 全局配置实例
config = Config()
