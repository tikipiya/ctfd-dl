"""CLI エントリーポイント."""
import argparse
import sys
import logging

from ctfd_downloader.config import Config
from ctfd_downloader.client import CTFdClient
from ctfd_downloader.downloader import Downloader
from ctfd_downloader.storage import Storage

logger = logging.getLogger(__name__)


def main():
    """メイン関数."""
    parser = argparse.ArgumentParser(
        description="CTFd challenge downloader and organizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="設定ファイルのパス (default: config.yaml)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="CTFd インスタンスのベースURL（設定ファイルより優先）",
    )
    parser.add_argument(
        "--token",
        type=str,
        help="API トークン（設定ファイルより優先）",
    )
    parser.add_argument(
        "--user",
        type=str,
        help="ユーザ名（設定ファイルより優先）",
    )
    parser.add_argument(
        "--password",
        type=str,
        help="パスワード（設定ファイルより優先）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="出力ディレクトリ（設定ファイルより優先）",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        help="並列ダウンロード数（設定ファイルより優先）",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="メタデータのみ取得し、ファイルダウンロードをスキップ",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="既存ファイルを上書き",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを出力",
    )

    args = parser.parse_args()

    # 設定を読み込み
    config = Config(args.config)

    # コマンドライン引数で上書き
    if args.base_url:
        config.set("base_url", args.base_url)
    if args.token:
        config.set("api_token", args.token)
    if args.user:
        config.set("username", args.user)
    if args.password:
        config.set("password", args.password)
    if args.output:
        config.set("output_dir", args.output)
    if args.concurrency:
        config.set("concurrency", args.concurrency)
    if args.force_overwrite:
        config.set("file.overwrite", True)
    if args.verbose:
        config.set("logging.level", "DEBUG")

    # ロギング設定
    config.setup_logging()

    # 必須設定の確認
    base_url = config.get("base_url")
    if not base_url:
        logger.error("BASE_URL が設定されていません")
        sys.exit(1)

    api_token = config.get("api_token")
    username = config.get("username")
    password = config.get("password")

    if not api_token and not (username and password):
        logger.error("認証情報が設定されていません（API_TOKEN または USERNAME/PASSWORD）")
        sys.exit(1)

    # クライアント初期化
    client = CTFdClient(
        base_url=base_url,
        api_token=api_token,
        username=username,
        password=password,
    )

    # 認証
    if not client.authenticate():
        logger.error("認証に失敗しました")
        sys.exit(1)

    # ストレージ初期化
    output_dir = config.get("output_dir", "./challenges")
    sanitize_names = config.get("file.sanitize_names", True)
    storage = Storage(root_dir=output_dir, sanitize_names=sanitize_names)

    # ダウンローダー初期化
    concurrency = config.get("concurrency", 4)
    max_attempts = config.get("retry.max_attempts", 3)
    backoff_base = config.get("retry.backoff_base", 2.0)
    downloader = Downloader(
        session=client.session,
        max_workers=concurrency,
        max_attempts=max_attempts,
        backoff_base=backoff_base,
    )

    # 課題一覧を取得
    logger.info("課題一覧を取得しています...")
    challenges = client.list_challenges()
    if not challenges:
        logger.warning("課題が見つかりませんでした")
        sys.exit(0)

    # 各課題を処理
    overwrite = config.get("file.overwrite", False)
    success_count = 0
    error_count = 0
    file_download_count = 0
    file_success_count = 0

    for challenge in challenges:
        challenge_id = challenge.get("id")
        challenge_name = challenge.get("name", "Unknown")
        category = challenge.get("category", "Uncategorized")

        logger.info(f"課題を処理中: [{category}] {challenge_name} (ID: {challenge_id})")

        try:
            # 課題詳細を取得
            detail = client.get_challenge(challenge_id)
            if not detail:
                logger.warning(f"課題 {challenge_id} の詳細を取得できませんでした")
                error_count += 1
                continue

            # source_url を追加
            detail["source_url"] = f"{base_url}/challenges/{challenge_id}"

            # ディレクトリを作成
            challenge_dir = storage.get_challenge_dir(category, challenge_name)
            storage.ensure_dir(challenge_dir)

            # メタデータとREADMEを保存
            storage.save_metadata(challenge_dir, detail)
            storage.save_readme(challenge_dir, detail)

            # ファイルをダウンロード
            files = detail.get("files", [])
            if files and not args.skip_download:
                file_list = []
                for file_path in files:
                    file_url = client.get_file_url(file_path)
                    dest_path = storage.get_file_path(challenge_dir, file_url)
                    file_list.append((file_url, str(dest_path)))
                    file_download_count += 1

                if file_list:
                    logger.info(f"  {len(file_list)} 個のファイルをダウンロード中...")
                    results = downloader.download_files_parallel(file_list, overwrite=overwrite)
                    file_success_count += sum(1 for success in results.values() if success)

            success_count += 1
            logger.info(f"  ✓ 完了: {challenge_name}")

        except Exception as e:
            logger.error(f"課題 {challenge_id} の処理中にエラーが発生しました: {e}", exc_info=True)
            error_count += 1

    # 統計を出力
    logger.info("=" * 60)
    logger.info("処理完了")
    logger.info(f"  課題: 成功 {success_count} / 失敗 {error_count} / 合計 {len(challenges)}")
    if not args.skip_download:
        logger.info(f"  ファイル: 成功 {file_success_count} / 合計 {file_download_count}")
    logger.info(f"  出力先: {output_dir}")
    logger.info("=" * 60)

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

