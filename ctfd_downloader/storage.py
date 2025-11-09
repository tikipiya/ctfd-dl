"""ストレージ管理モジュール."""
import os
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Storage:
    """ストレージ管理クラス."""

    # OS で禁止されている文字
    FORBIDDEN_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    MAX_FILENAME_LENGTH = 255

    def __init__(self, root_dir: str = "./challenges", sanitize_names: bool = True):
        """
        ストレージを初期化.

        Args:
            root_dir: ルートディレクトリ
            sanitize_names: ファイル名を正規化するか
        """
        self.root_dir = Path(root_dir).resolve()
        self.sanitize_names = sanitize_names
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, name: str) -> str:
        """
        ファイル名を正規化（OS 安全化）.

        Args:
            name: 元のファイル名

        Returns:
            正規化されたファイル名
        """
        if not self.sanitize_names:
            return name

        # 禁止文字を除去
        sanitized = re.sub(self.FORBIDDEN_CHARS, "_", name)
        # 連続するアンダースコアを1つに
        sanitized = re.sub(r"_+", "_", sanitized)
        # 先頭・末尾のアンダースコアと空白を除去
        sanitized = sanitized.strip("_ ")
        # 長さ制限
        if len(sanitized) > self.MAX_FILENAME_LENGTH:
            sanitized = sanitized[:self.MAX_FILENAME_LENGTH]
        # 空文字列の場合はデフォルト名
        if not sanitized:
            sanitized = "unnamed"

        return sanitized

    def get_challenge_dir(self, category: str, challenge_name: str) -> Path:
        """
        課題ディレクトリのパスを取得.

        Args:
            category: カテゴリ名
            challenge_name: 課題名

        Returns:
            ディレクトリパス
        """
        safe_category = self.sanitize_filename(category or "Uncategorized")
        safe_name = self.sanitize_filename(challenge_name)
        return self.root_dir / safe_category / safe_name

    def ensure_dir(self, path: Path):
        """
        ディレクトリを作成.

        Args:
            path: ディレクトリパス
        """
        path.mkdir(parents=True, exist_ok=True)
        # パーミッション設定（700）
        os.chmod(path, 0o700)

    def save_metadata(self, challenge_dir: Path, metadata: Dict[str, Any]):
        """
        メタデータを保存.

        Args:
            challenge_dir: 課題ディレクトリ
            metadata: メタデータ辞書
        """
        metadata_path = challenge_dir / "metadata.json"
        # fetched_at を追加
        metadata_with_timestamp = {
            **metadata,
            "fetched_at": datetime.now().isoformat(),
            "source_url": metadata.get("source_url", ""),
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_with_timestamp, f, indent=2, ensure_ascii=False)
        logger.debug(f"メタデータを保存しました: {metadata_path}")

    def save_readme(self, challenge_dir: Path, metadata: Dict[str, Any]):
        """
        README.md を生成・保存.

        Args:
            challenge_dir: 課題ディレクトリ
            metadata: メタデータ辞書
        """
        readme_path = challenge_dir / "README.md"

        # 説明文からHTMLタグを除去（簡易版）
        description = metadata.get("description", "")
        if description:
            import re
            description = re.sub(r"<[^>]+>", "", description)
            description = description.strip()

        # ファイル一覧
        files = metadata.get("files", [])
        file_list = "\n".join([f"- {os.path.basename(f)}" for f in files]) if files else "- （なし）"

        readme_content = f"""# {metadata.get('name', 'Unknown Challenge')}

**カテゴリ:** {metadata.get('category', 'Uncategorized')}
**ポイント:** {metadata.get('value', 0)}
**取得日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**ソースURL:** {metadata.get('source_url', 'N/A')}

## 説明

{description or '（説明なし）'}

## ファイル

{file_list}

## 注意

このファイルは CTFd から自動取得されたものです。
ダウンロードした実行ファイルは直接実行せず、適切な環境で解析してください。
"""

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        logger.debug(f"README.md を保存しました: {readme_path}")

    def get_file_path(self, challenge_dir: Path, file_url: str) -> Path:
        """
        ファイルの保存パスを取得.

        Args:
            challenge_dir: 課題ディレクトリ
            file_url: ファイルURL

        Returns:
            ファイルパス
        """
        files_dir = challenge_dir / "files"
        files_dir.mkdir(exist_ok=True)
        filename = os.path.basename(file_url.split("?")[0])  # クエリパラメータを除去
        safe_filename = self.sanitize_filename(filename)
        return files_dir / safe_filename

