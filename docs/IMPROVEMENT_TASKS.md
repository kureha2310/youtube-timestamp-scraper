# 改善タスクリスト - YouTube Timestamp Scraper

**最終更新**: 2025-12-08
**目的**: プロジェクトの保守性・拡張性・パフォーマンスを向上させるための改善項目リスト

---

## 📊 優先度の定義

| 優先度 | 説明 | 目安 |
|--------|------|------|
| 🔴 **高** | 機能・保守性に直接影響。早急に対応すべき | 1-2週間以内 |
| 🟡 **中** | 中長期的な改善効果あり。計画的に対応 | 1-3ヶ月以内 |
| 🟢 **低** | あると便利だが、後回しでも問題ない | 3ヶ月以降 |

---

## 🎯 改善項目サマリー

| カテゴリ | 高 | 中 | 低 | 合計 |
|---------|----|----|----|----|
| コード品質 | 3 | 2 | 1 | 6 |
| 機能 | 2 | 3 | 2 | 7 |
| 運用・保守 | 2 | 2 | 1 | 5 |
| パフォーマンス | 1 | 2 | 1 | 4 |
| セキュリティ | 1 | 1 | 0 | 2 |
| **合計** | **9** | **10** | **5** | **24** |

---

## 🔴 優先度：高（9項目）

### A. コード品質（3項目）

#### A-1: ロギング機構の導入

**現状の問題**:
- `print()` を使った単純なログのみ
- エラーの詳細が記録されない
- トラブルシューティングが困難

**改善案**:
```python
# 現状（youtube_song_scraper.py）
print(f"エラー: {e}")

# 改善後
import logging

logger = logging.getLogger(__name__)
logger.error(f"API呼び出しエラー: {e}", exc_info=True, extra={
    'channel_id': channel_id,
    'video_id': video_id,
    'api_quota_used': quota_used
})
```

**期待効果**:
- エラーの詳細を記録（スタックトレース、コンテキスト情報）
- ログレベルで出力制御（DEBUG/INFO/WARNING/ERROR）
- ファイルへのログ出力でトラブルシューティング効率化

**実装の流れ**:
```markdown
【Phase 1: 調査】（10分）
Task tool (Explore agent, very thorough) で:
- 既存のprint文の使用箇所を全調査
- ログレベルの分類（DEBUG/INFO/WARNING/ERROR）

【Phase 2: 実装】（1時間）
1. src/utils/logger.py を作成
2. 既存のprint文をlogger呼び出しに置き換え
3. config.json にログ設定を追加

【Phase 3: 検証】（10分）
- python update_web.py で動作確認
- ログファイルが正しく出力されるか確認
```

**参考ファイル**:
- 新規作成: `src/utils/logger.py`
- 修正対象: `src/extractors/youtube_song_scraper.py`, `export_to_web.py`, `update_web.py`

---

#### A-2: エラーハンドリングの強化

**現状の問題**:
```python
# youtube_song_scraper.py:L450
try:
    response = youtube.videos().list(...).execute()
except Exception as e:
    print(f"エラー: {e}")
    continue  # スキップするだけ
```

- すべての例外を `Exception` で捕捉（具体的なエラー種別が不明）
- エラー発生時にスキップするだけで、リトライや詳細ログがない
- ネットワークタイムアウト対応が弱い

**改善案**:
```python
import time
from googleapiclient.errors import HttpError

def fetch_video_with_retry(youtube, video_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = youtube.videos().list(
                part="snippet,contentDetails",
                id=video_id
            ).execute()
            return response
        except HttpError as e:
            if e.resp.status in [403, 429]:  # クォータ制限
                logger.error(f"APIクォータ制限: {e}")
                raise  # 再試行しない
            elif e.resp.status in [500, 503]:  # サーバーエラー
                logger.warning(f"API一時エラー (試行{attempt+1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)  # 指数バックオフ
            else:
                raise
        except Exception as e:
            logger.error(f"予期しないエラー: {e}", exc_info=True)
            raise
    raise Exception(f"最大リトライ回数({max_retries})を超えました")
```

**期待効果**:
- ネットワーク一時エラーの自動リトライ
- クォータ制限エラーの適切な処理
- エラー種別ごとの詳細ログ

**実装の流れ**:
```markdown
【Phase 1: 調査】（10分）
Task tool (Explore agent, very thorough) で:
- 既存のtry-except文の使用箇所を全調査
- エラー種別の分類

【Phase 2: 実装】（2時間）
1. src/utils/retry_handler.py を作成
2. API呼び出し箇所にリトライロジックを追加
3. エラー種別ごとの処理を実装

【Phase 3: テスト】（30分）
- 意図的にエラーを発生させてリトライ動作を確認
- クォータ制限時の挙動を確認
```

**参考ファイル**:
- 新規作成: `src/utils/retry_handler.py`
- 修正対象: `src/extractors/youtube_song_scraper.py`, `src/extractors/single_video_extractor.py`

---

#### A-3: 型ヒント（Type Hints）の追加

**現状の問題**:
```python
# src/utils/genre_classifier.py
def classify(self, artist, title):  # 型ヒントなし
    # ...
```

- 関数の引数・戻り値の型が不明確
- IDEの補完が効かない
- バグの早期発見が困難

**改善案**:
```python
from typing import Optional, Dict, List
from src.utils.infoclass import TimeStamp

def classify(self, artist: str, title: str) -> str:
    """ジャンルを分類する

    Args:
        artist: アーティスト名
        title: 曲名

    Returns:
        ジャンル名（Vocaloid/J-POP/アニメ/その他）
    """
    # ...

def scrape_channels(
    youtube,
    channels: List[Dict[str, str]],
    incremental: bool = False
) -> List[TimeStamp]:
    # ...
```

**期待効果**:
- IDEの補完・型チェックが有効化
- バグの早期発見（型の不一致）
- コードの可読性向上

**実装の流れ**:
```markdown
【Phase 1: 実装】（3時間）
以下のファイルに型ヒントを追加:
- src/utils/genre_classifier.py
- src/utils/channel_manager.py
- src/extractors/youtube_song_scraper.py（主要関数のみ）

【Phase 2: 検証】（30分）
- mypy でチェック: mypy src/
- python update_web.py で動作確認
```

**参考ファイル**:
- 修正対象: `src/utils/*.py`, `src/extractors/*.py`

---

### B. 機能（2項目）

#### B-1: ジャンル分類の精度向上

**現状の問題**:
- `genre_keywords.json` の辞書が不完全（約50アーティストのみ）
- Spotify API統合はあるが、活用が限定的
- 誤分類が散見される（例: YOASOBI → Vocaloid）

**改善案**:
1. **genre_keywords.json の拡充**
   - 主要アーティスト500組以上を登録
   - コミュニティ貢献（GitHub Issueでリクエスト受付）

2. **Spotify API統合の強化**
   ```python
   # 現状: spotify_classifier.py はあるが、デフォルトで使われていない

   # 改善後: genre_classifier.py に統合
   def classify(self, artist: str, title: str) -> str:
       # 1. genre_keywords.json で検索
       if artist in self.artist_to_genre:
           return self.artist_to_genre[artist]

       # 2. Spotify API で検索（キャッシュ活用）
       if self.spotify_enabled:
           genre = self.spotify_classifier.get_genre(artist, title)
           if genre:
               return genre

       # 3. キーワードマッチング
       return self._keyword_matching(artist, title)
   ```

3. **機械学習モデルの導入（将来的）**
   - scikit-learn でジャンル分類器を訓練
   - 既存のCSVデータを訓練データとして活用

**期待効果**:
- ジャンル分類精度 **70% → 90%** に向上
- 手動修正の工数削減

**実装の流れ**:
```markdown
【Phase 1: genre_keywords.json の拡充】（2時間）
1. 既存CSVから頻出アーティストを抽出
2. Spotify API で一括取得してジャンル判定
3. genre_keywords.json に追加

【Phase 2: Spotify API統合】（2時間）
1. genre_classifier.py に spotify_classifier を統合
2. キャッシュ機構を実装（config/spotify_cache.json）
3. 動作確認

【Phase 3: 既存データの再分類】（30分）
python scripts/classify/reclassify_genres.py output/csv/song_timestamps_complete.csv
```

**参考ファイル**:
- 修正対象: `src/utils/genre_classifier.py`, `config/genre_keywords.json`
- 参考: `src/utils/spotify_classifier.py`

---

#### B-2: 差分更新の信頼性向上

**現状の問題**:
```json
// last_scrape.json
{
  "last_run": "2025-12-08T03:57:02.850955+00:00"
}
```

- 単純なタイムスタンプのみ
- 途中で失敗した場合の再開機能がない
- キャッシュ不整合時の復旧メカニズムがない

**改善案**:
```json
// last_scrape_enhanced.json
{
  "last_run": "2025-12-08T03:57:02.850955+00:00",
  "channels": {
    "UCHM_SLi7s0AJ8UBmm3pWN6Q": {
      "name": "ふくもつく",
      "last_video_id": "xxxxx",
      "last_video_date": "2025-12-07T10:00:00Z",
      "status": "completed",
      "error": null
    },
    "UCmM2LkAA9WYFZor1k_szNew": {
      "name": "九文字ポルポ",
      "last_video_id": "yyyyy",
      "last_video_date": "2025-12-06T15:00:00Z",
      "status": "failed",
      "error": "API quota exceeded"
    }
  },
  "total_videos_processed": 25,
  "total_timestamps_extracted": 312
}
```

**期待効果**:
- チャンネル単位で進捗管理
- 失敗したチャンネルのみ再実行可能
- トラブルシューティングの効率化

**実装の流れ**:
```markdown
【Phase 1: 実装】（2時間）
1. src/utils/scrape_state_manager.py を作成
2. scrape_channels() に状態管理を統合
3. 既存の last_scrape.json を last_scrape_enhanced.json に移行

【Phase 2: 検証】（30分）
- 意図的にエラーを発生させて再開機能を確認
- python update_web.py で動作確認
```

**参考ファイル**:
- 新規作成: `src/utils/scrape_state_manager.py`
- 修正対象: `src/extractors/youtube_song_scraper.py`, `scripts/scrape/scrape_latest.py`

---

### C. 運用・保守（2項目）

#### C-1: バージョン管理の整理

**現状の問題**:
```
output/csv/
├── song_timestamps_complete.csv
├── song_timestamps_complete_backup_20251201.csv
├── song_timestamps_complete.csv.bak
├── song_timestamps_complete.old
└── ...（10個以上のバックアップファイル）
```

- 複数バージョンの同じファイルが存在
- `legacy/` ディレクトリに旧コードが残存
- クリーンアップが未実施

**改善案**:
1. **自動バックアップの仕組み化**
   ```python
   # update_web.py に追加
   def backup_csv():
       timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
       shutil.copy(
           'output/csv/song_timestamps_complete.csv',
           f'output/csv/backups/song_timestamps_complete_{timestamp}.csv'
       )

       # 30日以前のバックアップを削除
       cleanup_old_backups(days=30)
   ```

2. **legacy/ の整理**
   - 使用していないコードを削除
   - 必要なら `archive/` に移動してREADMEに理由を記載

**期待効果**:
- ディスク容量の削減
- 混乱の防止
- 自動バックアップで安心

**実装の流れ**:
```markdown
【Phase 1: 調査】（30分）
Task tool (Explore agent) で:
- 不要なバックアップファイルを特定
- legacy/ の使用状況を調査

【Phase 2: 実装】（1時間）
1. src/utils/backup_manager.py を作成
2. update_web.py に自動バックアップを統合
3. 不要ファイルを削除

【Phase 3: ドキュメント更新】（15分）
README.md にバックアップの仕組みを記載
```

**参考ファイル**:
- 新規作成: `src/utils/backup_manager.py`
- 修正対象: `update_web.py`

---

#### C-2: 設定ファイルの一貫性確保

**現状の問題**:
- `config/requirements.txt` と `requirements.txt` が2つ存在
- `config.json` と `genre_keywords.json` で重複定義がある
- `.env.example` が古い可能性

**改善案**:
1. **requirements.txt の統一**
   ```bash
   # ルートの requirements.txt を削除
   # config/requirements.txt に統一
   ```

2. **設定ファイルの統合**
   ```json
   // config.json
   {
     "api": { ... },
     "singing_detection": { ... },
     "timestamp_extraction": { ... },
     "genres": {
       "import_from": "config/genre_keywords.json"  // 外部ファイル参照
     }
   }
   ```

3. **.env.example の更新**
   ```bash
   # .env.example
   # YouTube Data API v3 キー（必須）
   API_KEY=your_youtube_api_key_here

   # Spotify API キー（オプション、ジャンル分類の精度向上）
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

   # ログレベル（DEBUG/INFO/WARNING/ERROR）
   LOG_LEVEL=INFO
   ```

**期待効果**:
- 設定の一元管理
- 混乱の防止

**実装の流れ**:
```markdown
【Phase 1: 統合】（1時間）
1. requirements.txt を config/ に統一
2. .env.example を最新化
3. README.md のインストール手順を更新

【Phase 2: 検証】（15分）
- 新規環境でインストール確認
```

---

### D. パフォーマンス（1項目）

#### D-1: データベース化の検討

**現状の問題**:
- CSV ベースのワークフロー（10,000件超で遅延）
- 全件読み込みでメモリ消費が大きい
- クエリ性能が低い（フィルタリング、ソート）

**改善案**:
```python
# SQLite を導入
import sqlite3

# テーブル定義
CREATE TABLE timestamps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_title TEXT NOT NULL,
    artist TEXT,
    genre TEXT,
    timestamp TEXT,
    stream_date DATE,
    video_id TEXT NOT NULL,
    confidence_score REAL,
    channel_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_genre (genre),
    INDEX idx_artist (artist),
    INDEX idx_video_id (video_id)
);
```

**期待効果**:
- クエリ速度 **10倍向上**（10,000件で 5秒 → 0.5秒）
- メモリ消費削減
- 複雑な検索・集計が可能

**実装の流れ**:
```markdown
【Phase 1: 設計】（1時間）
Task tool (Plan agent) で:
- データベーススキーマ設計
- CSV との互換性維持方法
- マイグレーション計画

【Phase 2: 実装】（4時間）
1. src/db/schema.py を作成
2. src/db/repository.py を作成
3. CSV → DB インポート機能を実装
4. 既存コードをDB対応に移行

【Phase 3: 検証】（1時間）
- パフォーマンステスト
- 既存機能の動作確認
```

**参考ファイル**:
- 新規作成: `src/db/schema.py`, `src/db/repository.py`
- 修正対象: `export_to_web.py`, フロントエンド（API化が必要）

**注意**: これは大規模な変更。後方互換性を維持しつつ、段階的に移行する。

---

### E. セキュリティ（1項目）

#### E-1: 入力検証の強化

**現状の問題**:
```python
# channel_manager.py
def add_channel(channel_id: str, name: str):
    # 検証なしでそのまま保存
    channels.append({
        "name": name,
        "channel_id": channel_id,
        "enabled": True
    })
```

- ユーザー入力の検証が限定的
- チャンネルIDのフォーマット検証がない
- XSS対策が不十分（フロントエンド）

**改善案**:
```python
import re

YOUTUBE_CHANNEL_ID_PATTERN = re.compile(r'^UC[\w-]{22}$')

def add_channel(channel_id: str, name: str):
    # チャンネルID検証
    if not YOUTUBE_CHANNEL_ID_PATTERN.match(channel_id):
        raise ValueError(f"無効なチャンネルID: {channel_id}")

    # 名前の検証
    if not name or len(name) > 100:
        raise ValueError(f"無効なチャンネル名: {name}")

    # サニタイズ
    name = name.strip()

    # 重複チェック
    if channel_id in [ch['channel_id'] for ch in channels]:
        raise ValueError(f"チャンネルID {channel_id} は既に登録されています")

    channels.append({
        "name": name,
        "channel_id": channel_id,
        "enabled": True
    })
```

**期待効果**:
- 不正な入力の防止
- データ整合性の向上

**実装の流れ**:
```markdown
【Phase 1: 実装】（2時間）
1. src/utils/validators.py を作成
2. channel_manager.py に検証ロジックを追加
3. フロントエンドにもバリデーションを追加

【Phase 2: テスト】（1時間）
- 不正な入力でエラーが出るか確認
```

**参考ファイル**:
- 新規作成: `src/utils/validators.py`
- 修正対象: `src/utils/channel_manager.py`, `channel_manager_gui.py`, フロントエンド

---

## 🟡 優先度：中（10項目）

### A. コード品質（2項目）

#### A-4: テストカバレッジの向上

**現状の問題**:
- `tests/` に4つの小規模テストのみ（総172行）
- ユニットテストが不十分
- 統合テストが存在しない

**改善案**:
```python
# tests/test_genre_classifier.py
import pytest
from src.utils.genre_classifier import GenreClassifier

class TestGenreClassifier:
    @pytest.fixture
    def classifier(self):
        return GenreClassifier()

    def test_vocaloid_classification(self, classifier):
        assert classifier.classify("初音ミク", "千本桜") == "Vocaloid"

    def test_jpop_classification(self, classifier):
        assert classifier.classify("YOASOBI", "夜に駆ける") == "J-POP"

    def test_unknown_artist(self, classifier):
        assert classifier.classify("Unknown Artist", "Unknown Song") == "その他"
```

**目標カバレッジ**:
- ユニットテスト: 70%以上
- 統合テスト: 主要フロー全カバー

**実装の流れ**:
```markdown
【Phase 1: テスト設計】（2時間）
Task tool (Plan agent) で:
- テスト対象の優先度付け
- テストケースの洗い出し

【Phase 2: 実装】（8時間）
以下のテストを作成:
- tests/test_genre_classifier.py
- tests/test_channel_manager.py
- tests/test_timestamp_extraction.py
- tests/integration/test_scrape_flow.py

【Phase 3: CI/CD統合】（1時間）
.github/workflows/test.yml を作成
```

**参考ファイル**:
- 新規作成: `tests/test_*.py`, `.github/workflows/test.yml`

---

#### A-5: コードの重複排除

**現状の問題**:
- タイムスタンプ抽出ロジックが複数ファイルに分散
- エラーハンドリングのパターンが重複
- 正規表現パターンが複数箇所にハードコード

**改善案**:
```python
# src/utils/patterns.py（新規作成）
class TimestampPatterns:
    PLAIN = r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:：・･]?\s*(.+?)(?=\n|\d{1,2}:\d{2}|$)'
    FLEXIBLE = r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[）)]\s*(.+?)(?=\n|$)'
    JAPANESE = r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[：・]\s*(.+?)(?=\n|$)'

    @classmethod
    def all_patterns(cls):
        return [cls.PLAIN, cls.FLEXIBLE, cls.JAPANESE]
```

**期待効果**:
- 保守性向上（修正箇所が1箇所に）
- コード量削減

**実装の流れ**:
```markdown
【Phase 1: 調査】（1時間）
Task tool (Explore agent, very thorough) で:
- 重複コードの洗い出し

【Phase 2: リファクタリング】（4時間）
1. 共通処理を src/utils/ に集約
2. 各ファイルから共通処理をimport
3. テスト実行で動作確認
```

---

### B. 機能（3項目）

#### B-3: スクレイピングの堅牢性向上

**現状の問題**:
- YouTube の仕様変更への対応が脆弱
- クォータ制限エラーハンドリングが不足
- リトライロジックが簡易的

**改善案**: A-2（エラーハンドリングの強化）と統合

---

#### B-4: Web UI の機能拡張

**現状の機能**:
- タイムスタンプ一覧表示
- フィルタリング（ジャンル、アーティスト、日付）
- ソート

**追加したい機能**:
1. **エクスポート機能**（ユーザー側）
   - フィルタリング結果をCSV/JSONでダウンロード

2. **統計情報の表示**
   - ジャンル別の曲数グラフ
   - 月別の配信数グラフ
   - 人気アーティストランキング

3. **ダークモード完成**
   - 現在は未完成状態

**実装の流れ**:
```markdown
【Phase 1: 計画】（30分）
Task tool (Plan agent) で:
- 機能の優先度付け
- UI/UX設計

【Phase 2: 実装】（8時間）
以下3つを並列実行:
【Task 1】エクスポート機能（Sonnet）
【Task 2】統計情報表示（Sonnet）
【Task 3】ダークモード完成（Haiku）
```

**参考ファイル**:
- 修正対象: `frontend/src/App.tsx`, `frontend/src/components/`

---

#### B-5: プレイリスト対応

**現状**: 単一動画のみ対応

**改善案**:
- YouTubeプレイリストからも一括取得できるようにする

**実装の流れ**: AI_DEVELOPMENT_GUIDE.md の「例1: 新機能追加」を参照

---

### C. 運用・保守（2項目）

#### C-3: ドキュメントの拡充

**現状の問題**:
- README.md に記載されているが存在しないドキュメント:
  - `SYSTEM_SPECIFICATION.md`
  - `QUICK_REFERENCE.md`
  - `TEXT_SEARCH_GUIDE.md`

**改善案**:
1. **SYSTEM_SPECIFICATION.md** - 技術仕様書
2. **QUICK_REFERENCE.md** - 開発者向けクイックリファレンス
3. **TEXT_SEARCH_GUIDE.md** - 文字列検索ツール使い方ガイド
4. **API_DOCUMENTATION.md** - 将来のREST API用

**実装の流れ**:
```markdown
【Phase 1: 作成】（4時間）
以下のドキュメントを作成:
- docs/SYSTEM_SPECIFICATION.md
- docs/QUICK_REFERENCE.md
- docs/TEXT_SEARCH_GUIDE.md
```

---

#### C-4: GitHub Actions の改善

**現状の問題**:
- エラー発生時の通知がない
- 実行履歴が見づらい

**改善案**:
```yaml
# .github/workflows/update-data.yml に追加
- name: Notify on failure
  if: failure()
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: 'Scrape failed on ${{ github.run_id }}',
        body: 'Check the logs: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}'
      })
```

**実装の流れ**:
```markdown
【Phase 1: 実装】（1時間）
1. エラー通知を追加
2. Slack/Discord通知の統合（オプション）

【Phase 2: テスト】（30分）
- 意図的にエラーを発生させて通知を確認
```

---

### D. パフォーマンス（2項目）

#### D-2: スクレイピング速度の最適化

**現状の問題**:
- API呼び出しが順次実行（並列化なし）
- バッチサイズが小さい（50件/リクエスト）

**改善案**:
```python
# 並列処理の導入
from concurrent.futures import ThreadPoolExecutor

def scrape_channels_parallel(youtube, channels, max_workers=3):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(scrape_single_channel, youtube, channel)
            for channel in channels
        ]
        results = [f.result() for f in futures]
    return results
```

**期待効果**:
- スクレイピング時間 **30%削減**（5分 → 3.5分）

**実装の流れ**:
```markdown
【Phase 1: 実装】（2時間）
1. scrape_channels_parallel() を実装
2. クォータ制限を考慮した並列数の調整

【Phase 2: テスト】（30分）
- パフォーマンステスト
- API クォータ消費の確認
```

---

#### D-3: フロントエンドの仮想スクロール導入

**現状の問題**:
- 大量データ（1,000件以上）で動作が重い
- 全データを一度にレンダリング

**改善案**:
```typescript
// react-window を使用
import { FixedSizeList } from 'react-window';

const TimestampList = ({ timestamps }) => {
  return (
    <FixedSizeList
      height={600}
      itemCount={timestamps.length}
      itemSize={80}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <TimestampCard timestamp={timestamps[index]} />
        </div>
      )}
    </FixedSizeList>
  );
};
```

**期待効果**:
- 初期レンダリング時間 **80%削減**（2秒 → 0.4秒）

---

### E. セキュリティ（1項目）

#### E-2: データプライバシーへの対応

**現状の問題**:
- コメント全文をローカル保存
- GDPR 等への対応が不明確

**改善案**:
1. **個人情報の匿名化**
   - ユーザー名を保存しない
   - コメント内容を保存しない（タイムスタンプのみ）

2. **データ削除機能**
   - 特定のチャンネル/動画のデータを削除できる機能

**実装の流れ**:
```markdown
【Phase 1: 調査】（1時間）
- 現在保存しているデータの洗い出し
- 個人情報の特定

【Phase 2: 実装】（2時間）
1. データ保存時に個人情報を除去
2. データ削除機能を実装
```

---

## 🟢 優先度：低（5項目）

### A. コード品質（1項目）

#### A-6: youtube_song_scraper.py のリファクタリング

**現状の問題**:
- 1ファイル1,213行（推奨は500行以内）

**改善案**: AI_DEVELOPMENT_GUIDE.md の「テンプレート3: リファクタリング」を参照

---

### B. 機能（2項目）

#### B-6: 国際化（i18n）対応

**現状**: UI が日本語のみ

**改善案**:
```typescript
// react-i18next を使用
import { useTranslation } from 'react-i18next';

const App = () => {
  const { t } = useTranslation();

  return (
    <h1>{t('app.title')}</h1>
  );
};
```

---

#### B-7: REST API の実装

**現状**: JSON ファイル直読み

**改善案**:
```python
# api/main.py（新規作成）
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/timestamps")
def get_timestamps(genre: str = None, artist: str = None):
    # DB からデータ取得
    pass
```

**期待効果**:
- 外部からのデータアクセスが可能
- リアルタイム更新

**注意**: D-1（データベース化）が前提

---

### C. 運用・保守（1項目）

#### C-5: コミュニティ貢献の仕組み化

**現状**: ジャンル分類の修正は個人で実施

**改善案**:
1. **GitHub Issue テンプレート**
   - 「ジャンル誤分類の報告」
   - 「新アーティスト追加リクエスト」

2. **Pull Request ウェルカム**
   - CONTRIBUTING.md を作成
   - genre_keywords.json への貢献を募る

---

### D. パフォーマンス（1項目）

#### D-4: CDN の活用

**現状**: GitHub Pages でホスティング

**改善案**:
- Cloudflare CDN を統合
- 画像最適化

**期待効果**:
- ページ読み込み速度向上

---

## 📊 実装の進め方

### 推奨順序

1. **Week 1-2: コード品質の基盤整備**
   - A-1: ロギング機構の導入
   - A-2: エラーハンドリングの強化
   - A-3: 型ヒントの追加

2. **Week 3-4: 機能改善**
   - B-1: ジャンル分類の精度向上
   - B-2: 差分更新の信頼性向上

3. **Week 5-6: 運用・保守**
   - C-1: バージョン管理の整理
   - C-2: 設定ファイルの一貫性確保
   - E-1: 入力検証の強化

4. **Week 7-8: テスト・ドキュメント**
   - A-4: テストカバレッジの向上
   - C-3: ドキュメントの拡充

5. **Month 3-: 大規模改善**
   - D-1: データベース化の検討（段階的に）
   - B-4: Web UI の機能拡張

---

## 📝 記録フォーマット

各タスク実施時は、以下のフォーマットで記録:

```markdown
# [タスクID] - 指示履歴

## 📋 基本情報
- **日時**: YYYY-MM-DD HH:MM - HH:MM
- **タスクID**: A-1（ロギング機構の導入）
- **優先度**: 🔴 高

## 🎯 目標
（このタスクのゴール）

## 📊 定量目標
- 所要時間: 2時間以内
- トークン消費: 80K以内
- 変更ファイル数: 約5ファイル

## 🔄 作業フロー
（AI_DEVELOPMENT_GUIDE.md のテンプレート使用）

## 📊 実績
- 実際の時間: X時間
- トークン消費: XXK
- 変更ファイル数: Xファイル

## 💡 学び
- Keep: （継続すること）
- Problem: （改善が必要だったこと）
- Try: （次回への改善策）
```

---

## 🎓 まとめ

このプロジェクトには **24個の改善項目** があります。

**優先順位**:
1. 🔴 **高（9項目）**: 1-2ヶ月で完了を目指す
2. 🟡 **中（10項目）**: 3ヶ月以内に完了を目指す
3. 🟢 **低（5項目）**: 半年以降、必要に応じて実施

**記録を忘れずに**:
- `docs/metrics/cost.csv` にトークン消費を記録
- `docs/instructions/YYYYMMDD_[topic].md` に指示履歴を記録
- `docs/metrics/weekly_review.md` を毎週更新

---

**このファイルの更新ルール**:
- 新しいタスクが発生したら追加
- タスク完了したら「✅ 完了」マークを付ける
- 定期的に優先度を見直す

**次回レビュー**: 月次