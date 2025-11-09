# CTFd Downloader

CTFd インスタンスから課題情報と添付ファイルを自動取得・整理する Python ツールです。

## 機能

- Token 認証またはユーザ名/パスワード認証による CTFd API へのアクセス
- 課題一覧・詳細情報の取得
- 添付ファイルの自動ダウンロード
- `challenges/<Category>/<Challenge Name>/` の構造で整理保存
- メタデータ（JSON）と README（Markdown）の自動生成
- 並列ダウンロードとリトライ機能
- ロギングとエラーハンドリング

## インストール

```bash
pip install ctfd-dl
```

## 設定

1. `config.example.yaml` を `config.yaml` にコピー
2. `config.yaml` を編集して CTFd インスタンスの情報を設定

```yaml
base_url: "https://ctf.example.com"
api_token: "your_api_token_here"  # 推奨
# または
username: "your_username"
password: "your_password"
output_dir: "./challenges"
concurrency: 4
```

または環境変数を使用：

```bash
export CTFD_BASE_URL="https://ctf.example.com"
export CTFD_API_TOKEN="your_api_token_here"
```

## 使用方法

パッケージをインストールすると、`ctfd-dl` コマンドが利用可能になります。

```bash
# 基本的な使用
ctfd-dl --config config.yaml

# コマンドライン引数で設定を上書き
ctfd-dl --base-url https://ctf.example.com --token YOUR_TOKEN --output ./my_challenges

# メタデータのみ取得（ファイルダウンロードをスキップ）
ctfd-dl --skip-download

# 詳細ログを出力
ctfd-dl --verbose
```

## 出力構造

```
challenges/
└─ <Category>/
   └─ <Challenge Name>/
      ├─ files/
      │  ├─ attached1.zip
      │  └─ script.py
      ├─ metadata.json
      └─ README.md
```

## 注意事項

- **法的注意**: 他者運営の CTFd インスタンスにアクセスする場合は、必ず運営者の許可を得てください。
- **セキュリティ**: ダウンロードした実行ファイルは直接実行せず、適切な環境で解析してください。
- **サーバ負荷**: 並列ダウンロード数（`concurrency`）を適切に設定し、サーバに負荷をかけないようにしてください。

## ライセンス

MIT License

## 作者

tikisan (GitHub: @tikipiya)

