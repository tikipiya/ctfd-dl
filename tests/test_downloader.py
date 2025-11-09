"""ダウンローダーのテスト."""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from ctfd_downloader.downloader import Downloader
import requests


class TestDownloader:
    """Downloader のテスト."""

    def setup_method(self):
        """テスト前のセットアップ."""
        self.temp_dir = tempfile.mkdtemp()
        self.session = Mock()
        self.downloader = Downloader(
            session=self.session,
            max_workers=2,
            max_attempts=3,
            backoff_base=2.0,
        )

    def teardown_method(self):
        """テスト後のクリーンアップ."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_download_file_success(self):
        """ダウンロード成功テスト."""
        dest_path = os.path.join(self.temp_dir, "test_file.txt")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "10"}
        mock_response.iter_content = lambda chunk_size: [b"test data"]

        self.session.get.return_value = mock_response

        result = self.downloader.download_file(
            "https://example.com/file.txt",
            dest_path,
            overwrite=False,
        )

        assert result is True
        assert os.path.exists(dest_path)

    def test_download_file_skip_existing(self):
        """既存ファイルのスキップテスト."""
        dest_path = os.path.join(self.temp_dir, "existing_file.txt")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "w") as f:
            f.write("existing")

        result = self.downloader.download_file(
            "https://example.com/file.txt",
            dest_path,
            overwrite=False,
        )

        assert result is True
        # セッションのgetが呼ばれていないことを確認
        self.session.get.assert_not_called()

    def test_download_file_404_error(self):
        """404エラーのテスト."""
        mock_response = Mock()
        mock_response.status_code = 404
        self.session.get.return_value = mock_response

        dest_path = os.path.join(self.temp_dir, "not_found.txt")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        result = self.downloader.download_file(
            "https://example.com/notfound.txt",
            dest_path,
            overwrite=False,
        )

        assert result is False

    def test_download_file_rate_limit(self):
        """レート制限のテスト."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.headers = {"Content-Length": "10"}
        mock_response_200.iter_content = lambda chunk_size: [b"test data"]

        self.session.get.side_effect = [mock_response_429, mock_response_200]

        dest_path = os.path.join(self.temp_dir, "rate_limited.txt")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        with patch("time.sleep"):  # スリープをモック
            result = self.downloader.download_file(
                "https://example.com/file.txt",
                dest_path,
                overwrite=False,
            )

        assert result is True

