import json
import os
import re
import csv
import time
from datetime import datetime, timezone, timedelta
from dataclasses import asdict
from typing import List, Optional

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# MeCabのインポート（オプション）
try:
    import MeCab
    mecab_reading = MeCab.Tagger('-Oyomi')
    print("MeCab loaded successfully")
except (ImportError, RuntimeError) as e:
    print(f"MeCab not available: {type(e).__name__}. Using simple hiragana conversion.")
    mecab_reading = None

from infoclass import VideoInfo, CommentInfo, TimeStamp
from utils import aligned_json_dump
from enhanced_extractor import (
    Config, EnhancedTimestampExtractor, 
    EnhancedGenreClassifier, EnhancedSongParser, 
    EnhancedTextCleaner
)

# 設定とAPI初期化
load_dotenv()
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise RuntimeError("`.env` に API_KEY がありません。YouTube Data API v3 のAPIキーを設定してください。")

youtube = discovery.build('youtube', 'v3', developerKey=API_KEY)

# 設定ファイル読み込み
try:
    config = Config('config.json')
    print("設定ファイル config.json を読み込みました")
except FileNotFoundError:
    print("config.json が見つかりません。デフォルト設定で実行します。")
    # デフォルト設定を作成
    config_data = {
        "singing_detection": {
            "include_keywords": ["歌", "うた", "歌枠", "カラオケ", "music", "song"],
            "exclude_keywords": ["ゲーム", "雑談", "料理"],
            "minimum_score": 2,
            "minimum_score_override": 4
        },
        "api": {"max_results_per_request": 50, "max_comments_per_video": 100, "retry_delay": 1.0}
    }
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    config = Config('config.json')

# 拡張機能の初期化
extractor = EnhancedTimestampExtractor(config)
genre_classifier = EnhancedGenreClassifier(config)
song_parser = EnhancedSongParser(config)
text_cleaner = EnhancedTextCleaner(config)

# 入力チャンネルID読み込み
try:
    users = json.load(open('user_ids.json', encoding='utf-8'))
    print(f"{len(users)}個のチャンネルIDを読み込みました")
except FileNotFoundError:
    print("user_ids.json が見つかりません。サンプルを作成します。")
    users = ["UCxxxxxxxxxxxxxxxxxxxxxx"]
    with open('user_ids.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

class EnhancedAnalyzer:
    def __init__(self, config: Config):
        self.config = config
        self.singing_config = config.singing_detection

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
        """ジャンルを自動判定（設定ファイルベース）"""
        return genre_classifier.classify_genre(title, artist)

    def calculate_confidence_score(self, video_info: VideoInfo) -> float:
        """歌動画の確度スコアを計算（設定ファイルベース）"""
        title = video_info.title
        description = video_info.description
        combined_text = f"{title} {description}".lower()
        
        include_keywords = self.singing_config.get('include_keywords', [])
        exclude_keywords = self.singing_config.get('exclude_keywords', [])
        bonus_patterns = self.singing_config.get('bonus_patterns', [])
        
        singing_score = 0
        for keyword in include_keywords:
            if keyword.lower() in combined_text:
                singing_score += 1
        
        exclude_score = 0
        for keyword in exclude_keywords:
            if keyword.lower() in combined_text:
                exclude_score += 1
        
        # ボーナスパターンをチェック
        for pattern in bonus_patterns:
            if re.search(pattern, combined_text):
                singing_score += 3 if pattern == '[歌うたウタ]' else 2
        
        timestamp_count = len(re.findall(r'\d{1,2}:\d{2}', description))
        if timestamp_count >= 3:
            singing_score += 2
        
        # 正規化してスコアを0-1の範囲に
        raw_score = max(0, singing_score - exclude_score)
        return min(1.0, raw_score / 10.0)

    def clean_title(self, text: str) -> str:
        """テキストクリーニング（拡張版）"""
        return text_cleaner.clean_text(text)

    def parse_song_title_artist(self, title: str) -> tuple[str, str]:
        """曲名とアーティストを分離（拡張版）"""
        return song_parser.parse_song_info(title)

def is_singing_stream(title: str, description: str) -> bool:
    """歌動画判定ロジック（設定ファイルベース）"""
    combined_text = f"{title} {description}".lower()
    
    include_keywords = config.singing_detection.get('include_keywords', [])
    exclude_keywords = config.singing_detection.get('exclude_keywords', [])
    bonus_patterns = config.singing_detection.get('bonus_patterns', [])
    min_score = config.singing_detection.get('minimum_score', 2)
    min_score_override = config.singing_detection.get('minimum_score_override', 4)
    
    singing_score = 0
    for keyword in include_keywords:
        if keyword.lower() in combined_text:
            singing_score += 1
    
    exclude_score = 0
    for keyword in exclude_keywords:
        if keyword.lower() in combined_text:
            exclude_score += 1
    
    # ボーナスパターンをチェック
    for pattern in bonus_patterns:
        if re.search(pattern, combined_text):
            singing_score += 3 if pattern == '[歌うたウタ]' else 2
    
    timestamp_count = len(re.findall(r'\d{1,2}:\d{2}', description))
    if timestamp_count >= 3:
        singing_score += 2
    
    if singing_score >= min_score and exclude_score <= singing_score:
        return True
    elif singing_score >= min_score_override:
        return True
    else:
        return False

def get_uploads_playlist_id(channel_id: str, retry_count: int = 3) -> str | None:
    """アップロードプレイリストIDを取得（リトライ機能付き）"""
    if not channel_id or not channel_id.startswith("UC"):
        return None
    
    for attempt in range(retry_count):
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
        except HttpError as e:
            if e.resp.status in [403, 429]:  # Quota exceeded or rate limited
                if attempt < retry_count - 1:
                    wait_time = (2 ** attempt) * config.data.get('api', {}).get('retry_delay', 1.0)
                    print(f"API制限に到達。{wait_time}秒待機中...")
                    time.sleep(wait_time)
                    continue
            print(f"チャンネル {channel_id} の uploads プレイリスト取得でエラー: {e}")
            return None
        except Exception as e:
            print(f"チャンネル {channel_id} の uploads プレイリスト取得でエラー: {e}")
            return None
    return None

def get_video_info_in_playlist(playlist_id: str, max_results: int = None) -> list[VideoInfo]:
    """プレイリストから動画情報を取得"""
    video_info_list: list[VideoInfo] = []
    if max_results is None:
        max_results = config.data.get('api', {}).get('max_results_per_request', 50)
    
    try:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=max_results,
            fields="nextPageToken,items/snippet(publishedAt,title,description,resourceId/videoId)"
        )
        while request:
            response = request.execute()
            items = response.get("items", [])
            for i in items:
                vi = VideoInfo.from_response_snippet(i["snippet"])
                vid = vi.id

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
                    print(f"動画 {vid} の詳細取得でエラー: {e}")

                video_info_list.append(vi)

            request = youtube.playlistItems().list_next(request, response)
    except Exception as e:
        print(f"プレイリスト {playlist_id} の取得でエラー: {e}")
    return video_info_list

def get_comments(video_id: str, max_results: int = None) -> list[CommentInfo]:
    """動画のコメントを取得"""
    comment_list: list[CommentInfo] = []
    if max_results is None:
        max_results = config.data.get('api', {}).get('max_comments_per_video', 100)
    
    comment_field = "snippet(videoId,textDisplay,textOriginal)"
    top_comment_f = f"items/snippet/topLevelComment/{comment_field}"
    replies_f = f"items/replies/comments/{comment_field}"

    try:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            maxResults=max_results,
            videoId=video_id,
            fields=f"nextPageToken,{top_comment_f},{replies_f}"
        )
        while request:
            response = request.execute()
            for item in response.get("items", []):
                comment_list.extend(CommentInfo.response_item_to_comments(item))
            request = youtube.commentThreads().list_next(request, response)
    except Exception as e:
        print(f"動画 {video_id} のコメント取得でエラー: {e}")

    return comment_list

def main():
    print("YouTube歌動画タイムスタンプ抽出ツール（強化版）")
    print("=" * 60)
    
    analyzer = EnhancedAnalyzer(config)
    
    # 1. 動画情報取得
    print("動画情報を取得中...")
    uploads_ids: list[str] = []
    for i, uc in enumerate(users, 1):
        print(f"  {i}/{len(users)}: チャンネル {uc}")
        up = get_uploads_playlist_id(uc)
        if up:
            uploads_ids.append(up)
        else:
            print(f"取得失敗: {uc}")

    video_info_list: list[VideoInfo] = []
    for i, upid in enumerate(uploads_ids, 1):
        print(f"  プレイリスト {i}/{len(uploads_ids)} を処理中...")
        video_info_list += get_video_info_in_playlist(upid)

    # 2. 歌動画フィルタリング
    print("\n歌動画を検出中...")
    filtered_video_list = []
    for vi in video_info_list:
        if is_singing_stream(vi.title, vi.description):
            filtered_video_list.append(vi)

    print(f"全動画数: {len(video_info_list)}, 歌枠動画数: {len(filtered_video_list)}")

    print("\n=== 歌枠として検出された動画 ===")
    for i, vi in enumerate(filtered_video_list[:10]):
        try:
            print(f"{i+1}. {vi.title}")
        except UnicodeEncodeError:
            # エンコーディングエラーが発生した場合は代替表示
            safe_title = vi.title.encode('ascii', 'ignore').decode('ascii')
            print(f"{i+1}. {safe_title} [タイトルに特殊文字を含む]")
    if len(filtered_video_list) > 10:
        print(f"... 他 {len(filtered_video_list) - 10} 件")

    # 3. コメント取得
    print(f"\n{len(filtered_video_list)}件の動画からコメントを取得中...")
    for i, video_info in enumerate(filtered_video_list):
        try:
            print(f"  {i+1}/{len(filtered_video_list)}: {video_info.title[:50]}...")
        except UnicodeEncodeError:
            print(f"  {i+1}/{len(filtered_video_list)}: [特殊文字を含むタイトル]...")
        video_info.comments = get_comments(video_info.id)

    # 4. タイムスタンプ抽出（強化版）
    print("\nタイムスタンプを抽出中（強化版エンジン使用）...")
    all_timestamps = []
    
    for i, v in enumerate(filtered_video_list):
        try:
            print(f"  {i+1}/{len(filtered_video_list)}: {v.title[:50]}...")
        except UnicodeEncodeError:
            print(f"  {i+1}/{len(filtered_video_list)}: [特殊文字を含むタイトル]...")
        
        # 従来の方法も並行して使用
        traditional_ts = TimeStamp.from_videoinfo(v)
        
        # 強化版エンジンでタイムスタンプを抽出
        enhanced_timestamps = []
        
        # 概要欄から抽出
        desc_timestamps = extractor.extract_all_timestamps(v.description)
        for timestamp, content in desc_timestamps:
            enhanced_timestamps.append({
                'video_id': v.id,
                'video_title': v.title,
                'published_at': v.published_at,
                'stream_start': getattr(v, 'stream_start', None),
                'link': f"https://www.youtube.com/watch?v={v.id}&t={timestamp}",
                'timestamp': timestamp,
                'text': content
            })
        
        # コメントから抽出
        for comment in v.comments:
            comment_timestamps = extractor.extract_all_timestamps(comment.text_display)
            for timestamp, content in comment_timestamps:
                enhanced_timestamps.append({
                    'video_id': v.id,
                    'video_title': v.title,
                    'published_at': v.published_at,
                    'stream_start': getattr(v, 'stream_start', None),
                    'link': f"https://www.youtube.com/watch?v={v.id}&t={timestamp}",
                    'timestamp': timestamp,
                    'text': content
                })
        
        # 従来の結果と強化版の結果を統合
        all_traditional = [asdict(ts) for ts in traditional_ts]
        
        # 重複除去しつつマージ
        seen = set()
        for ts_data in all_traditional + enhanced_timestamps:
            key = (ts_data['video_id'], ts_data['timestamp'], ts_data['text'].lower())
            if key not in seen:
                seen.add(key)
                # TimeStampオブジェクトに変換
                ts_obj = TimeStamp(
                    video_id=ts_data['video_id'],
                    video_title=ts_data['video_title'],
                    published_at=ts_data['published_at'],
                    link=ts_data['link'],
                    timestamp=ts_data['timestamp'],
                    text=ts_data['text'],
                    stream_start=ts_data.get('stream_start')
                )
                all_timestamps.append(ts_obj)
    
    print(f"抽出されたタイムスタンプ数: {len(all_timestamps)}")

    # 5. CSV形式に変換
    print("\nCSV形式に変換中...")
    rows = []
    seen = {}
    idx = 1

    for entry in all_timestamps:
        video_id = entry.video_id
        raw_title = entry.text
        timestamp = entry.timestamp
        published_at = getattr(entry, 'stream_start', None) or entry.published_at
        
        # 確度スコア計算（該当する動画を見つけて計算）
        confidence = 0.0
        for vi in filtered_video_list:
            if vi.id == video_id:
                confidence = analyzer.calculate_confidence_score(vi)
                break

        song_title, artist = analyzer.parse_song_title_artist(raw_title)

        # 歌手なしは除外
        if not artist:
            continue

        # 重複判定
        key = (song_title.lower(), artist.lower(), video_id, timestamp)
        if key in seen:
            if re.match(r"^\s*\d+", raw_title):
                continue
        seen[key] = True

        # ジャンル判定
        genre = analyzer.detect_genre(song_title, artist)
        
        # ひらがな変換
        search_text = analyzer.to_hiragana(song_title)

        # 日付をJSTへ
        try:
            dt = datetime.fromisoformat((published_at or "").replace("Z", "+00:00"))
            date_str = dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y/%m/%d")
        except Exception:
            date_str = ""

        rows.append([
            idx,
            song_title,
            artist,
            search_text,  # ひらがな検索用
            genre,
            timestamp,
            date_str,
            video_id,
            f"{confidence:.2f}"  # 確度スコア
        ])
        idx += 1

    # 6. CSV出力
    output_file = "song_timestamps_enhanced.csv"
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["No","曲","歌手-ユニット","検索用","ジャンル","タイムスタンプ","配信日","動画ID","確度スコア"])
        writer.writerows(rows)

    print(f"\n完了！CSVを出力しました: {output_file}")
    print(f"統計:")
    print(f"   - 処理した動画数: {len(filtered_video_list)}")
    print(f"   - 抽出したタイムスタンプ数: {len(all_timestamps)}")
    print(f"   - 最終出力行数: {len(rows)}")
    
    # 確度スコア統計
    if rows:
        scores = [float(row[8]) for row in rows]
        high_conf = len([s for s in scores if s > 0.7])
        med_conf = len([s for s in scores if 0.4 <= s <= 0.7])
        low_conf = len([s for s in scores if s < 0.4])
        
        print(f"   - 高確度 (>0.7): {high_conf}件")
        print(f"   - 中確度 (0.4-0.7): {med_conf}件")  
        print(f"   - 低確度 (<0.4): {low_conf}件")

    # ジャンル統計
    genres = {}
    for row in rows:
        genre = row[4]
        genres[genre] = genres.get(genre, 0) + 1
    
    print(f"\nジャンル別統計:")
    for genre, count in sorted(genres.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {genre}: {count}件")

    # JSONファイルも保存（バックアップ用）
    vi_dict = [asdict(vi) for vi in filtered_video_list]
    aligned_json_dump(vi_dict, "comment_info_enhanced.json")
    print(f"\nバックアップJSONも作成: comment_info_enhanced.json")

if __name__ == "__main__":
    main()