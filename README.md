# YouTube タイムスタンプ抽出ツール

YouTubeの配信動画からタイムスタンプ（曲名・アーティスト・ジャンルなど）を自動抽出してCSV形式で出力するツール

## 🎯 主な機能

- **タイムスタンプ自動抽出**: コメント・概要欄から「曲名 / アーティスト」形式を抽出
- **ジャンル自動分類**: Vocaloid/J-POP/アニメ/その他に自動分類
- **確度スコア**: タイムスタンプの信頼性を0.0-1.0で評価
- **重複除去**: 同じ曲の重複を自動排除
- **統計表示**: 確度スコア分布・ジャンル別統計を表示
- **📍 NEW: 文字列検索**: チャンネル内のコメント・字幕から特定文字列を検索

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

```bash
python main.py
```

メニューから「2. チャンネル選択してスクレイプ」を選択

### 3. 出力確認

- `output/csv/song_timestamps_complete.csv` - メイン出力（CSV形式）
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
├── main.py                  # メインエントリーポイント
├── user_ids.json            # チャンネル設定
├── config.json              # 基本設定
├── .env                     # APIキー（要作成）
│
├── src/
│   ├── extractors/
│   │   ├── youtube_song_scraper.py     # メインロジック（最重要）
│   │   ├── single_video_extractor.py   # 単一動画抽出
│   │   ├── youtube_scraper_enhanced.py # 一括抽出
│   │   ├── transcript_only_scraper.py  # トランスクリプト抽出
│   │   └── bulk_transcript_scraper.py  # 一括トランスクリプト
│   │
│   ├── utils/
│   │   ├── genre_classifier.py  # ジャンル分類
│   │   ├── channel_manager.py   # チャンネル管理
│   │   ├── infoclass.py         # データクラス
│   │   └── utils.py             # ユーティリティ関数
│   │
│   └── analyzers/
│       └── transcript_topic_analyzer.py  # 話題分析
│
├── config/
│   └── genre_keywords.json  # ジャンル分類キーワード辞書
│
├── docs/
│   ├── SYSTEM_SPECIFICATION.md          # 詳細仕様書
│   ├── QUICK_REFERENCE.md               # クイックリファレンス
│   └── confidence_score_improvements.md # 確度スコア改善案
│
├── tools/
│   ├── reclassify_genres.py    # CSV再分類ツール
│   ├── tag_classifier.py       # タグ別分類ツール
│   └── build_tag_reference.py  # タグ参照構築
│
├── legacy/                      # 旧バージョンファイル
│
└── output/                      # 出力ディレクトリ
    ├── csv/
    └── json/
```

## 🔧 高度な使い方

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
