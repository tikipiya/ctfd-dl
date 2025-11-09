"""CTFd クライアントのテスト."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ctfd_downloader.client import CTFdClient


class TestCTFdClient:
    """CTFdClient のテスト."""

    def test_get_file_url_absolute(self):
        """絶対URLの処理テスト."""
        client = CTFdClient(base_url="https://ctf.example.com")
        url = client.get_file_url("https://example.com/file.zip")
        assert url == "https://example.com/file.zip"

    def test_get_file_url_relative_root(self):
        """ルート相対パスの処理テスト."""
        client = CTFdClient(base_url="https://ctf.example.com")
        url = client.get_file_url("/files/abc123/file.zip")
        assert url == "https://ctf.example.com/files/abc123/file.zip"

    def test_get_file_url_relative(self):
        """相対パスの処理テスト."""
        client = CTFdClient(base_url="https://ctf.example.com")
        url = client.get_file_url("files/abc123/file.zip")
        assert url == "https://ctf.example.com/files/abc123/file.zip"

    @patch("ctfd_downloader.client.requests.Session")
    def test_authenticate_with_token_success(self, mock_session_class):
        """Token認証の成功テスト."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        client = CTFdClient(
            base_url="https://ctf.example.com",
            api_token="test_token",
        )
        result = client.authenticate()

        assert result is True
        assert client.authenticated is True
        mock_session.headers.update.assert_called_once()
        mock_session.get.assert_called_once_with("https://ctf.example.com/api/v1/users/me")

    @patch("ctfd_downloader.client.requests.Session")
    def test_authenticate_with_token_failure(self, mock_session_class):
        """Token認証の失敗テスト."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 401
        mock_session.get.return_value = mock_response

        client = CTFdClient(
            base_url="https://ctf.example.com",
            api_token="invalid_token",
        )
        result = client.authenticate()

        assert result is False
        assert client.authenticated is False

