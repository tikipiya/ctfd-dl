"""設定管理モジュール."""
import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# .env ファイルを読み込み
load_dotenv()


class Config:
    """設定管理クラス."""

    def __init__(self, config_path: Optional[str] = None):
        """
        設定を初期化.

        Args:
            config_path: 設定ファイルのパス（デフォルト: config.yaml）
        """
        self.config_path = config_path or "config.yaml"
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """設定ファイルを読み込む."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}

        # 環境変数で上書き
        self.config.setdefault("base_url", os.getenv("CTFD_BASE_URL", ""))
        self.config.setdefault("api_token", os.getenv("CTFD_API_TOKEN", ""))
        self.config.setdefault("username", os.getenv("CTFD_USERNAME", ""))
        self.config.setdefault("password", os.getenv("CTFD_PASSWORD", ""))

        # デフォルト値の設定
        defaults = {
            "output_dir": "./challenges",
            "concurrency": 4,
            "retry": {
                "max_attempts": 3,
                "backoff_base": 2,
            },
            "file": {
                "overwrite": False,
                "sanitize_names": True,
            },
            "logging": {
                "level": "INFO",
            },
        }

        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
            elif isinstance(value, dict):
                self.config[key] = {**value, **self.config.get(key, {})}

    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得.

        Args:
            key: 設定キー（ドット区切りでネスト可能）
            default: デフォルト値

        Returns:
            設定値
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any):
        """
        設定値を設定.

        Args:
            key: 設定キー（ドット区切りでネスト可能）
            value: 設定値
        """
        keys = key.split(".")
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def setup_logging(self):
        """ロギングを設定."""
        level = getattr(logging, self.get("logging.level", "INFO").upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

