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

    def _deep_merge(self, defaults: Dict[str, Any], user_config: Any) -> Dict[str, Any]:
        """
        デフォルト設定とユーザー設定を安全に再帰的マージ.

        Args:
            defaults: デフォルト設定辞書
            user_config: ユーザー設定（辞書でない可能性もある）

        Returns:
            マージされた設定辞書
        """
        if not isinstance(user_config, dict):
            user_config = {}

        result = {}
        # デフォルトに含まれるキーを走査
        for key, def_val in defaults.items():
            user_val = user_config.get(key)
            if isinstance(def_val, dict):
                if user_val is None or not isinstance(user_val, dict):
                    result[key] = self._deep_merge(def_val, {})
                else:
                    result[key] = self._deep_merge(def_val, user_val)
            else:
                if user_val is None:
                    result[key] = def_val
                else:
                    result[key] = user_val

        # デフォルトに含まれないユーザー独自のキーも保持
        for key, user_val in user_config.items():
            if key not in result:
                result[key] = user_val

        return result

    def _sanitize_and_validate(self):
        """設定値の型変換と無効値のバリデーション・正規化を行う."""
        # base_url の正規化
        base_url = self.config.get("base_url")
        if base_url and isinstance(base_url, str):
            base_url = base_url.strip()
            if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
                base_url = f"https://{base_url}"
            self.config["base_url"] = base_url
        else:
            self.config["base_url"] = ""

        # api_token, username, password の文字列正規化
        for cred_key in ["api_token", "username", "password"]:
            val = self.config.get(cred_key)
            if val is not None and isinstance(val, str):
                self.config[cred_key] = val.strip()
            elif val is None:
                self.config[cred_key] = ""

        # concurrency の数値化
        concurrency = self.config.get("concurrency")
        try:
            concurrency_int = int(concurrency)
            self.config["concurrency"] = concurrency_int if concurrency_int > 0 else 4
        except (ValueError, TypeError):
            self.config["concurrency"] = 4

        # retry の型変換とバリデーション
        retry = self.config.get("retry")
        if not isinstance(retry, dict):
            retry = {}
            self.config["retry"] = retry

        try:
            max_attempts = int(retry.get("max_attempts", 3))
            retry["max_attempts"] = max_attempts if max_attempts > 0 else 3
        except (ValueError, TypeError):
            retry["max_attempts"] = 3

        try:
            backoff_base = float(retry.get("backoff_base", 2.0))
            retry["backoff_base"] = backoff_base if backoff_base > 0 else 2.0
        except (ValueError, TypeError):
            retry["backoff_base"] = 2.0

        # file の型変換とバリデーション
        file_cfg = self.config.get("file")
        if not isinstance(file_cfg, dict):
            file_cfg = {}
            self.config["file"] = file_cfg

        def to_bool(val: Any, default: bool) -> bool:
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                s = val.strip().lower()
                if s in ("true", "1", "yes", "on"):
                    return True
                if s in ("false", "0", "no", "off"):
                    return False
            if isinstance(val, (int, float)):
                return bool(val)
            return default

        file_cfg["overwrite"] = to_bool(file_cfg.get("overwrite"), False)
        file_cfg["sanitize_names"] = to_bool(file_cfg.get("sanitize_names"), True)

        # logging のレベル正規化
        logging_cfg = self.config.get("logging")
        if not isinstance(logging_cfg, dict):
            logging_cfg = {}
            self.config["logging"] = logging_cfg

        lvl = logging_cfg.get("level")
        if isinstance(lvl, str) and lvl.strip().upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logging_cfg["level"] = lvl.strip().upper()
        else:
            logging_cfg["level"] = "INFO"

    def _load_config(self):
        """設定ファイルを読み込む."""
        raw_config: Dict[str, Any] = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        raw_config = loaded
            except Exception as e:
                logging.warning(f"設定ファイル {self.config_path} の読み込みに失敗しました: {e}")

        # デフォルト値の定義
        defaults = {
            "base_url": "",
            "api_token": "",
            "username": "",
            "password": "",
            "output_dir": "./challenges",
            "concurrency": 4,
            "retry": {
                "max_attempts": 3,
                "backoff_base": 2.0,
            },
            "file": {
                "overwrite": False,
                "sanitize_names": True,
            },
            "logging": {
                "level": "INFO",
            },
        }

        # デフォルト設定とマージ
        self.config = self._deep_merge(defaults, raw_config)

        # 環境変数で空値や未設定項目を補完
        env_mappings = {
            "base_url": "CTFD_BASE_URL",
            "api_token": "CTFD_API_TOKEN",
            "username": "CTFD_USERNAME",
            "password": "CTFD_PASSWORD",
        }
        for key, env_name in env_mappings.items():
            current_val = self.config.get(key)
            if not current_val or (isinstance(current_val, str) and not current_val.strip()):
                env_val = os.getenv(env_name, "")
                if env_val:
                    self.config[key] = env_val

        # 型変換と正規化
        self._sanitize_and_validate()

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
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        # 設定変更時に再バリデーション
        self._sanitize_and_validate()

    def setup_logging(self):
        """ロギングを設定."""
        level_str = str(self.get("logging.level", "INFO")).upper()
        level = getattr(logging, level_str, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


