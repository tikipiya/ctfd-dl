"""ストレージのテスト."""
import pytest
import tempfile
import shutil
from pathlib import Path
from ctfd_downloader.storage import Storage


class TestStorage:
    """Storage のテスト."""

    def setup_method(self):
        """テスト前のセットアップ."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(root_dir=self.temp_dir, sanitize_names=True)

    def teardown_method(self):
        """テスト後のクリーンアップ."""
        shutil.rmtree(self.temp_dir)

    def test_sanitize_filename_basic(self):
        """基本的なファイル名正規化テスト."""
        assert self.storage.sanitize_filename("test.txt") == "test.txt"
        assert self.storage.sanitize_filename("test file.zip") == "test file.zip"

    def test_sanitize_filename_forbidden_chars(self):
        """禁止文字の除去テスト."""
        assert self.storage.sanitize_filename("test<>file.zip") == "test__file.zip"
        assert self.storage.sanitize_filename("test:file.zip") == "test_file.zip"
        assert self.storage.sanitize_filename("test/file.zip") == "test_file.zip"

    def test_sanitize_filename_multiple_underscores(self):
        """連続アンダースコアの正規化テスト."""
        assert self.storage.sanitize_filename("test___file.zip") == "test_file.zip"

    def test_sanitize_filename_long_name(self):
        """長いファイル名の切り詰めテスト."""
        long_name = "a" * 300
        result = self.storage.sanitize_filename(long_name)
        assert len(result) == 255

    def test_sanitize_filename_empty(self):
        """空文字列の処理テスト."""
        assert self.storage.sanitize_filename("") == "unnamed"
        assert self.storage.sanitize_filename("   ") == "unnamed"

    def test_get_challenge_dir(self):
        """課題ディレクトリパスの取得テスト."""
        path = self.storage.get_challenge_dir("Web", "SQLi 101")
        assert isinstance(path, Path)
        assert "Web" in str(path)
        assert "SQLi" in str(path)

    def test_get_challenge_dir_uncategorized(self):
        """カテゴリなしの場合のテスト."""
        path = self.storage.get_challenge_dir("", "Test Challenge")
        assert "Uncategorized" in str(path)

    def test_save_metadata(self):
        """メタデータ保存テスト."""
        challenge_dir = Path(self.temp_dir) / "test_challenge"
        challenge_dir.mkdir(parents=True)

        metadata = {
            "id": 1,
            "name": "Test Challenge",
            "category": "Web",
            "value": 100,
        }
        self.storage.save_metadata(challenge_dir, metadata)

        metadata_path = challenge_dir / "metadata.json"
        assert metadata_path.exists()

        import json
        with open(metadata_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["id"] == 1
        assert "fetched_at" in saved_data

    def test_save_readme(self):
        """README保存テスト."""
        challenge_dir = Path(self.temp_dir) / "test_challenge"
        challenge_dir.mkdir(parents=True)

        metadata = {
            "name": "Test Challenge",
            "category": "Web",
            "value": 100,
            "description": "<p>Test description</p>",
            "files": ["/files/test.zip"],
        }
        self.storage.save_readme(challenge_dir, metadata)

        readme_path = challenge_dir / "README.md"
        assert readme_path.exists()

        content = readme_path.read_text(encoding="utf-8")
        assert "Test Challenge" in content
        assert "Web" in content
        assert "100" in content

