"""CTFd API クライアント."""
import time
import logging
import requests
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class CTFdClient:
    """CTFd API クライアント."""

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        クライアントを初期化.

        Args:
            base_url: CTFd インスタンスのベースURL
            api_token: API トークン（優先）
            username: ユーザ名（Tokenがない場合）
            password: パスワード（Tokenがない場合）
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.authenticated = False

        # HTTPS を強制
        if not self.base_url.startswith("https://"):
            logger.warning(f"BASE_URL が HTTPS ではありません: {self.base_url}")

    def authenticate(self) -> bool:
        """
        認証を実行.

        Returns:
            認証成功時 True
        """
        if self.api_token:
            return self._authenticate_with_token()
        elif self.username and self.password:
            return self._authenticate_with_credentials()
        else:
            logger.error("認証情報が設定されていません（API_TOKEN または USERNAME/PASSWORD）")
            return False

    def _authenticate_with_token(self) -> bool:
        """Token 認証を実行."""
        try:
            self.session.headers.update({"Authorization": f"Token {self.api_token}"})
            # 認証確認のためユーザ情報を取得
            response = self.session.get(f"{self.base_url}/api/v1/users/me")
            if response.status_code == 200:
                self.authenticated = True
                logger.info("Token 認証に成功しました")
                return True
            else:
                logger.error(f"Token 認証に失敗しました: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Token 認証中にエラーが発生しました: {e}")
            return False

    def _authenticate_with_credentials(self) -> bool:
        """ユーザ名/パスワード認証を実行."""
        try:
            # CSRF トークンを取得
            login_page = self.session.get(f"{self.base_url}/login")
            if login_page.status_code != 200:
                logger.error(f"ログインページの取得に失敗しました: {login_page.status_code}")
                return False

            # CSRF トークンを抽出（CTFd の実装に依存）
            # 一般的には hidden input または meta tag から取得
            csrf_token = None
            if "csrfNonce" in login_page.text:
                import re
                match = re.search(r'csrfNonce["\']?\s*[:=]\s*["\']([^"\']+)["\']', login_page.text)
                if match:
                    csrf_token = match.group(1)

            # ログインリクエスト
            login_data = {
                "name": self.username,
                "password": self.password,
            }
            if csrf_token:
                login_data["nonce"] = csrf_token

            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                allow_redirects=False,
            )

            if response.status_code in [200, 302]:
                # Cookie が設定されているか確認
                if self.session.cookies:
                    self.authenticated = True
                    logger.info("ユーザ名/パスワード認証に成功しました")
                    return True
                else:
                    logger.error("認証に失敗しました（Cookie が設定されませんでした）")
                    return False
            else:
                logger.error(f"ログインに失敗しました: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"認証中にエラーが発生しました: {e}")
            return False

    def list_challenges(self) -> List[Dict[str, Any]]:
        """
        課題一覧を取得.

        Returns:
            課題のリスト
        """
        if not self.authenticated:
            logger.error("認証されていません")
            return []

        try:
            challenges = []
            page = 1
            while True:
                response = self.session.get(
                    f"{self.base_url}/api/v1/challenges",
                    params={"page": page},
                )
                if response.status_code != 200:
                    logger.error(f"課題一覧の取得に失敗しました: {response.status_code}")
                    break

                data = response.json()
                if "data" in data:
                    page_challenges = data["data"]
                    if not page_challenges:
                        break
                    challenges.extend(page_challenges)
                    # ページネーション確認
                    meta = data.get("meta", {})
                    if meta.get("page", page) >= meta.get("pages", 1):
                        break
                    page += 1
                else:
                    break

            logger.info(f"{len(challenges)} 件の課題を取得しました")
            return challenges
        except Exception as e:
            logger.error(f"課題一覧の取得中にエラーが発生しました: {e}")
            return []

    def get_challenge(self, challenge_id: int) -> Optional[Dict[str, Any]]:
        """
        課題詳細を取得.

        Args:
            challenge_id: 課題ID

        Returns:
            課題詳細データ
        """
        if not self.authenticated:
            logger.error("認証されていません")
            return None

        try:
            response = self.session.get(f"{self.base_url}/api/v1/challenges/{challenge_id}")
            if response.status_code == 200:
                data = response.json()
                return data.get("data")
            else:
                logger.warning(f"課題 {challenge_id} の取得に失敗しました: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"課題 {challenge_id} の取得中にエラーが発生しました: {e}")
            return None

    def get_file_url(self, relative_path: str) -> str:
        """
        ファイルの絶対URLを取得.

        Args:
            relative_path: 相対パスまたは絶対URL

        Returns:
            絶対URL
        """
        if relative_path.startswith("http://") or relative_path.startswith("https://"):
            return relative_path
        # 相対パスの場合、base_url と結合
        if relative_path.startswith("/"):
            return urljoin(self.base_url, relative_path)
        else:
            return urljoin(f"{self.base_url}/", relative_path)

