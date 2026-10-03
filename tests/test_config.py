"""Config モジュールの単体テスト."""
import os
import tempfile
import unittest
from ctfd_downloader.config import Config


class TestConfigRobustness(unittest.TestCase):
    """様々なフォーマットの config.yaml に対する堅牢性テスト."""

    def setUp(self):
        """テスト用の作業ディレクトリ作成."""
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """テスト用の作業ディレクトリ削除."""
        self.temp_dir.cleanup()

    def create_yaml_file(self, content: str) -> str:
        """一時 YAML ファイルを作成."""
        file_path = os.path.join(self.temp_dir.name, "config.yaml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_empty_yaml_file(self):
        """完全に空のファイルまたは空辞書の場合."""
        path = self.create_yaml_file("")
        config = Config(path)

        self.assertEqual(config.get("concurrency"), 4)
        self.assertEqual(config.get("retry.max_attempts"), 3)
        self.assertEqual(config.get("retry.backoff_base"), 2.0)
        self.assertFalse(config.get("file.overwrite"))
        self.assertTrue(config.get("file.sanitize_names"))

    def test_empty_sections(self):
        """空セクション (retry:, file:, logging:) のみ指定された場合."""
        content = """
base_url: "https://ctf.example.com"
retry:
file:
logging:
"""
        path = self.create_yaml_file(content)
        config = Config(path)

        self.assertEqual(config.get("base_url"), "https://ctf.example.com")
        self.assertEqual(config.get("retry.max_attempts"), 3)
        self.assertEqual(config.get("retry.backoff_base"), 2.0)
        self.assertFalse(config.get("file.overwrite"))

    def test_string_numbers_and_booleans(self):
        """数値が文字列で指定されている場合."""
        content = """
concurrency: "8"
retry:
  max_attempts: "5"
  backoff_base: "1.5"
file:
  overwrite: "true"
  sanitize_names: "false"
"""
        path = self.create_yaml_file(content)
        config = Config(path)

        self.assertEqual(config.get("concurrency"), 8)
        self.assertEqual(config.get("retry.max_attempts"), 5)
        self.assertEqual(config.get("retry.backoff_base"), 1.5)
        self.assertTrue(config.get("file.overwrite"))
        self.assertFalse(config.get("file.sanitize_names"))

    def test_invalid_values_fallback(self):
        """無効な数値や文字列が指定された場合のデフォルト値フォールバック."""
        content = """
concurrency: -5
retry:
  max_attempts: "invalid"
  backoff_base: -1
logging:
  level: "INVALID_LEVEL"
"""
        path = self.create_yaml_file(content)
        config = Config(path)

        self.assertEqual(config.get("concurrency"), 4)
        self.assertEqual(config.get("retry.max_attempts"), 3)
        self.assertEqual(config.get("retry.backoff_base"), 2.0)
        self.assertEqual(config.get("logging.level"), "INFO")

    def test_base_url_scheme_autofix(self):
        """base_url にスキームが付いていない場合への自動付加."""
        content = """
base_url: "ctf.example.com"
"""
        path = self.create_yaml_file(content)
        config = Config(path)

        self.assertEqual(config.get("base_url"), "https://ctf.example.com")

    def test_env_var_fallback_when_yaml_empty(self):
        """YAML の項目が空文字や None の場合に環境変数が適用されるか."""
        content = """
base_url: ""
api_token: null
"""
        path = self.create_yaml_file(content)

        os.environ["CTFD_BASE_URL"] = "https://env.example.com"
        os.environ["CTFD_API_TOKEN"] = "env-token-123"
        try:
            config = Config(path)
            self.assertEqual(config.get("base_url"), "https://env.example.com")
            self.assertEqual(config.get("api_token"), "env-token-123")
        finally:
            os.environ.pop("CTFD_BASE_URL", None)
            os.environ.pop("CTFD_API_TOKEN", None)

    def test_safe_get_nested(self):
        """中間キーが存在しない、または None の場合の安全な get."""
        content = """
retry: null
"""
        path = self.create_yaml_file(content)
        config = Config(path)

        self.assertEqual(config.get("retry.max_attempts"), 3)
        self.assertEqual(config.get("non_existent.key", "default_val"), "default_val")


if __name__ == "__main__":
    unittest.main()
