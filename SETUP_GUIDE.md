# 歌枠タイムスタンプWebサイト セットアップガイド

このガイドでは、GitHub Pagesを使って自動更新される歌枠タイムスタンプサイトを公開する手順を説明します。

## 📋 前提条件

- GitHubアカウント
- YouTube Data API v3のAPIキー

## 🚀 セットアップ手順

### 1. リポジトリの準備

```bash
# リポジトリをGitHubにプッシュ（まだの場合）
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/youtube-timestamp-scraper.git
git push -u origin main
```

### 2. YouTube API キーの設定

#### 2.1 APIキーを取得

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成
3. 「APIとサービス」→「ライブラリ」から「YouTube Data API v3」を有効化
4. 「認証情報」→「認証情報を作成」→「APIキー」を選択
5. 生成されたAPIキーをコピー

#### 2.2 GitHub Secretsに登録

1. GitHubリポジトリページを開く
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. Name: `YOUTUBE_API_KEY`
5. Value: コピーしたAPIキーを貼り付け
6. **Add secret** をクリック

### 3. GitHub Pagesの有効化

1. リポジトリの **Settings** タブを開く
2. 左メニューから **Pages** を選択
3. **Source** で以下を設定:
   - Branch: `main`
   - Folder: `/docs`
4. **Save** をクリック

数分後、以下のURLでサイトが公開されます:
```
https://YOUR_USERNAME.github.io/youtube-timestamp-scraper/
```

### 4. 初回データ生成

GitHub Actionsが自動実行されますが、手動で初回実行することも可能です:

1. リポジトリの **Actions** タブを開く
2. 左メニューから **Update Timestamp Data** を選択
3. **Run workflow** → **Run workflow** をクリック

### 5. 動作確認

1. Actionsが完了するまで待つ（5-10分程度）
2. 公開URLにアクセス
3. データが表示されることを確認

## ⚙️ 設定のカスタマイズ

### 自動更新頻度の変更

`.github/workflows/update-data.yml` の `cron` 設定を変更:

```yaml
schedule:
  # 毎日 AM 9:00 (JST) に実行
  - cron: '0 0 * * *'

  # 例: 12時間ごとに実行
  - cron: '0 */12 * * *'

  # 例: 月曜・水曜・金曜の9時に実行
  - cron: '0 0 * * 1,3,5'
```

### チャンネルの追加・削除

`user_ids.json` を編集:

```json
{
  "channels": [
    {
      "name": "新しいチャンネル",
      "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
      "enabled": true
    }
  ]
}
```

変更をプッシュすると、次回の自動実行時に反映されます。

## 🎨 デザインのカスタマイズ

フロントエンドファイルを編集:
- `docs/index.html` - HTML構造
- `docs/css/style.css` - スタイル
- `docs/js/app.js` - 機能

変更後、`git push` すれば数分で反映されます。

## 📊 ローカルでのテスト

```bash
# データを生成
python export_to_web.py

# ローカルサーバー起動
cd docs
python -m http.server 8000

# ブラウザで開く
# http://localhost:8000/
```

## ❓ トラブルシューティング

### サイトが表示されない

- GitHub Pagesの設定が正しいか確認
- `docs/` ディレクトリに `index.html` が存在するか確認
- GitHub Actionsのログを確認

### データが更新されない

- GitHub Secretsに `YOUTUBE_API_KEY` が設定されているか確認
- Actionsのログでエラーを確認
- APIクォータ制限を確認

### APIクォータ制限エラー

YouTube Data API v3は1日あたり10,000ユニットの制限があります。
チャンネル数や動画数が多い場合、制限に達することがあります。

対策:
- 更新頻度を減らす（毎日 → 週2回など）
- 複数のAPIキーを使用（推奨しません）

## 📝 参考リンク

- [GitHub Pages ドキュメント](https://docs.github.com/ja/pages)
- [GitHub Actions ドキュメント](https://docs.github.com/ja/actions)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)

## 💡 ヒント

- **独自ドメイン**: GitHub Pagesは独自ドメインにも対応
- **HTTPS**: 自動で有効化されます
- **アクセス解析**: Google Analyticsなどを追加可能
