# Claude開発ルール - YouTube Timestamp Scraper

**最終更新**: 2025-12-08
**プロジェクト**: YouTubeの配信動画からタイムスタンプを自動抽出するツール

---

## 🚨 最優先ルール（必ず守ること）

### 1. 既存コードの確認が最優先

**絶対にやること**:
- 新機能追加前に、必ず既存の実装パターンを確認する
- 「自分で考えた新しいパターン」を作らない
- 既存のパターンを完全に踏襲する

**確認すべきファイル**:
```
スクレイピングロジック: src/extractors/youtube_song_scraper.py (1,213行)
データクラス定義: src/utils/infoclass.py (486行)
ジャンル分類: src/utils/genre_classifier.py (299行)
スクリプトパターン: scripts/scrape/scrape_latest.py (47行)
```

### 2. Task tool の積極活用

**いつ使うか**:
- 既存実装を調査する時 → `Explore agent, very thorough`
- 新機能の実装計画を立てる時 → `Plan agent`
- 3つ以上の独立したタスクがある時 → 複数の `General-purpose agent` を並列実行

**使わなくていい時**:
- タイポ修正
- 既知のバグ修正（1箇所のみ）
- コメント追加

### 3. 曖昧な指示には必ず聞き返す

**悪い例（勝手に実装開始）**:
```
ユーザー: 「ジャンル分類を改善して」
Claude: （いきなり実装開始）← これはダメ
```

**良い例（確認してから実装）**:
```
ユーザー: 「ジャンル分類を改善して」
Claude: 「承知しました。効率的に進めるため、いくつか確認させてください：
1. どのジャンルの精度が低いですか？（Vocaloid/J-POP/アニメ/その他）
2. 誤分類の具体例はありますか？
3. genre_keywords.json を編集する方法でよいですか？

確認後、以下の流れで進めます：
- Task tool (Explore agent) で既存の分類ロジック全調査
- 改善案を提示
- 承認後に実装」
```

---

## 📐 アーキテクチャ方針

### フロントエンド
- **技術スタック**: React 19.2 + Vite 7.2 + TypeScript 5.9 + Tailwind CSS 4.1
- **ディレクトリ**: `frontend/src/`
- **ビルド出力**: `docs/` (GitHub Pages用)
- **データ取得**: JSON ファイル直読み（`public/data/*.json`）
- **スタイル**: Tailwind CSS のユーティリティクラス

### バックエンド
- **技術スタック**: Python 3.10+
- **主要ライブラリ**: pandas, requests, google-api-python-client
- **設計思想**:
  - スクレイピング（Extractors） + データ処理（Utils） + スクリプト（Scripts）の3層構造
  - すべてのデータクラスは `src/utils/infoclass.py` で定義
  - ジャンル分類は `src/utils/genre_classifier.py` で一元管理

### データフロー
```
YouTube API → Extractors → DataFrame → CSV → export_to_web.py → JSON → React Frontend
                                   ↓
                              重複除去・ジャンル分類
```

### GitHub Actions
- 毎日 AM 9:00 JST に自動更新
- `update-data.yml` が `youtube_song_scraper.main()` を実行
- 自動コミット → Vercel が自動デプロイ

---

## 📁 既存パターン参照（最重要）

### スクレイピング系

| 機能 | 参照ファイル | 説明 |
|------|------------|------|
| メインスクレイパー | `src/extractors/youtube_song_scraper.py` | 最重要。すべてのスクレイピングロジックの基本 |
| 単体動画抽出 | `src/extractors/single_video_extractor.py` | 1動画だけを処理する場合 |
| テキスト検索 | `src/extractors/text_search_extractor.py` | コメント・字幕から文字列検索 |
| 字幕のみ取得 | `src/extractors/transcript_only_scraper.py` | 字幕データのみ取得 |

### データ処理系

| 機能 | 参照ファイル | 説明 |
|------|------------|------|
| データクラス | `src/utils/infoclass.py` | CommentInfo, VideoInfo, TimeStamp の定義 |
| ジャンル分類 | `src/utils/genre_classifier.py` | アーティスト名/曲名からジャンルを判定 |
| チャンネル管理 | `src/utils/channel_manager.py` | user_ids.json の読み書き |
| Spotify連携 | `src/utils/spotify_classifier.py` | Spotify APIでジャンル取得（オプション） |

### スクリプト系

| 機能 | 参照ファイル | 説明 |
|------|------------|------|
| 差分更新 | `scripts/scrape/scrape_latest.py` | 前回以降の動画のみ取得 |
| 全件取得 | `scripts/scrape/scrape_all_channels.py` | 全チャンネルの全動画を取得 |
| ジャンル再分類 | `scripts/classify/reclassify_genres.py` | 既存CSVのジャンルを再判定 |
| CSV分割 | `scripts/split/split_csv_by_artist.py` | アーティスト別にCSV分割 |

### メインスクリプト

| 機能 | 参照ファイル | 説明 |
|------|------------|------|
| ワンクリック更新 | `update_web.py` | 推奨。差分更新→CSV→JSON変換を自動実行 |
| Web表示更新 | `export_to_web.py` | CSV→JSON変換のみ |
| インタラクティブメニュー | `main.py` | 対話形式で各機能を実行 |

---

## 🎯 コーディング規約

### Python

#### 命名規則
```python
# クラス: PascalCase
class VideoInfo:
    pass

# 関数: snake_case
def scrape_channels():
    pass

# 定数: UPPER_SNAKE_CASE
MAX_COMMENTS_PER_VIDEO = 100

# 変数: snake_case
channel_id = "UCxxxxx"
```

#### ファイル構成
- 1ファイル500行以内を推奨（現状は1,213行のファイルもあるが、リファクタ時は分割する）
- 1関数50行以内を推奨
- docstring は関数の最初に記述（Googleスタイル）

#### import順序
```python
# 1. 標準ライブラリ
import os
import json
from datetime import datetime

# 2. サードパーティライブラリ
import pandas as pd
from googleapiclient.discovery import build

# 3. ローカルモジュール
from src.utils.infoclass import TimeStamp, VideoInfo
from src.utils.genre_classifier import GenreClassifier
```

#### エラーハンドリング
```python
# 既存のパターンを参照: youtube_song_scraper.py:L450-L480
try:
    # API呼び出し
    response = youtube.videos().list(...).execute()
except Exception as e:
    print(f"エラー: {e}")
    continue  # スキップして次へ
```

### TypeScript/React

#### 命名規則
```typescript
// コンポーネント: PascalCase
const TimestampList: React.FC = () => { ... }

// 関数: camelCase
const fetchTimestamps = async () => { ... }

// 定数: UPPER_SNAKE_CASE
const API_BASE_URL = "https://api.example.com"

// 型: PascalCase
type Timestamp = { ... }
```

#### コンポーネント構造
```typescript
// 既存パターン: frontend/src/App.tsx
// 1. import
// 2. 型定義
// 3. コンポーネント定義
// 4. export
```

---

## 🚫 禁止事項

### 絶対にやってはいけないこと

1. **既存のデータ構造を勝手に変更**
   - ❌ CSV列の順序変更
   - ❌ JSON キーの名前変更
   - ❌ データクラスのフィールド削除

2. **設定ファイルを無視**
   - ❌ `config.json` を読まずにハードコード
   - ❌ `user_ids.json` の構造を変更
   - ❌ `genre_keywords.json` を無視して独自ロジック

3. **外部ライブラリの無断追加**
   - ❌ `pip install` を勝手に実行
   - ❌ `requirements.txt` に記載せずに使用

4. **APIキーをコードに埋め込む**
   - ❌ `API_KEY = "xxxxx"` のようなハードコード
   - ✅ 常に `.env` から読み込む

5. **デバッグコードのコミット**
   - ❌ `print("デバッグ用")` を残す
   - ❌ `console.log("test")` を残す
   - ✅ ロギングは必要最小限に

6. **重複コードの作成**
   - ❌ 同じ処理を複数箇所に書く
   - ✅ 既存の関数・クラスを再利用

---

## 🔖 重要な設計判断と理由

### 1. なぜ差分更新を推奨するのか？

**理由**: YouTube Data API v3 のクォータ制限（1日10,000ユニット）

- 全件取得: 1チャンネル約2,000ユニット → 5チャンネルで上限
- 差分更新: 1チャンネル約100ユニット → 100チャンネル可能

**実装**: `last_scrape.json` に前回実行日時を記録し、次回は `publishedAfter` パラメータで絞り込む

### 2. なぜ CSV と JSON の2つの形式で出力するのか？

**理由**:
- CSV: Excel で編集可能、データバックアップ、統計分析
- JSON: Web フロントエンドで直接読み込み、軽量

**実装**: `export_to_web.py` が CSV を読み込んで JSON に変換

### 3. なぜジャンル分類を自動化するのか？

**理由**: 手動分類は時間がかかる（1,000曲で約5時間）

**実装**:
1. `genre_keywords.json` のアーティスト名マッピング
2. Spotify API で自動取得（オプション）
3. キーワードマッチング（"ボカロ", "アニメ" など）

### 4. なぜ確度スコアを算出するのか？

**理由**: すべてのコメントが歌枠とは限らない

**実装**: `calculate_confidence_score()` で以下を考慮
- 動画タイトル・概要欄に歌関連キーワードが含まれるか
- タイムスタンプの数（多いほど信頼度高）
- 除外キーワード（"ゲーム", "雑談" など）

---

## 📝 実装メモ（進行中の機能・決定事項）

### 2025-12-08: プロジェクト改善方針

**背景**:
- AI開発ガイド（ai-collaboration-guide）のベストプラクティスを適用
- 既存コードの保守性向上、AIとの協働効率化

**次回実装予定**:
1. ロギング機構の追加（`logging` モジュール導入）
2. エラーハンドリングの強化
3. テストカバレッジの向上
4. データベース化の検討（SQLite）

**決定事項**:
- 既存の CSV ベースのワークフローは維持（後方互換性）
- フロントエンドは React のまま（Next.js への移行は検討中）

---

## 🔄 標準作業フロー

### パターンA: 新機能追加（例: プレイリスト対応）

```markdown
【Phase 1: 探索】（10分）
Task tool (Explore agent, very thorough) で以下を調査:
- 既存のスクレイピング実装パターン全調査
- プレイリスト関連のコード抽出
- 類似機能の実装例

【Phase 2: 計画】（15分）
Task tool (Plan agent) で以下を立案:
- 変更が必要なファイルリスト
- 実装ステップ（段階的に）
- リスクと対策

【Phase 3: 実装】（並列実行、1時間）
Task 1: バックエンド実装（Sonnet）
  - src/extractors/playlist_extractor.py 作成
  - src/extractors/youtube_song_scraper.py にプレイリスト対応追加

Task 2: フロントエンド実装（Sonnet）
  - frontend/src/components/PlaylistView.tsx 作成

Task 3: テスト実装（Haiku）
  - tests/test_playlist_extractor.py 作成

【Phase 4: 検証】（10分）
- 実際に実行して動作確認
- エッジケースのテスト
```

### パターンB: バグ修正（例: ジャンル誤分類）

```markdown
【Step 1: 原因調査】（5分）
- src/utils/genre_classifier.py を読む
- config/genre_keywords.json を確認
- 誤分類の具体例を特定

【Step 2: 修正実装】（10分）
- genre_keywords.json にマッピング追加
- または classify() メソッドの条件分岐を修正

【Step 3: 再分類実行】（5分）
python scripts/classify/reclassify_genres.py output/csv/song_timestamps_complete.csv

【Step 4: 確認】（5分）
- CSV を開いて修正箇所を確認
```

### パターンC: 複数画面への展開（例: 新コンポーネント追加）

```markdown
【Phase 1: 既存調査】（10分）
Task tool (Explore agent, very thorough) で:
- 既存の共通コンポーネント全調査
- 使用箇所の洗い出し

【Phase 2: 並列実装】（30分）
以下3つを並列実行:
【Task 1】Page A 対応（Sonnet）
【Task 2】Page B 対応（Sonnet）
【Task 3】Page C 対応（Sonnet）

各タスクの指示:
「既存の components/common/Button.tsx のパターンを完全に踏襲すること。
propsの型定義、スタイル、エラーハンドリングをすべて同じにする。」

【Phase 3: 統合確認】（10分）
- npm run build でビルド成功を確認
- 各画面で動作確認
```

---

## 📊 Task Tool 使い分け早見表

| 状況 | 指示の頭に追加 | agent | thoroughness | 具体例 |
|------|---------------|-------|-------------|--------|
| 既存実装を全調査 | Task tool で | Explore | very thorough | 「既存のスクレイピングパターンを全調査」 |
| 新機能の実装計画 | Task tool で | Plan | - | 「プレイリスト対応の実装計画を立案」 |
| 3つ以上の独立タスク | 以下N個を並列実行: | General-purpose × N | - | 「3画面にコンポーネント展開」 |
| 単純1ファイル修正 | そのまま直接指示でOK | - | - | 「タイポ修正」 |

---

## 🛠️ よくある質問（FAQ）

### Q1: 新しいチャンネルを追加するには？

**A**: `user_ids.json` にチャンネル情報を追加

```json
{
  "name": "新しいチャンネル",
  "channel_id": "UCxxxxxxxxxxxxxxxxxxxxx",
  "enabled": true
}
```

その後、`python update_web.py` で自動取得開始

### Q2: ジャンル分類が間違っているときは？

**A**: `config/genre_keywords.json` を編集

```json
{
  "artist_to_genre": {
    "アーティスト名": "正しいジャンル"
  }
}
```

その後、`python scripts/classify/reclassify_genres.py output/csv/song_timestamps_complete.csv`

### Q3: APIクォータ制限に達したら？

**A**: 翌日まで待つ、または以下の対策:
1. 差分更新（`update_web.py`）を使う（クォータ消費が少ない）
2. 対象チャンネルを減らす（`user_ids.json` で `enabled: false`）
3. 別のAPIキーを取得

### Q4: 既存のCSVをリセットしたい

**A**:
```bash
# バックアップ作成
cp output/csv/song_timestamps_complete.csv output/csv/backup_$(date +%Y%m%d).csv

# 削除
rm output/csv/song_timestamps_*.csv

# 全件取得
python scripts/scrape/scrape_all_channels.py
# メニューで「2」（全件取得）を選択
```

### Q5: フロントエンドのビルドが失敗する

**A**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 📈 記録とレビュー

### 指示履歴の記録（推奨）

新しい機能を実装する際は、以下のディレクトリに記録:

```
docs/
├── instructions/
│   └── YYYYMMDD_[topic].md
├── metrics/
│   └── cost.csv
└── explorations/
    └── YYYYMMDD_[探索結果].md
```

**cost.csv フォーマット**:
```csv
日付,タスク名,手法,トークン消費,時間(h),変更ファイル数,コスト($),備考
2025-12-08,プレイリスト対応,Task tool,120000,1.5,8,1.80,Explore+Plan+並列実装
```

### 週次レビュー

毎週末に `docs/metrics/weekly_review.md` を更新:
- 今週の実績（タスク数、時間、トークン消費）
- Keep（継続すること）
- Problem（改善が必要だったこと）
- Try（次回への改善策）

---

## 🎓 まとめ: 3つの黄金ルール

1. **既存を見せる** → ファイルパスを明示して「このパターンを踏襲」
2. **具体的に伝える** → 5W1H（何を、どこに、なぜ、どうやって、いつまでに）
3. **影響範囲を確認** → Task tool (Explore agent) で事前調査

---

**このファイルの更新ルール**:
- 新しい設計判断をしたら「実装メモ」に追記
- 新しいパターンファイルを作ったら「既存パターン参照」に追加
- FAQが増えたら「よくある質問」に追記

**次回レビュー**: 主要機能追加時、または月次
