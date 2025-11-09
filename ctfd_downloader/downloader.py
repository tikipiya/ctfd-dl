"""ファイルダウンローダー."""
import os
import time
import logging
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)


class Downloader:
    """ファイルダウンローダー."""

    def __init__(
        self,
        session: requests.Session,
        max_workers: int = 4,
        max_attempts: int = 3,
        backoff_base: float = 2.0,
    ):
        """
        ダウンローダーを初期化.

        Args:
            session: requests.Session オブジェクト
            max_workers: 並列ダウンロード数
            max_attempts: 最大リトライ回数
            backoff_base: 指数バックオフのベース値
        """
        self.session = session
        self.max_workers = max_workers
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.executor: Optional[ThreadPoolExecutor] = None

    def download_file(
        self,
        url: str,
        dest_path: str,
        overwrite: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """
        ファイルをダウンロード.

        Args:
            url: ダウンロードURL
            dest_path: 保存先パス
            overwrite: 既存ファイルを上書きするか
            progress_callback: 進捗コールバック (downloaded, total)

        Returns:
            成功時 True
        """
        if os.path.exists(dest_path) and not overwrite:
            logger.debug(f"ファイルが既に存在します（スキップ）: {dest_path}")
            return True

        # ディレクトリを作成
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        for attempt in range(self.max_attempts):
            try:
                response = self.session.get(url, stream=True, timeout=30)
                if response.status_code == 429:
                    # レート制限
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"レート制限に達しました。{retry_after}秒待機します")
                    time.sleep(retry_after)
                    continue

                if response.status_code != 200:
                    logger.error(f"ダウンロードに失敗しました: {url} (ステータス: {response.status_code})")
                    if attempt < self.max_attempts - 1:
                        wait_time = self.backoff_base ** attempt
                        logger.info(f"{wait_time}秒後にリトライします...")
                        time.sleep(wait_time)
                        continue
                    return False

                # Content-Length を取得
                total_size = int(response.headers.get("Content-Length", 0))
                chunk_size = 8192

                with open(dest_path, "wb") as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_size)

                logger.info(f"ダウンロード完了: {dest_path}")
                return True

            except requests.exceptions.RequestException as e:
                logger.warning(f"ダウンロード中にエラーが発生しました（試行 {attempt + 1}/{self.max_attempts}）: {e}")
                if attempt < self.max_attempts - 1:
                    wait_time = self.backoff_base ** attempt
                    time.sleep(wait_time)
                else:
                    logger.error(f"ダウンロードに失敗しました: {url}")
                    return False
            except Exception as e:
                logger.error(f"予期しないエラーが発生しました: {e}")
                return False

        return False

    def download_files_parallel(
        self,
        file_list: list[tuple[str, str]],
        overwrite: bool = False,
    ) -> dict[str, bool]:
        """
        複数ファイルを並列ダウンロード.

        Args:
            file_list: (url, dest_path) のタプルのリスト
            overwrite: 既存ファイルを上書きするか

        Returns:
            {dest_path: success} の辞書
        """
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures: dict[Future, tuple[str, str]] = {}
            for url, dest_path in file_list:
                future = executor.submit(self.download_file, url, dest_path, overwrite)
                futures[future] = (url, dest_path)

            # 進捗バー
            with tqdm(total=len(file_list), desc="ダウンロード中") as pbar:
                for future in futures:
                    url, dest_path = futures[future]
                    try:
                        success = future.result()
                        results[dest_path] = success
                        pbar.update(1)
                    except Exception as e:
                        logger.error(f"ダウンロードタスクでエラーが発生しました: {e}")
                        results[dest_path] = False
                        pbar.update(1)

        return results

