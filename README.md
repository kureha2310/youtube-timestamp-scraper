# YouTube タイムスタンプ抽出ツール

YouTubeの配信動画からタイムスタンプ（曲名・アーティスト・ジャンルなど）を自動抽出してCSV形式で出力するツール

## 🎯 主な機能

- **タイムスタンプ自動抽出**: コメント・概要欄から「曲名 / アーティスト」形式を抽出
- **ジャンル自動分類**: Vocaloid/J-POP/アニメ/その他に自動分類
- **確度スコア**: タイムスタンプの信頼性を0.0-1.0で評価
- **重複除去**: 同じ曲の重複を自動排除
- **統計表示**: 確度スコア分布・ジャンル別統計を表示
- **🚀 NEW: 差分更新**: 前回以降の最新動画のみを高速取得
- **🎨 NEW: ワンクリック更新**: Web表示を自動更新（CSV→JSON変換）
- **📍 文字列検索**: チャンネル内のコメント・字幕から特定文字列を検索

## 📦 インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-username/youtube-timestamp-scraper.git
cd youtube-timestamp-scraper

# 仮想環境を作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt

# YouTube Data API v3のAPIキーを設定
echo "API_KEY=your_api_key_here" > .env
```

## 🚀 使い方

### 1. チャンネルIDを設定

`user_ids.json` にスクレイプ対象のチャンネルIDを追加：

```json
{
  "channels": [
    {
      "name": "チャンネル名",
      "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
      "enabled": true
    }
  ]
}
```

### 2. スクレイプ実行

#### 🚀 推奨: ワンクリック更新（最速）

```bash
# Windows
update_web.bat

# Mac/Linux
./update_web.sh

# または直接実行
python update_web.py
```

このコマンドで以下を自動実行：
1. 最新動画のタイムスタンプ取得（差分更新）
2. CSV生成
3. Web表示用JSON生成

#### 従来の方法

```bash
# 差分更新（最新動画のみ・高速）
python scrape_latest.py

# または全件取得（初回・完全リセット時）
python scrape_all_channels.py
```

### 3. 出力確認

- `output/csv/song_timestamps_singing_only.csv` - 歌枠のみ（CSV形式）
- `output/csv/song_timestamps_other.csv` - その他（CSV形式）
- `docs/data/timestamps_singing.json` - Web表示用（JSON形式）
- `output/json/comment_info.json` - バックアップ（JSON形式）

## 📊 出力形式

### CSV出力例

```csv
No,曲,歌手-ユニット,検索用,ジャンル,タイムスタンプ,配信日,動画ID,確度スコア
1,夜に駆ける,YOASOBI,夜に駆ける,J-POP,00:25:36,2025/02/04,N9dsnKVpRwA,0.60
2,ヒバナ,DECO*27,ひばな,Vocaloid,5:21,2025/05/28,RY-Htvm-zpY,1.0
```

**列の説明:**
- **No**: 通し番号
- **曲**: 曲名
- **歌手-ユニット**: アーティスト名
- **検索用**: ひらがな変換した曲名
- **ジャンル**: Vocaloid/J-POP/アニメ/その他
- **タイムスタンプ**: mm:ss または hh:mm:ss
- **配信日**: 配信日（JST）
- **動画ID**: YouTube動画ID
- **確度スコア**: 歌配信の信頼度（0.0-1.0）

## 📂 プロジェクト構造

```
youtube-timestamp-scraper/
├── 🚀 メインスクリプト
│   ├── main.py                  # メインエントリーポイント
│   ├── update_web.py            # Web更新（推奨・日常使用）
│   ├── update_vercel.py         # Vercel更新（フロントビルド含む）
│   ├── export_to_web.py         # CSV→JSON変換
│   ├── search_text.py           # 文字列検索ツール
│   └── channel_manager_gui.py   # GUIチャンネル管理
│
├── 📁 scripts/                  # その他スクリプト
│   ├── scrape/                  # スクレイピング系
│   │   ├── scrape_all_channels.py
│   │   ├── scrape_latest.py
│   │   ├── scrape_all_dual_mode.py
│   │   └── scrape_mitsu.py
│   ├── classify/                # 分類・整理系
│   │   ├── auto_classify_genres.py
│   │   ├── reclassify_genres.py
│   │   └── reclassify_non_songs.py
│   ├── split/                   # データ分割系
│   │   ├── split_csv_by_artist.py
│   │   └── split_csv_other.py
│   └── utils/                   # ユーティリティ系
│       ├── get_channel_names.py
│       ├── check_channel_counts.py
│       ├── check_unknown_channel.py
│       └── merge_csv_data.py
│
├── 📚 src/                      # コアライブラリ
│   ├── extractors/
│   │   ├── youtube_song_scraper.py     # メインロジック（最重要）
│   │   ├── single_video_extractor.py
│   │   ├── youtube_scraper_enhanced.py
│   │   ├── transcript_only_scraper.py
│   │   └── bulk_transcript_scraper.py
│   ├── utils/
│   │   ├── genre_classifier.py
│   │   ├── channel_manager.py
│   │   ├── infoclass.py
│   │   └── utils.py
│   └── analyzers/
│       └── transcript_topic_analyzer.py
│
├── ⚙️ config/
│   ├── genre_keywords.json      # ジャンル分類キーワード辞書
│   ├── config.json              # 基本設定
│   └── .env                     # APIキー（要作成）
│
├── 📖 docs/                     # ドキュメント
│   ├── SETUP_GUIDE.md
│   ├── SEARCH_EXAMPLE.md
│   ├── SPOTIFY_SETUP.md
│   └── [その他ドキュメント]
│
├── 🌐 frontend/                 # Webフロントエンド
│   └── [Vite + React]
│
├── 🔧 tools/                    # ツール類
├── 📦 legacy/                   # 旧バージョンファイル
├── 🧪 tests/                    # テスト
└── 📊 output/                   # 出力ディレクトリ
    ├── csv/
    └── json/
```

## 🔧 高度な使い方

### 🤖 GitHub Actionsで自動更新

リポジトリに以下のSecretsを設定すると、毎日自動更新されます:

1. GitHubリポジトリの Settings > Secrets > Actions で `YOUTUBE_API_KEY` を追加
2. `.github/workflows/update-timestamps.yml` が毎日午前9時（JST）に実行
3. 自動的にコミット・プッシュされます

**手動実行:**
1. GitHubリポジトリの "Actions" タブを開く
2. "Auto Update Timestamps" を選択
3. "Run workflow" をクリック

### 差分更新 vs 全件取得

| モード | 実行コマンド | 速度 | 用途 |
|--------|------------|------|------|
| 🚀 差分更新 | `update_web.py` / `scrape_latest.py` | 超高速 | 日常的な更新 |
| 🔄 全件取得 | `scrape_all_channels.py` → 「2」選択 | 低速 | 初回・完全リセット |

**仕組み:**
- `last_scrape.json` に前回実行日時を記録
- 次回は前回以降の動画のみを取得
- 既存CSVに自動マージ（重複除去）

### ジャンル分類のカスタマイズ

`config/genre_keywords.json` を編集してアーティストやキーワードを追加：

```json
{
  "artist_to_genre": {
    "新しいアーティスト": "J-POP"
  }
}
```

### CSVの再分類

```bash
python tools/reclassify_genres.py output/csv/song_timestamps_complete.csv
```

### 📍 文字列検索ツール（NEW）

チャンネル内のコメント・字幕から特定の文字列を検索:

```bash
python search_text.py
```

対話形式で以下を入力:
1. チャンネルID
2. 検索する文字列
3. 検索対象（コメント・字幕・両方）
4. 検索する動画数

**コマンドライン引数でも実行可能:**

```bash
python search_text.py UCxxxxxx "検索文字列" --all --max-videos 100
```

詳細は [TEXT_SEARCH_GUIDE.md](docs/TEXT_SEARCH_GUIDE.md) を参照

## 📖 ドキュメント

- **[SYSTEM_SPECIFICATION.md](docs/SYSTEM_SPECIFICATION.md)** - 詳細な技術仕様
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - 開発者向けクイックリファレンス
- **[TEXT_SEARCH_GUIDE.md](docs/TEXT_SEARCH_GUIDE.md)** - 文字列検索ツール使い方ガイド

## ⚠️ 注意事項

- YouTube Data API v3の日次クォータ制限に注意
- 大量のチャンネルを一度にスクレイプすると制限に達する可能性あり
- APIキーは`.env`ファイルに保存（.gitignoreに追加済み）

## 📝 ライセンス

MIT License

## 🙏 謝辞

このプロジェクトはYouTubeの歌配信文化を記録・分析するために作成されました。
