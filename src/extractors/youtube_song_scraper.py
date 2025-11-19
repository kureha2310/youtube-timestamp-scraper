import json
import os
import re
import csv
import sys
from datetime import datetime, timezone, timedelta
from dataclasses import asdict
from typing import List, Optional

from googleapiclient import discovery
from dotenv import load_dotenv

# Windows環境でのcp932エンコーディングエラーを防ぐための設定
if sys.platform == 'win32':
    # 標準出力をUTF-8に設定（Python 3.7+）
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def safe_print(text):
    """エンコーディングエラーを回避する安全なprint関数"""
    try:
        print(text)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # エンコードできない文字を置き換える
        safe_text = str(text).encode('ascii', 'replace').decode('ascii')
        print(safe_text)

# MeCabのインポート（オプション）
try:
    import MeCab
    mecab_reading = MeCab.Tagger('-Oyomi')
    safe_print("MeCab loaded successfully")
except (ImportError, RuntimeError) as e:
    safe_print(f"MeCab not available: {type(e).__name__}. Using simple hiragana conversion.")
    mecab_reading = None

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.infoclass import VideoInfo, CommentInfo, TimeStamp
from utils.utils import aligned_json_dump
from utils.genre_classifier import GenreClassifier
from utils.music_classifier import MusicClassifier

load_dotenv()
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise RuntimeError("`.env` に API_KEY がありません。YouTube Data API v3 のAPIキーを設定してください。")

youtube = discovery.build('youtube', 'v3', developerKey=API_KEY)

# 入力チャンネルID読み込み
try:
    user_data = json.load(open('user_ids.json', encoding='utf-8'))
    # 新形式（辞書型）か旧形式（配列型）か判定
    if isinstance(user_data, dict):
        users = [ch['channel_id'] for ch in user_data.get('channels', []) if ch.get('enabled', True)]
    else:
        users = user_data  # 旧形式（配列）
except FileNotFoundError:
    safe_print("user_ids.json が見つかりません。サンプルを作成します。")
    users = ["UCxxxxxxxxxxxxxxxxxxxxxx"]
    with open('user_ids.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

class EnhancedAnalyzer:
    def __init__(self):
        # ジャンル分類器を初期化（JSON統合版）
        self.genre_classifier = GenreClassifier()

    def to_hiragana(self, text: str) -> str:
        """テキストをひらがなに変換"""
        if mecab_reading:
            try:
                reading = mecab_reading.parse(text).strip()
                hiragana = ''
                for char in reading:
                    if 'ァ' <= char <= 'ヶ':
                        hiragana += chr(ord(char) - ord('ァ') + ord('ぁ'))
                    elif char == 'ヵ':
                        hiragana += 'か'
                    elif char == 'ヶ':
                        hiragana += 'け'
                    else:
                        hiragana += char.lower()
                return hiragana
            except:
                pass
        
        # MeCabが使えない場合の簡易変換
        return self._simple_katakana_to_hiragana(text.lower())
    
    def _simple_katakana_to_hiragana(self, text: str) -> str:
        """簡易カタカナ→ひらがな変換（英数字・記号も処理）"""
        result = ''
        for char in text:
            if 'ァ' <= char <= 'ヶ':
                result += chr(ord(char) - ord('ァ') + ord('ぁ'))
            elif char == 'ヵ':
                result += 'か'
            elif char == 'ヶ':
                result += 'け'
            elif 'A' <= char <= 'Z':
                result += char.lower()
            elif char in '０１２３４５６７８９':
                # 全角数字を半角に
                result += str(ord(char) - ord('０'))
            elif char in '（）［］｛｝':
                # 全角括弧を除去
                continue
            else:
                result += char
        return result

    def detect_genre(self, title: str, artist: str) -> str:
        """ジャンルを自動判定（JSON統合版）"""
        return self.genre_classifier.classify(artist, title)

    def calculate_confidence_score(self, video_info: VideoInfo, extracted_timestamps: list = None) -> float:
        """
        歌動画の確度スコアを計算（改善版）

        Args:
            video_info: 動画情報
            extracted_timestamps: 抽出されたタイムスタンプのリスト（省略可）

        Returns:
            0.0-1.0の確度スコア
        """
        title = video_info.title
        description = video_info.description

        # 既存のis_singing_stream関数と同じロジック
        combined_text = f"{title} {description}".lower()
        singing_keywords = [
            "歌", "うた", "歌枠", "うたわく", "歌配信", "singing", "sing",
            "カラオケ", "からおけ", "karaoke",
            "音楽", "music", "楽曲", "ソング", "song",
            "メドレー", "medley", "弾き語り",
            "ライブ", "live", "演奏", "performance",
            "アカペラ", "acappella", "コーラス", "chorus",
            "歌ってみた", "うたってみた", "歌リレー", "歌回",
            "リクエスト歌", "歌練習", "新曲", "cover",
            "ボカロ", "vocaloid", "アニソン", "anime song", "anisong",
            "セトリ", "setlist", "リハ", "リハーサル", "rehearsal"
        ]
        exclude_keywords = [
            "ゲーム", "game", "gaming", "プレイ", "play",
            "雑談", "zatsudan", "talk", "おしゃべり", "chat",
            "料理", "cooking", "クッキング", "食べる", "eating",
            "お絵描き", "絵", "drawing", "art", "イラスト",
            "工作", "craft", "作業", "work", "study", "勉強"
        ]

        singing_score = 0
        for keyword in singing_keywords:
            if keyword in combined_text:
                singing_score += 1

        exclude_score = 0
        for keyword in exclude_keywords:
            if keyword in combined_text:
                exclude_score += 1

        # タイトルの重要なパターン（重み増加）
        if re.search(r'[歌うたウタ]', title):
            singing_score += 5  # 3→5に増加（最も信頼できるシグナル）
        if re.search(r'[♪♫♬🎵🎶🎤🎼]', combined_text):
            singing_score += 2

        timestamp_count = len(re.findall(r'\d{1,2}:\d{2}', description))
        if timestamp_count >= 3:
            singing_score += 2

        # コメント分析による追加スコア
        if hasattr(video_info, 'comments') and video_info.comments:
            comment_timestamp_count = 0
            song_format_count = 0

            for comment in video_info.comments:
                comment_text = comment.text_display if hasattr(comment, 'text_display') else str(comment)
                comment_timestamps = len(re.findall(r'\d{1,2}:\d{2}', comment_text))
                if comment_timestamps >= 3:
                    comment_timestamp_count += 1

                # タイムスタンプ + 「曲名 / アーティスト」形式を検出
                # HTMLタグも考慮（YouTubeコメントは<a>タグを含む）
                if re.search(r'\d{1,2}:\d{2}(?::\d{2})?[^/\n]*/.+', comment_text):
                    song_format_count += 1

            # コメントに多数のタイムスタンプがある場合、歌配信の可能性が高い
            if comment_timestamp_count >= 2:
                singing_score += 4
            elif comment_timestamp_count >= 1:
                singing_score += 2

            # 「曲名 / アーティスト」形式のタイムスタンプが複数ある場合、スコア追加
            if song_format_count >= 3:
                singing_score += 6
            elif song_format_count >= 2:
                singing_score += 4
            elif song_format_count >= 1:
                singing_score += 2

        # ★新機能: タイムスタンプの質を評価（最も信頼できる指標）
        timestamp_quality_score = 0
        if extracted_timestamps:
            # アーティスト名がある割合
            artist_count = sum(1 for ts in extracted_timestamps if '/' in ts.text)
            artist_ratio = artist_count / max(1, len(extracted_timestamps))

            if artist_ratio > 0.8:
                timestamp_quality_score += 10  # 80%以上にアーティスト名 = 確実に歌枠
            elif artist_ratio > 0.5:
                timestamp_quality_score += 6
            elif artist_ratio > 0.2:
                timestamp_quality_score += 3

            # タイムスタンプの数（多いほど信頼できる）
            ts_count = len(extracted_timestamps)
            if ts_count >= 20:
                timestamp_quality_score += 4
            elif ts_count >= 10:
                timestamp_quality_score += 3
            elif ts_count >= 5:
                timestamp_quality_score += 2
            elif ts_count >= 3:
                timestamp_quality_score += 1

        # 総合スコア計算
        raw_score = max(0, singing_score + timestamp_quality_score - exclude_score)

        # 動的な正規化（最大スコアを推定）
        # 基本スコア最大: 20点 + タイムスタンプ質: 14点 + コメント: 10点 = 44点
        max_possible_score = 44
        normalized_score = min(1.0, raw_score / max_possible_score)

        return normalized_score

    def clean_title(self, text: str) -> str:
        """先頭ナンバリングを除去"""
        # 全角数字を半角に統一
        text = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        # より包括的なナンバリングパターン（複数回適用して再帰的に除去）
        # "01. 曲名" "1) 曲名" "【1】曲名" "(1) 曲名" など
        # 複数のナンバリングが連続している場合もある（例: "01. 1) 曲名"）
        max_iterations = 3  # 最大3回繰り返す

        for _ in range(max_iterations):
            original = text
            patterns = [
                r"^\s*\d{1,3}[\.\。\)）\]】\-ー・]\s*",  # "01." "01。" "1)" "1】" "1-" "1・" など（全角ピリオドも含む）
                r"^\s*[\(\(【\[]\s*\d{1,3}\s*[\)\)】\]]\s*",  # "(1)" "【1】" "[1]" など
                r"^\s*\d{1,3}\s+",  # "01 " (数字+スペース)
                r"^\s*[第]\d{1,3}[曲話回章]\s*",  # "第1曲" "第1話" など
            ]

            for pattern in patterns:
                text = re.sub(pattern, "", text)

            # 変化がなくなったら終了
            if text == original:
                break

        text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)

        # 先頭の装飾記号を除去（&, ＆, ※, ★, ☆, ■, □, ◆, ◇, ●, ○, ▲, △, ▼, ▽など）
        text = re.sub(r"^\s*[&＆※★☆■□◆◇●○▲△▼▽➤➡→⇒►▶►・]+\s*", "", text)

        return text.strip()

    def is_valid_song_entry(self, title: str, artist: str) -> bool:
        """有効な曲エントリかどうかを判定"""
        # 曲名が空の場合は無効
        if not title or not title.strip():
            return False

        # 数字と記号のみで構成されている場合は無効
        if re.match(r'^[\d\s\.\-\(\)\[\]　]+$', title):
            return False

        # ナンバリングパターンのみ（"01." "1)" など）の場合は無効
        if re.match(r'^\d+[\.\)\-\s]*$', title):
            return False

        # 無効なキーワードパターン（明らかにゴミ）
        invalid_patterns = [
            r'^セトリ$',
            r'^タイムスタンプ$',
            r'^リスト$',
            r'^曲目$',
            r'^\d+曲目$',
            r'^BGM$',
            r'待機',
            r'配信開始',
            r'休憩',
            r'ゲーム',
            r'雑談',
            r'実況',
            r'テスト',
            r'お知らせ',
            r'告知',
            r'^🦉',  # 絵文字で始まる
            r'見えて実は',  # 「単純なように見えて実は...」みたいなの
            # 初配信などのタイムスタンプ（歌ではない）
            r'初配信',
            r'初.*配信',  # 「初歌配信」なども除外
            r'第一声',
            r'自己紹介',
            r'公開',
            r'について',
            r'目標',
            r'今後',
            r'作品',
            r'画伯',
            r'語る',
            r'得意',
        ]

        title_lower = title.lower()
        for pattern in invalid_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return False

        # アーティスト名がある場合はOK
        if artist and artist.strip():
            return True

        # アーティスト名がない場合は、曲名らしさで判定
        # 1. 曲名が短すぎる（2文字以下）場合は無効
        if len(title.strip()) <= 2:
            return False

        # 2. 日本語の曲名らしいパターン（ひらがな・カタカナ・漢字が含まれる）
        if re.search(r'[ぁ-んァ-ヶー一-龯]', title):
            return True

        # 3. 英語の曲名らしいパターン（英字が主体）
        if re.match(r'^[a-zA-Z\s\-\'.!?]+$', title) and len(title.strip()) >= 3:
            return True

        # それ以外のアーティスト名なしエントリは無効
        return False

    def parse_song_title_artist(self, title: str) -> tuple[str, str]:
        """曲名とアーティストを分離"""
        title = self.clean_title(title)

        # 「曲 / 歌手」形式で分割
        parts = re.split(r"\s*/\s*", title, maxsplit=1)
        if len(parts) == 2:
            # 分割後も各部分に対してclean_titleを適用（ナンバリングが曲名側に残っている場合）
            song_title = self.clean_title(parts[0].strip())
            artist = parts[1].strip()
            return song_title, artist
        else:
            return title.strip(), ""

def is_singing_stream(title: str, description: str, comments: Optional[List[str]] = None) -> bool:
    """歌動画判定ロジック（コメント分析強化版）"""
    combined_text = f"{title} {description}".lower()
    singing_keywords = [
        "歌", "うた", "歌枠", "うたわく", "歌配信", "singing", "sing",
        "カラオケ", "からおけ", "karaoke",
        "音楽", "music", "楽曲", "ソング", "song",
        "メドレー", "medley", "弾き語り",
        "ライブ", "live", "演奏", "performance",
        "アカペラ", "acappella", "コーラス", "chorus",
        "歌ってみた", "うたってみた", "歌リレー", "歌回",
        "リクエスト歌", "歌練習", "新曲", "cover",
        "ボカロ", "vocaloid", "アニソン", "anime song", "anisong",
        "セトリ", "setlist", "リハ", "リハーサル", "rehearsal"
    ]
    exclude_keywords = [
        "ゲーム", "game", "gaming", "プレイ", "play",
        "雑談", "zatsudan", "talk", "おしゃべり", "chat",
        "料理", "cooking", "クッキング", "食べる", "eating",
        "お絵描き", "絵", "drawing", "art", "イラスト",
        "工作", "craft", "作業", "work", "study", "勉強"
    ]
    singing_score = 0
    for keyword in singing_keywords:
        if keyword in combined_text:
            singing_score += 1
    exclude_score = 0
    for keyword in exclude_keywords:
        if keyword in combined_text:
            exclude_score += 1
    if re.search(r'[歌うたウタ]', title):
        singing_score += 3
    if re.search(r'[♪♫♬🎵🎶🎤🎼]', combined_text):
        singing_score += 2
    timestamp_count = len(re.findall(r'\d{1,2}:\d{2}', description))
    if timestamp_count >= 3:
        singing_score += 2

    # コメント分析による追加スコア
    if comments:
        comment_timestamp_count = 0
        song_format_count = 0  # 「曲名 / アーティスト」形式のカウント

        for comment in comments:
            comment_timestamps = len(re.findall(r'\d{1,2}:\d{2}', comment))
            if comment_timestamps >= 3:  # 1コメントに3つ以上のタイムスタンプ
                comment_timestamp_count += 1

            # タイムスタンプ + 「曲名 / アーティスト」形式を検出
            # 例: "43:00 蝶々結び / Aimer" や "1:23:45 曲名/歌手"
            # HTMLタグも考慮（YouTubeコメントは<a>タグを含む）
            if re.search(r'\d{1,2}:\d{2}(?::\d{2})?[^/\n]*/.+', comment):
                song_format_count += 1

        # コメントに多数のタイムスタンプがある場合、歌配信の可能性が高い
        if comment_timestamp_count >= 2:
            singing_score += 4
        elif comment_timestamp_count >= 1:
            singing_score += 2

        # 「曲名 / アーティスト」形式のタイムスタンプが複数ある場合、歌配信の可能性が非常に高い
        if song_format_count >= 3:
            singing_score += 6  # 強い信号
        elif song_format_count >= 2:
            singing_score += 4
        elif song_format_count >= 1:
            singing_score += 2

    if singing_score >= 2 and exclude_score <= singing_score:
        return True
    elif singing_score >= 4:
        return True
    else:
        return False

def merge_with_existing_csv(csv_file: str, new_rows: list) -> list:
    """
    既存CSVファイルと新しいデータをマージ（重複除去）

    Args:
        csv_file: 既存CSVファイルパス
        new_rows: 新しいデータ行のリスト

    Returns:
        マージ後のデータ行リスト
    """
    if not os.path.exists(csv_file):
        return new_rows

    try:
        existing_rows = []
        with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # ヘッダーをスキップ
            for row in reader:
                existing_rows.append(row)

        # 重複チェック用のキー (動画ID + タイムスタンプ)
        existing_keys = {(row[7], row[5]) for row in existing_rows}  # (動画ID, タイムスタンプ)
        new_unique_rows = []

        for row in new_rows:
            key = (row[7], row[5])
            if key not in existing_keys:
                new_unique_rows.append(row)
                existing_keys.add(key)

        # 既存データと新データを結合
        merged = existing_rows + new_unique_rows

        # 配信日でソート（古い順）
        merged.sort(key=lambda x: (x[6], x[5]))  # 配信日、タイムスタンプでソート

        # 連番を振り直す
        for i, row in enumerate(merged, 1):
            row[0] = i

        safe_print(f"  既存: {len(existing_rows)}件, 新規: {len(new_unique_rows)}件, 合計: {len(merged)}件")
        return merged

    except Exception as e:
        safe_print(f"  [!] CSVマージでエラー: {e}")
        return new_rows

def get_uploads_playlist_id(channel_id: str) -> str | None:
    """既存関数をそのまま使用"""
    if not channel_id or not channel_id.startswith("UC"):
        return None
    try:
        resp = youtube.channels().list(
            part="contentDetails",
            id=channel_id,
            fields="items/contentDetails/relatedPlaylists/uploads"
        ).execute()
        items = resp.get("items", [])
        if not items:
            return None
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        safe_print(f"チャンネル {channel_id} の uploads プレイリスト取得でエラー: {e}")
        return None

def get_video_info_in_playlist(playlist_id: str, published_after: str = None) -> list[VideoInfo]:
    """
    プレイリストから動画情報を取得（差分更新対応）

    Args:
        playlist_id: プレイリストID
        published_after: この日付以降の動画のみ取得（ISO 8601形式）
    """
    video_info_list: list[VideoInfo] = []
    try:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            fields="nextPageToken,items/snippet(publishedAt,title,description,resourceId/videoId)"
        )

        filter_date = None
        if published_after:
            filter_date = datetime.fromisoformat(published_after.replace("Z", "+00:00"))

        while request:
            response = request.execute()
            items = response.get("items", [])

            should_break = False
            for i in items:
                vi = VideoInfo.from_response_snippet(i["snippet"])
                vid = vi.id

                # 日付フィルタリング（古い動画が出てきたら終了）
                if filter_date:
                    try:
                        video_date = datetime.fromisoformat(vi.published_at.replace("Z", "+00:00"))
                        if video_date < filter_date:
                            safe_print(f"  ✓ {filter_date.strftime('%Y-%m-%d')} より前の動画に到達、処理終了")
                            should_break = True
                            break
                    except Exception as e:
                        safe_print(f"  ! 日付パースエラー: {e}")

                # --- 動画詳細を追加で取得 ---
                try:
                    details = youtube.videos().list(
                        part="liveStreamingDetails,snippet",
                        id=vid,
                        fields="items(snippet/publishedAt,liveStreamingDetails/actualStartTime)"
                    ).execute()

                    if details.get("items"):
                        item = details["items"][0]
                        vi.stream_start = item.get("liveStreamingDetails", {}).get("actualStartTime")
                        if not vi.stream_start:
                            vi.stream_start = item["snippet"]["publishedAt"]

                except Exception as e:
                    safe_print(f"動画 {vid} の詳細取得でエラー: {e}")

                video_info_list.append(vi)

            if should_break:
                break

            request = youtube.playlistItems().list_next(request, response)
    except Exception as e:
        safe_print(f"プレイリスト {playlist_id} の取得でエラー: {e}")
    return video_info_list

def get_comments(video_id: str) -> list[CommentInfo]:
    """既存関数をそのまま使用"""
    comment_list: list[CommentInfo] = []
    comment_field = "snippet(videoId,textDisplay,textOriginal)"
    top_comment_f = f"items/snippet/topLevelComment/{comment_field}"
    replies_f = f"items/replies/comments/{comment_field}"

    try:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            maxResults=100,
            videoId=video_id,
            fields=f"nextPageToken,{top_comment_f},{replies_f}"
        )
        while request:
            response = request.execute()
            for item in response.get("items", []):
                comment_list.extend(CommentInfo.response_item_to_comments(item))
            request = youtube.commentThreads().list_next(request, response)
    except Exception as e:
        safe_print(f"動画 {video_id} のコメント取得でエラー: {e}")

    return comment_list

def scrape_channels(channel_ids: List[str], output_file: str = "output/csv/song_timestamps_complete.csv", filter_singing_only: bool = False, incremental: bool = True):
    """
    指定されたチャンネルIDリストをスクレイプする

    Args:
        channel_ids: スクレイプするチャンネルIDのリスト
        output_file: 出力CSVファイル名（デフォルトはoutput/csv/に保存）
        filter_singing_only: Trueの場合は歌枠のみ、Falseの場合はすべての動画を対象
        incremental: Trueの場合は差分更新、Falseの場合は全件取得
    """
    mode_text = "【歌枠モード】" if filter_singing_only else "【総合モード】"
    update_text = "【差分更新】" if incremental else "【全件取得】"
    safe_print(f"YouTubeタイムスタンプ抽出ツール {mode_text} {update_text}")
    safe_print("=" * 60)
    safe_print(f"対象チャンネル数: {len(channel_ids)}")
    safe_print("")

    analyzer = EnhancedAnalyzer()

    # 前回実行日時を読み込む
    published_after = None
    if incremental:
        try:
            with open('last_scrape.json', 'r', encoding='utf-8') as f:
                last_scrape_data = json.load(f)
                last_run = last_scrape_data.get('last_run')
                if last_run:
                    published_after = last_run
                    safe_print(f"[差分更新] {last_run} 以降の動画を取得します")
                else:
                    safe_print("[差分更新] 初回実行のため全動画を取得します")
        except FileNotFoundError:
            safe_print("[差分更新] last_scrape.json が見つかりません。全動画を取得します")

    # 1. 動画情報取得
    uploads_ids: list[str] = []
    for uc in channel_ids:
        up = get_uploads_playlist_id(uc)
        if up:
            uploads_ids.append(up)
        else:
            safe_print(f"取得失敗: {uc}")

    video_info_list: list[VideoInfo] = []
    for upid in uploads_ids:
        video_info_list += get_video_info_in_playlist(upid, published_after=published_after)

    # 2. フィルタリング
    if filter_singing_only:
        # 歌枠フィルタリング（歌枠のみ）
        filtered_video_list = []
        for vi in video_info_list:
            # 歌枠判定 or 概要欄にタイムスタンプが1つ以上ある場合は通す
            has_timestamp_in_desc = len(re.findall(r'\d{1,2}:\d{2}', vi.description)) >= 1
            # 初配信など特別な動画も通す（コメントにタイムスタンプがある可能性）
            is_debut_or_special = bool(re.search(r'初配信|debut|初.*配信', vi.title, re.IGNORECASE))
            
            if is_singing_stream(vi.title, vi.description) or has_timestamp_in_desc or is_debut_or_special:
                filtered_video_list.append(vi)
        safe_print(f"全動画数: {len(video_info_list)}, 歌枠動画数: {len(filtered_video_list)}")
        safe_print("\n=== 歌枠として検出された動画 ===")
    else:
        # すべての動画を対象
        filtered_video_list = []
        for vi in video_info_list:
            filtered_video_list.append(vi)
        safe_print(f"全動画数: {len(video_info_list)}, 処理対象動画数: {len(filtered_video_list)}")
        safe_print("\n=== 処理対象の動画 ===")
    for i, vi in enumerate(filtered_video_list[:10]):
        try:
            safe_print(f"{i+1}. {vi.title}")
        except UnicodeEncodeError:
            safe_title = vi.title.encode('ascii', 'ignore').decode('ascii')
            safe_print(f"{i+1}. {safe_title} [...]")
    if len(filtered_video_list) > 10:
        safe_print(f"... 他 {len(filtered_video_list) - 10} 件")

    # 3. コメント取得 + 再フィルタリング
    safe_print("\nコメントを取得中...")
    filter_singing_only = False  # すべての動画を対象とする
    secondary_filtered_list = []
    for i, video_info in enumerate(filtered_video_list):
        try:
            safe_print(f"{i+1}/{len(filtered_video_list)}: {video_info.title}")
        except UnicodeEncodeError:
            safe_print(f"{i+1}/{len(filtered_video_list)}: [title with emoji]")
        video_info.comments = get_comments(video_info.id)

        if filter_singing_only:
            # 歌枠フィルタリング：コメント分析で再判定
            comment_texts = [c.text_display for c in video_info.comments] if video_info.comments else []
            if is_singing_stream(video_info.title, video_info.description, comment_texts):
                secondary_filtered_list.append(video_info)
            else:
                safe_print(f"  → コメント分析により除外")
        else:
            # すべての動画を通す
            secondary_filtered_list.append(video_info)

    filtered_video_list = secondary_filtered_list
    if filter_singing_only:
        safe_print(f"\nコメント分析後の歌枠動画数: {len(filtered_video_list)}")
    else:
        safe_print(f"\n処理対象動画数: {len(filtered_video_list)}")

    # 4. タイムスタンプ抽出
    safe_print("\nタイムスタンプを抽出中...")
    all_timestamps = []
    video_timestamps_map = {}  # 動画IDごとのタイムスタンプを保持

    for v in filtered_video_list:
        ts_list = TimeStamp.from_videoinfo(v)
        all_timestamps.extend(ts_list)
        video_timestamps_map[v.id] = ts_list  # 動画ごとに保存

    safe_print(f"抽出されたタイムスタンプ数: {len(all_timestamps)}")

    # 5. CSV形式に変換（重複除去強化版）
    safe_print("\nCSV形式に変換中...")
    rows = []
    seen = {}
    duplicate_groups = {}
    idx = 1

    for entry in all_timestamps:
        video_id = entry.video_id
        raw_title = entry.text
        timestamp = entry.timestamp
        published_at = getattr(entry, 'stream_start', None) or entry.published_at

        confidence = 0.0
        for vi in filtered_video_list:
            if vi.id == video_id:
                # 改善版：動画のタイムスタンプを渡す
                ts_for_video = video_timestamps_map.get(video_id, [])
                confidence = analyzer.calculate_confidence_score(vi, ts_for_video)
                break

        song_title, artist = analyzer.parse_song_title_artist(raw_title)

        if not analyzer.is_valid_song_entry(song_title, artist):
            continue

        time_parts = timestamp.split(':')
        total_seconds = 0
        try:
            if len(time_parts) == 2:
                total_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
            elif len(time_parts) == 3:
                total_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
        except:
            total_seconds = 0

        normalized_key = (
            song_title.lower().strip(),
            artist.lower().strip(),
            video_id,
            total_seconds // 5
        )

        if normalized_key not in duplicate_groups:
            duplicate_groups[normalized_key] = []

        duplicate_groups[normalized_key].append({
            'raw_title': raw_title,
            'song_title': song_title,
            'artist': artist,
            'timestamp': timestamp,
            'total_seconds': total_seconds,
            'video_id': video_id,
            'published_at': published_at,
            'confidence': confidence,
            'has_numbering': bool(re.match(r"^\s*\d+", raw_title))
        })

    # 音楽分類器を初期化
    music_classifier = MusicClassifier(request_delay=3.0)

    safe_print("\n[*] タイムスタンプを分類中...")
    for normalized_key, duplicates in duplicate_groups.items():
        best = max(duplicates, key=lambda x: (
            not x['has_numbering'],
            len(x['song_title']),
            len(x['artist'])
        ))

        # 音楽かどうかを判定し、必要に応じてアーティスト情報を補完
        classification = music_classifier.classify_timestamp(
            best['song_title'],
            best['artist'],
            use_itunes=False  # iTunes API無効化（高速化のため）
        )

        genre = analyzer.detect_genre(classification['title'], classification['artist'])
        search_text = analyzer.to_hiragana(classification['title'])

        try:
            dt = datetime.fromisoformat((best['published_at'] or "").replace("Z", "+00:00"))
            date_str = dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y/%m/%d")
        except Exception:
            date_str = ""

        row_data = [
            idx,
            classification['title'],
            classification['artist'],
            search_text,
            genre,
            best['timestamp'],
            date_str,
            best['video_id'],
            f"{best['confidence']:.2f}",
            best['total_seconds'],
            classification['is_music']  # 音楽かどうかのフラグを追加
        ]
        rows.append(row_data)
        idx += 1

    rows.sort(key=lambda x: (x[6], x[9]))

    # 歌とその他に分類
    singing_rows = []
    other_rows = []

    for i, row in enumerate(rows, 1):
        row[0] = i
        is_music = row.pop()  # is_musicフラグを取り出す
        total_seconds = row.pop()  # total_secondsを削除

        if is_music:
            singing_rows.append(row)
        else:
            other_rows.append(row)

    # 再度連番を振り直す
    for i, row in enumerate(singing_rows, 1):
        row[0] = i
    for i, row in enumerate(other_rows, 1):
        row[0] = i

    # 6. 既存CSVとマージ（差分更新の場合）
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    output_singing = os.path.join(output_dir, "song_timestamps_singing_only.csv")
    output_other = os.path.join(output_dir, "song_timestamps_other.csv")

    if incremental:
        # 既存データを読み込んでマージ
        singing_rows = merge_with_existing_csv(output_singing, singing_rows)
        other_rows = merge_with_existing_csv(output_other, other_rows)
        safe_print(f"\n[差分更新] 既存データとマージしました")

    with open(output_singing, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["No","曲","歌手-ユニット","検索用","ジャンル","タイムスタンプ","配信日","動画ID","確度スコア"])
        writer.writerows(singing_rows)

    with open(output_other, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["No","曲","歌手-ユニット","検索用","ジャンル","タイムスタンプ","配信日","動画ID","確度スコア"])
        writer.writerows(other_rows)

    rows = singing_rows + other_rows  # 統計表示用に結合

    safe_print(f"\n完了！CSVを出力しました:")
    safe_print(f"   - 歌枠: {output_singing} ({len(singing_rows)}件)")
    safe_print(f"   - その他: {output_other} ({len(other_rows)}件)")
    safe_print(f"\n統計:")
    safe_print(f"   - 処理した動画数: {len(filtered_video_list)}")
    safe_print(f"   - 抽出したタイムスタンプ数: {len(all_timestamps)}")
    safe_print(f"   - 最終出力行数: {len(rows)}")

    if rows:
        # 確度スコア統計
        scores = [float(row[8]) for row in rows]
        high_conf = len([s for s in scores if s > 0.7])
        med_conf = len([s for s in scores if 0.4 <= s <= 0.7])
        low_conf = len([s for s in scores if s < 0.4])

        safe_print(f"\n   確度スコア分布:")
        safe_print(f"   - 高確度 (>0.7): {high_conf}件 ({high_conf/len(rows)*100:.1f}%)")
        safe_print(f"   - 中確度 (0.4-0.7): {med_conf}件 ({med_conf/len(rows)*100:.1f}%)")
        safe_print(f"   - 低確度 (<0.4): {low_conf}件 ({low_conf/len(rows)*100:.1f}%)")
        safe_print(f"   - 平均確度: {sum(scores)/len(scores):.2f}")

        # ジャンル別統計
        genre_stats = {}
        for row in rows:
            genre = row[4]  # ジャンル列
            genre_stats[genre] = genre_stats.get(genre, 0) + 1

        safe_print(f"\n   ジャンル別統計:")
        for genre, count in sorted(genre_stats.items(), key=lambda x: x[1], reverse=True):
            safe_print(f"   - {genre}: {count}曲 ({count/len(rows)*100:.1f}%)")

    vi_dict = [asdict(vi) for vi in filtered_video_list]
    aligned_json_dump(vi_dict, "output/json/comment_info.json")
    safe_print(f"\nバックアップJSONも作成: output/json/comment_info.json")

    # 実行日時を保存（次回の差分更新用）
    if incremental:
        now = datetime.now(timezone.utc).isoformat()
        with open('last_scrape.json', 'w', encoding='utf-8') as f:
            json.dump({
                'last_run': now,
                'note': 'このファイルは最後にスクレイプした日時を記録します'
            }, f, ensure_ascii=False, indent=2)
        safe_print(f"\n[差分更新] 次回実行時は {now} 以降の動画を取得します")


def main():
    safe_print("YouTube歌動画タイムスタンプ抽出ツール（統合版）")
    safe_print("=" * 60)

    analyzer = EnhancedAnalyzer()

    # 1. 動画情報取得（既存ロジック）
    uploads_ids: list[str] = []
    for uc in users:
        up = get_uploads_playlist_id(uc)
        if up:
            uploads_ids.append(up)
        else:
            safe_print(f"取得失敗: {uc}")

    video_info_list: list[VideoInfo] = []
    for upid in uploads_ids:
        video_info_list += get_video_info_in_playlist(upid)

    # 2. フィルタリング（すべての動画からタイムスタンプを抽出）
    # 歌枠フィルタリングを無効化し、すべての動画を対象とする
    filtered_video_list = []
    for vi in video_info_list:
        # すべての動画を通す（タイムスタンプがあれば抽出）
        filtered_video_list.append(vi)

    safe_print(f"全動画数: {len(video_info_list)}, 処理対象動画数: {len(filtered_video_list)}")

    safe_print("\n=== 処理対象の動画 ===")
    for i, vi in enumerate(filtered_video_list[:10]):
        try:
            safe_print(f"{i+1}. {vi.title}")
        except UnicodeEncodeError:
            # 絵文字などが含まれる場合はエンコードして表示
            safe_title = vi.title.encode('ascii', 'ignore').decode('ascii')
            safe_print(f"{i+1}. {safe_title} [...]")
    if len(filtered_video_list) > 10:
        safe_print(f"... 他 {len(filtered_video_list) - 10} 件")

    # 3. コメント取得 + 再フィルタリング
    safe_print("\nコメントを取得中...")
    filter_singing_only = False  # すべての動画を対象とする
    secondary_filtered_list = []
    for i, video_info in enumerate(filtered_video_list):
        try:
            safe_print(f"{i+1}/{len(filtered_video_list)}: {video_info.title}")
        except UnicodeEncodeError:
            safe_print(f"{i+1}/{len(filtered_video_list)}: [title with emoji]")
        video_info.comments = get_comments(video_info.id)

        if filter_singing_only:
            # 歌枠フィルタリング：コメント分析で再判定
            comment_texts = [c.text_display for c in video_info.comments] if video_info.comments else []
            if is_singing_stream(video_info.title, video_info.description, comment_texts):
                secondary_filtered_list.append(video_info)
            else:
                safe_print(f"  → コメント分析により除外")
        else:
            # すべての動画を通す
            secondary_filtered_list.append(video_info)

    filtered_video_list = secondary_filtered_list
    if filter_singing_only:
        safe_print(f"\nコメント分析後の歌枠動画数: {len(filtered_video_list)}")
    else:
        safe_print(f"\n処理対象動画数: {len(filtered_video_list)}")

    # 4. タイムスタンプ抽出
    safe_print("\nタイムスタンプを抽出中...")
    all_timestamps = []
    video_timestamps_map = {}  # 動画IDごとのタイムスタンプを保持

    for v in filtered_video_list:
        ts_list = TimeStamp.from_videoinfo(v)
        all_timestamps.extend(ts_list)
        video_timestamps_map[v.id] = ts_list  # 動画ごとに保存

    safe_print(f"抽出されたタイムスタンプ数: {len(all_timestamps)}")

    # 5. CSV形式に変換（重複除去強化版）
    safe_print("\nCSV形式に変換中...")
    rows = []
    seen = {}
    duplicate_groups = {}  # 重複をグループ化
    idx = 1

    # 第1パス: すべてのタイムスタンプをグループ化
    for entry in all_timestamps:
        video_id = entry.video_id
        raw_title = entry.text
        timestamp = entry.timestamp
        published_at = getattr(entry, 'stream_start', None) or entry.published_at

        # 確度スコア計算（該当する動画を見つけて計算）
        confidence = 0.0
        for vi in filtered_video_list:
            if vi.id == video_id:
                # 改善版：動画のタイムスタンプを渡す
                ts_for_video = video_timestamps_map.get(video_id, [])
                confidence = analyzer.calculate_confidence_score(vi, ts_for_video)
                break

        song_title, artist = analyzer.parse_song_title_artist(raw_title)

        # 無効なエントリは除外（歌手なし、ナンバリングのみ、など）
        if not analyzer.is_valid_song_entry(song_title, artist):
            continue

        # タイムスタンプを秒に変換（±5秒以内は同じとみなす）
        time_parts = timestamp.split(':')
        total_seconds = 0
        try:
            if len(time_parts) == 2:  # mm:ss
                total_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
            elif len(time_parts) == 3:  # hh:mm:ss
                total_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
        except:
            total_seconds = 0

        # 正規化キー（曲名とアーティストの類似性、タイムスタンプの近さで判定）
        normalized_key = (
            song_title.lower().strip(),
            artist.lower().strip(),
            video_id,
            total_seconds // 5  # 5秒単位で丸める
        )

        if normalized_key not in duplicate_groups:
            duplicate_groups[normalized_key] = []

        duplicate_groups[normalized_key].append({
            'raw_title': raw_title,
            'song_title': song_title,
            'artist': artist,
            'timestamp': timestamp,
            'total_seconds': total_seconds,
            'video_id': video_id,
            'published_at': published_at,
            'confidence': confidence,
            'has_numbering': bool(re.match(r"^\s*\d+", raw_title))
        })

    # 音楽分類器を初期化
    music_classifier = MusicClassifier(request_delay=3.0)

    safe_print("\n[*] タイムスタンプを分類中...")
    # 第2パス: 各グループから最適なものを選択し、分類
    for normalized_key, duplicates in duplicate_groups.items():
        # 優先順位: ナンバリングなし > 詳細な曲名 > 長い曲名
        best = max(duplicates, key=lambda x: (
            not x['has_numbering'],  # ナンバリングがない方が優先
            len(x['song_title']),     # 曲名が長い方が詳細
            len(x['artist'])          # アーティスト名が長い方が詳細
        ))

        # 音楽かどうかを判定し、必要に応じてアーティスト情報を補完
        classification = music_classifier.classify_timestamp(
            best['song_title'],
            best['artist'],
            use_itunes=True
        )

        # ジャンル判定
        genre = analyzer.detect_genre(classification['title'], classification['artist'])

        # ひらがな変換
        search_text = analyzer.to_hiragana(classification['title'])

        # 日付をJSTへ
        try:
            dt = datetime.fromisoformat((best['published_at'] or "").replace("Z", "+00:00"))
            date_str = dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y/%m/%d")
        except Exception:
            date_str = ""

        rows.append([
            idx,
            classification['title'],
            classification['artist'],
            search_text,
            genre,
            best['timestamp'],
            date_str,
            best['video_id'],
            f"{best['confidence']:.2f}",
            best['total_seconds'],  # ソート用に追加（CSV出力時には除外）
            classification['is_music']  # 音楽かどうかのフラグを追加
        ])
        idx += 1

    # 配信日とタイムスタンプでソート（古い順）
    rows.sort(key=lambda x: (x[6], x[9]))  # 配信日、タイムスタンプ（秒）でソート

    # 歌とその他に分類
    singing_rows = []
    other_rows = []

    for i, row in enumerate(rows, 1):
        row[0] = i
        is_music = row.pop()  # is_musicフラグを取り出す
        total_seconds = row.pop()  # total_secondsを削除

        if is_music:
            singing_rows.append(row)
        else:
            other_rows.append(row)

    # 再度連番を振り直す
    for i, row in enumerate(singing_rows, 1):
        row[0] = i
    for i, row in enumerate(other_rows, 1):
        row[0] = i

    # 6. CSV出力（2つのファイル）
    output_dir = "output/csv"
    os.makedirs(output_dir, exist_ok=True)

    output_singing = os.path.join(output_dir, "song_timestamps_singing_only.csv")
    output_other = os.path.join(output_dir, "song_timestamps_other.csv")

    with open(output_singing, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["No","曲","歌手-ユニット","検索用","ジャンル","タイムスタンプ","配信日","動画ID","確度スコア"])
        writer.writerows(singing_rows)

    with open(output_other, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["No","曲","歌手-ユニット","検索用","ジャンル","タイムスタンプ","配信日","動画ID","確度スコア"])
        writer.writerows(other_rows)

    rows = singing_rows + other_rows  # 統計表示用に結合

    safe_print(f"\n完了！CSVを出力しました:")
    safe_print(f"   - 歌枠: {output_singing} ({len(singing_rows)}件)")
    safe_print(f"   - その他: {output_other} ({len(other_rows)}件)")
    safe_print(f"\n統計:")
    safe_print(f"   - 処理した動画数: {len(filtered_video_list)}")
    safe_print(f"   - 抽出したタイムスタンプ数: {len(all_timestamps)}")
    safe_print(f"   - 最終出力行数: {len(rows)}")

    if rows:
        # 確度スコア統計
        scores = [float(row[8]) for row in rows]
        high_conf = len([s for s in scores if s > 0.7])
        med_conf = len([s for s in scores if 0.4 <= s <= 0.7])
        low_conf = len([s for s in scores if s < 0.4])

        safe_print(f"\n   確度スコア分布:")
        safe_print(f"   - 高確度 (>0.7): {high_conf}件 ({high_conf/len(rows)*100:.1f}%)")
        safe_print(f"   - 中確度 (0.4-0.7): {med_conf}件 ({med_conf/len(rows)*100:.1f}%)")
        safe_print(f"   - 低確度 (<0.4): {low_conf}件 ({low_conf/len(rows)*100:.1f}%)")
        safe_print(f"   - 平均確度: {sum(scores)/len(scores):.2f}")

        # ジャンル別統計
        genre_stats = {}
        for row in rows:
            genre = row[4]  # ジャンル列
            genre_stats[genre] = genre_stats.get(genre, 0) + 1

        safe_print(f"\n   ジャンル別統計:")
        for genre, count in sorted(genre_stats.items(), key=lambda x: x[1], reverse=True):
            safe_print(f"   - {genre}: {count}曲 ({count/len(rows)*100:.1f}%)")

    # JSONファイルも保存（バックアップ用）
    vi_dict = [asdict(vi) for vi in filtered_video_list]
    aligned_json_dump(vi_dict, "output/json/comment_info.json")
    safe_print(f"\nバックアップJSONも作成: output/json/comment_info.json")

if __name__ == "__main__":
    main()