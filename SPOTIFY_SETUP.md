# Spotify API セットアップガイド

Spotify APIを使った自動ジャンル判定機能を使うための設定方法です。

## 1. Spotify Developer アカウント作成

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) にアクセス
2. Spotifyアカウントでログイン（なければ無料で作成）
3. 利用規約に同意

## 2. アプリケーション作成

1. Dashboard で「Create app」をクリック
2. 以下の情報を入力:
   - **App name**: `YouTube Timestamp Scraper`（任意の名前）
   - **App description**: `Genre classification for YouTube timestamps`
   - **Redirect URI**: `http://localhost:8888/callback`（今回は使わないが必須）
   - **APIs used**: `Web API` にチェック
3. 「Save」をクリック
4. 作成されたアプリをクリック
5. 「Settings」をクリック

## 3. 認証情報の取得

1. Settings画面で以下の情報をコピー:
   - **Client ID**: `abcdef123456...`
   - **Client Secret**: 「View client secret」をクリックして表示

⚠️ **重要**: Client Secretは秘密情報です。公開リポジトリにコミットしないでください！

## 4. 環境変数の設定

### Windows (PowerShell)

```powershell
# 一時的に設定（現在のセッションのみ有効）
$env:SPOTIFY_CLIENT_ID="あなたのClient ID"
$env:SPOTIFY_CLIENT_SECRET="あなたのClient Secret"

# 確認
echo $env:SPOTIFY_CLIENT_ID
```

### Windows (コマンドプロンプト)

```cmd
# 一時的に設定
set SPOTIFY_CLIENT_ID=あなたのClient ID
set SPOTIFY_CLIENT_SECRET=あなたのClient Secret

# 確認
echo %SPOTIFY_CLIENT_ID%
```

### Linux / Mac

```bash
# 一時的に設定
export SPOTIFY_CLIENT_ID="あなたのClient ID"
export SPOTIFY_CLIENT_SECRET="あなたのClient Secret"

# 確認
echo $SPOTIFY_CLIENT_ID

# 永続的に設定したい場合は ~/.bashrc または ~/.zshrc に追加
echo 'export SPOTIFY_CLIENT_ID="あなたのClient ID"' >> ~/.bashrc
echo 'export SPOTIFY_CLIENT_SECRET="あなたのClient Secret"' >> ~/.bashrc
source ~/.bashrc
```

## 5. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

または個別にインストール:

```bash
pip install spotipy pandas
```

## 6. 動作確認

### テスト実行

```bash
python src/utils/spotify_classifier.py
```

成功すると以下のような出力が表示されます:

```
✓ Spotify API接続成功

Spotify API テスト
============================================================
YOASOBI / 夜に駆ける
  → J-POP

米津玄師 / Lemon
  → J-POP

Official髭男dism / Pretender
  → J-POP

King Gnu / 白日
  → ロック

SHISHAMO / 明日も
  → ロック

キャッシュ統計
============================================================
キャッシュ件数: 5
  見つかった: 5
  見つからなかった: 0
```

### エラーが出る場合

**「警告: SPOTIFY_CLIENT_ID と SPOTIFY_CLIENT_SECRET を環境変数に設定してください」**
→ 環境変数が正しく設定されていません。上記の手順を再確認してください

**「spotipy がインストールされていません」**
→ `pip install spotipy` を実行してください

## 7. 自動ジャンル判定の実行

### ドライラン（変更を保存せず結果のみ確認）

```bash
python auto_classify_genres.py --dry-run
```

### 実際に実行（「その他」を再分類）

```bash
python auto_classify_genres.py
```

### すべてのCSVファイルを処理

```bash
python auto_classify_genres.py --all
```

### オプション

- `--input <ファイル>`: 入力CSVファイルを指定
- `--output <ファイル>`: 出力CSVファイルを指定（指定しない場合は上書き）
- `--target <ジャンル>`: 再分類対象のジャンル（デフォルト: その他）
- `--dry-run`: ドライラン（実際には保存しない）
- `--all`: すべてのCSVファイルを処理

## 8. キャッシュについて

判定結果は `config/spotify_cache.json` に自動的にキャッシュされます。

- 一度判定した楽曲は次回以降、APIを呼び出さずにキャッシュから取得
- APIレート制限の回避に役立ちます
- キャッシュをクリアしたい場合は `config/spotify_cache.json` を削除

## API制限について

Spotify APIの無料枠:
- **1時間あたり**: 制限なし
- **1日あたり**: 制限なし
- **レート制限**: あり（スクリプトで0.1秒の待機時間を設定済み）

通常の使用では制限に引っかかることはありません。

## トラブルシューティング

### 「429 Too Many Requests」エラー

レート制限に引っかかった場合は、しばらく待ってから再実行してください。
スクリプトは自動的に0.1秒ずつ待機するようになっています。

### 「アーティストが見つかりません」

- マイナーなアーティストはSpotifyに登録されていない可能性があります
- 表記ゆれ（全角/半角、スペースなど）が原因の場合もあります
- その場合は既存のキーワードベース分類器がフォールバックとして動作します

### キャッシュが保存されない

- `config/` ディレクトリが存在するか確認してください
- 書き込み権限があるか確認してください

## セキュリティ注意事項

⚠️ **絶対に以下のファイルをGitにコミットしないでください:**
- `.env` ファイル（認証情報を含む場合）
- `config/spotify_cache.json`（個人の検索履歴）

`.gitignore` に追加することをお勧めします:

```gitignore
# Spotify API
.env
config/spotify_cache.json
```
