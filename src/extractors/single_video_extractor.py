#!/usr/bin/env python3
"""
単一動画のタイムスタンプ抽出機能
"""

import json
import os
import csv
import time
from datetime import datetime, timezone, timedelta
from dataclasses import asdict
from typing import List, Optional

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.infoclass import VideoInfo, CommentInfo, TimeStamp
from utils.utils import aligned_json_dump
from extractors.enhanced_extractor import (
    Config, EnhancedTimestampExtractor,
    EnhancedGenreClassifier, EnhancedSongParser,
    EnhancedTextCleaner
)
from analyzers.transcript_topic_analyzer import TranscriptTopicAnalyzer

class SingleVideoExtractor:
    def __init__(self):
        """初期化"""
        # 環境設定
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise RuntimeError(".envファイルにAPI_KEYが設定されていません")
        
        # YouTube API初期化
        self.youtube = discovery.build('youtube', 'v3', developerKey=self.api_key)
        
        # 設定ファイル読み込み
        try:
            self.config = Config('config.json')
            print("設定ファイル config.json を読み込みました")
        except FileNotFoundError:
            print("config.json が見つかりません。デフォルト設定で実行します")
            self._create_default_config()
            self.config = Config('config.json')
        
        # 拡張機能の初期化
        self.extractor = EnhancedTimestampExtractor(self.config)
        self.genre_classifier = EnhancedGenreClassifier(self.config)
        self.song_parser = EnhancedSongParser(self.config)
        self.text_cleaner = EnhancedTextCleaner(self.config)
        self.topic_analyzer = TranscriptTopicAnalyzer()
    
    def _create_default_config(self):
        """デフォルト設定ファイルを作成"""
        config_data = {
            "singing_detection": {
                "include_keywords": ["歌", "うた", "歌枠", "カラオケ", "music", "song", "singing"],
                "exclude_keywords": ["ゲーム", "雑談", "料理", "game", "chat"],
                "bonus_patterns": ["[歌うたウタ]", "[歌枠うたわく]"],
                "minimum_score": 2,
                "minimum_score_override": 4
            },
            "timestamp_extraction": {
                "patterns": {
                    "plain_timestamp": r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:：・･]?\s*(.+?)(?=\n|\d{1,2}:\d{2}|$)",
                    "flexible_timestamp": r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[）)]\s*(.+?)(?=\n|$)",
                    "japanese_timestamp": r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[：・]\s*(.+?)(?=\n|$)"
                }
            },
            "text_cleaning": {
                "normalize_chars": {
                    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
                    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
                    "（": "(", "）": ")", "［": "[", "］": "]"
                },
                "numbering_patterns": [
                    r"^\d+\.\s*",
                    r"^\d+\)\s*",
                    r"^\d+[-–—]\s*",
                    r"^第?\d+[曲首]\s*"
                ]
            },
            "genres": {
                "vocaloid": {
                    "artists": ["初音ミク", "鏡音リン", "鏡音レン", "巡音ルカ", "MEIKO", "KAITO", "IA", "GUMI"],
                    "producers": ["ボカロP", "DECO*27", "ハチ", "米津玄師"],
                    "keywords": ["ボカロ", "vocaloid", "ミク", "ボーカロイド"]
                },
                "anime": {
                    "keywords": ["アニメ", "anime", "OP", "ED", "主題歌", "挿入歌"],
                    "titles": ["残酷な天使のテーゼ", "God knows", "only my railgun"]
                },
                "jpop": {
                    "artists": ["YOASOBI", "あいみょん", "米津玄師", "LiSA"],
                    "keywords": ["jpop", "j-pop", "ポップス"]
                }
            },
            "api": {
                "max_results_per_request": 50,
                "max_comments_per_video": 100,
                "retry_delay": 1.0
            }
        }
        
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    def get_video_info(self, video_id: str) -> Optional[VideoInfo]:
        """動画情報を取得"""
        try:
            # 動画の基本情報を取得
            response = self.youtube.videos().list(
                part='snippet,liveStreamingDetails',
                id=video_id,
                fields='items(snippet(publishedAt,title,description),liveStreamingDetails/actualStartTime)'
            ).execute()
            
            items = response.get('items', [])
            if not items:
                print(f"動画が見つかりませんでした: {video_id}")
                return None
            
            item = items[0]
            snippet = item['snippet']
            
            # VideoInfoオブジェクトを作成
            video_info = VideoInfo(
                id=video_id,
                title=snippet['title'],
                description=snippet['description'],
                published_at=snippet['publishedAt'],
                comments=[]  # 空のリストで初期化
            )
            
            # ライブストリーミング情報があれば設定
            live_details = item.get('liveStreamingDetails', {})
            if live_details.get('actualStartTime'):
                video_info.stream_start = live_details['actualStartTime']
            else:
                video_info.stream_start = snippet['publishedAt']
            
            return video_info
            
        except HttpError as e:
            print(f"動画情報の取得でエラー: {e}")
            return None
        except Exception as e:
            print(f"予期しないエラー: {e}")
            return None
    
    def get_comments(self, video_id: str, max_results: int = None) -> List[CommentInfo]:
        """動画のコメントを取得"""
        comment_list: List[CommentInfo] = []
        if max_results is None:
            max_results = self.config.data.get('api', {}).get('max_comments_per_video', 100)
        
        comment_field = "snippet(videoId,textDisplay,textOriginal)"
        top_comment_f = f"items/snippet/topLevelComment/{comment_field}"
        replies_f = f"items/replies/comments/{comment_field}"
        
        try:
            print(f"コメントを取得中... (最大{max_results}件)")
            request = self.youtube.commentThreads().list(
                part="snippet,replies",
                maxResults=min(max_results, 100),  # APIの制限
                videoId=video_id,
                fields=f"nextPageToken,{top_comment_f},{replies_f}"
            )
            
            count = 0
            while request and count < max_results:
                response = request.execute()
                for item in response.get("items", []):
                    comments = CommentInfo.response_item_to_comments(item)
                    comment_list.extend(comments)
                    count += len(comments)
                    
                    if count >= max_results:
                        break
                
                if count >= max_results:
                    break
                    
                request = self.youtube.commentThreads().list_next(request, response)
            
            print(f"{len(comment_list)}件のコメントを取得しました")
            
        except HttpError as e:
            if e.resp.status == 403:
                print("コメントが無効になっているか、アクセスが制限されています")
            else:
                print(f"コメント取得でエラー: {e}")
        except Exception as e:
            print(f"コメント取得で予期しないエラー: {e}")
        
        return comment_list
    
    def extract_timestamps(self, video_info: VideoInfo) -> List[TimeStamp]:
        """タイムスタンプを抽出"""
        all_timestamps = []
        
        print("タイムスタンプを抽出中...")
        
        # 概要欄から抽出
        desc_count = 0
        desc_timestamps = self.extractor.extract_all_timestamps(video_info.description)
        for timestamp, content in desc_timestamps:
            all_timestamps.append(TimeStamp(
                video_id=video_info.id,
                video_title=video_info.title,
                published_at=video_info.published_at,
                stream_start=getattr(video_info, 'stream_start', None),
                link=f"https://www.youtube.com/watch?v={video_info.id}&t={self._timestamp_to_seconds(timestamp)}",
                timestamp=timestamp,
                text=content
            ))
            desc_count += 1
        
        print(f"   概要欄から: {desc_count}件")
        
        # コメントから抽出
        comment_count = 0
        for comment in video_info.comments:
            comment_timestamps = self.extractor.extract_all_timestamps(comment.text_display)
            for timestamp, content in comment_timestamps:
                all_timestamps.append(TimeStamp(
                    video_id=video_info.id,
                    video_title=video_info.title,
                    published_at=video_info.published_at,
                    stream_start=getattr(video_info, 'stream_start', None),
                    link=f"https://www.youtube.com/watch?v={video_info.id}&t={self._timestamp_to_seconds(timestamp)}",
                    timestamp=timestamp,
                    text=content
                ))
                comment_count += 1
        
        print(f"   コメントから: {comment_count}件")
        print(f"合計 {len(all_timestamps)}件のタイムスタンプを抽出しました")
        
        return all_timestamps
    
    def _timestamp_to_seconds(self, timestamp: str) -> int:
        """タイムスタンプ文字列を秒数に変換"""
        parts = timestamp.split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return 0
    
    def calculate_confidence_score(self, video_info: VideoInfo) -> float:
        """歌動画の確度スコアを計算"""
        title = video_info.title
        description = video_info.description
        combined_text = f"{title} {description}".lower()
        
        singing_config = self.config.singing_detection
        include_keywords = singing_config.get('include_keywords', [])
        exclude_keywords = singing_config.get('exclude_keywords', [])
        
        singing_score = 0
        for keyword in include_keywords:
            if keyword.lower() in combined_text:
                singing_score += 1
        
        exclude_score = 0
        for keyword in exclude_keywords:
            if keyword.lower() in combined_text:
                exclude_score += 1
        
        # タイムスタンプの数もスコアに影響
        import re
        timestamp_count = len(re.findall(r'\d{1,2}:\d{2}', description))
        if timestamp_count >= 3:
            singing_score += 2
        
        # 正規化してスコアを0-1の範囲に
        raw_score = max(0, singing_score - exclude_score)
        return min(1.0, raw_score / 10.0)
    
    def save_to_csv(self, timestamps: List[TimeStamp], video_info: VideoInfo, filename: str = None):
        """CSVファイルに保存"""
        if filename is None:
            filename = f"timestamps_{video_info.id}.csv"
        
        print(f"CSV形式で保存中: {filename}")
        
        rows = []
        seen = set()
        idx = 1
        
        confidence = self.calculate_confidence_score(video_info)
        
        for entry in timestamps:
            raw_title = entry.text
            timestamp = entry.timestamp
            published_at = getattr(entry, 'stream_start', None) or entry.published_at
            
            # 楽曲情報の解析
            song_title, artist = self.song_parser.parse_song_info(raw_title)
            
            # アーティストなしは除外（オプション）
            if not artist:
                artist = "不明"  # 代わりに不明として記録
            
            # 重複判定
            key = (song_title.lower(), artist.lower(), timestamp)
            if key in seen:
                continue
            seen.add(key)
            
            # ジャンル判定
            genre = self.genre_classifier.classify_genre(song_title, artist)
            
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
                genre,
                timestamp,
                date_str,
                video_info.id,
                f"{confidence:.2f}",
                entry.link
            ])
            idx += 1
        
        # CSV書き込み
        with open(filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "No", "曲", "歌手・ユニット", "ジャンル", "タイムスタンプ", 
                "配信日", "動画ID", "確度スコア", "リンク"
            ])
            writer.writerows(rows)
        
        print(f"{len(rows)}件をCSVに保存しました")
        
        # 統計表示
        if rows:
            genres = {}
            for row in rows:
                genre = row[3]
                genres[genre] = genres.get(genre, 0) + 1
            
            print(f"\nジャンル別統計:")
            for genre, count in sorted(genres.items(), key=lambda x: x[1], reverse=True):
                print(f"   {genre}: {count}件")
    
    def save_to_json(self, video_info: VideoInfo, filename: str = None):
        """JSONファイルに保存（バックアップ用）"""
        if filename is None:
            filename = f"video_info_{video_info.id}.json"
        
        print(f"JSONバックアップを保存中: {filename}")
        
        video_dict = asdict(video_info)
        aligned_json_dump([video_dict], filename)
        
        print(f"JSONバックアップを保存しました")
    
    def analyze_topics_from_transcript(self, video_id: str, video_info: VideoInfo):
        """字幕から話題を分析"""
        try:
            print("\n字幕から話題を分析中...")
            segments = self.topic_analyzer.analyze_topics(video_id)
            
            if segments:
                print(f"検出された話題セグメント:")
                print("-" * 60)
                for i, segment in enumerate(segments, 1):
                    duration_min = segment.duration / 60
                    print(f"{i:2d}. {segment.start_timestamp}-{segment.end_timestamp} "
                          f"({duration_min:.1f}分) {segment.topic}")
                    if segment.keywords:
                        keywords_str = ", ".join(segment.keywords[:3])  # 最初の3つのキーワード
                        print(f"     キーワード: {keywords_str}")
                
                # CSVに保存
                self.topic_analyzer.save_topics_to_csv(segments, video_id, video_info.title)
                
                return segments
            else:
                print("話題セグメントが検出されませんでした")
                return []
                
        except Exception as e:
            print(f"字幕解析でエラー: {e}")
            return []
    
    def extract_video_timestamps(self, video_id: str, analyze_topics: bool = False):
        """メイン実行関数"""
        print(f"\n動画ID: {video_id}")
        print("="*60)
        
        # 1. 動画情報取得
        print("動画情報を取得中...")
        video_info = self.get_video_info(video_id)
        if not video_info:
            return
        
        print(f"タイトル: {video_info.title}")
        print(f"公開日: {video_info.published_at}")
        
        # 2. コメント取得
        video_info.comments = self.get_comments(video_id)
        
        # 3. タイムスタンプ抽出
        timestamps = self.extract_timestamps(video_info)
        
        if not timestamps:
            print("タイムスタンプが見つかりませんでした")
            return
        
        # 4. 結果表示
        print(f"\n抽出されたタイムスタンプ:")
        print("-" * 60)
        for i, ts in enumerate(timestamps[:10], 1):  # 最初の10件を表示
            song_title, artist = self.song_parser.parse_song_info(ts.text)
            genre = self.genre_classifier.classify_genre(song_title, artist)
            print(f"{i:2d}. {ts.timestamp} - {song_title} / {artist} ({genre})")
        
        if len(timestamps) > 10:
            print(f"    ... 他 {len(timestamps) - 10} 件")
        
        # 5. 保存
        self.save_to_csv(timestamps, video_info)
        self.save_to_json(video_info)
        
        # 6. 字幕から話題分析（オプション）
        topic_segments = []
        if analyze_topics:
            topic_segments = self.analyze_topics_from_transcript(video_id, video_info)
        
        print(f"\n完了しました!")
        print(f"   タイムスタンプ数: {len(timestamps)}件")
        print(f"   確度スコア: {self.calculate_confidence_score(video_info):.2f}")
        if topic_segments:
            print(f"   話題セグメント数: {len(topic_segments)}個")
        
        return {
            'timestamps': timestamps,
            'topic_segments': topic_segments,
            'video_info': video_info
        }

def main():
    """メイン関数（テスト用）"""
    try:
        extractor = SingleVideoExtractor()
        
        # テスト用の動画ID
        video_id = input("動画ID または YouTube URL を入力してください: ").strip()
        
        # URL から動画IDを抽出
        if "youtube.com" in video_id or "youtu.be" in video_id:
            import re
            match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', video_id)
            if match:
                video_id = match.group(1)
            else:
                print("無効なYouTube URLです")
                return
        
        # 話題分析オプション
        analyze_topics = input("字幕から話題も分析しますか？ (y/N): ").strip().lower() == 'y'
        
        extractor.extract_video_timestamps(video_id, analyze_topics=analyze_topics)
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()