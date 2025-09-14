import json
import re
import os
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import csv

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    TRANSCRIPT_AVAILABLE = True
except ImportError:
    print("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
    TRANSCRIPT_AVAILABLE = False

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    print("google-api-python-client not installed. Run: pip install google-api-python-client")
    YOUTUBE_API_AVAILABLE = False

from enhanced_extractor import Config, EnhancedGenreClassifier, EnhancedSongParser, EnhancedTextCleaner

class VideoContentScraper:
    def __init__(self, config: Config, api_key: str = None):
        self.config = config
        self.api_key = api_key
        self.genre_classifier = EnhancedGenreClassifier(config)
        self.song_parser = EnhancedSongParser(config)
        self.text_cleaner = EnhancedTextCleaner(config)
        
        if api_key and YOUTUBE_API_AVAILABLE:
            self.youtube = build('youtube', 'v3', developerKey=api_key)
        else:
            self.youtube = None
    
    def extract_from_description(self, video_id: str) -> List[Tuple[str, str, str]]:
        """動画説明文からセトリ情報を抽出"""
        if not self.youtube:
            return []
        
        try:
            response = self.youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()
            
            if not response['items']:
                return []
            
            description = response['items'][0]['snippet']['description']
            return self._parse_setlist_from_text(description)
        
        except Exception as e:
            print(f"Description extraction error for {video_id}: {e}")
            return []
    
    def extract_from_chapters(self, video_id: str) -> List[Tuple[str, str, str]]:
        """YouTubeチャプターから楽曲情報を抽出"""
        if not self.youtube:
            return []
        
        try:
            response = self.youtube.videos().list(
                part='contentDetails',
                id=video_id
            ).execute()
            
            # チャプター情報は直接APIでは取得できないため、
            # 説明文からチャプター形式の情報を抽出
            return self.extract_from_description(video_id)
        
        except Exception as e:
            print(f"Chapter extraction error for {video_id}: {e}")
            return []
    
    def extract_from_transcript(self, video_id: str) -> List[Tuple[str, str, str]]:
        """字幕・キャプションから楽曲情報を推測"""
        if not TRANSCRIPT_AVAILABLE:
            return []
        
        try:
            # 日本語字幕を優先、なければ自動生成を取得
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            transcript = None
            # 日本語字幕を探す
            try:
                transcript = transcript_list.find_transcript(['ja'])
            except:
                # 日本語がなければ自動生成を探す
                try:
                    transcript = transcript_list.find_generated_transcript(['ja'])
                except:
                    # それでもなければ利用可能な最初の字幕を使用
                    for t in transcript_list:
                        transcript = t
                        break
            
            if not transcript:
                return []
            
            # 字幕データを取得
            transcript_data = transcript.fetch()
            
            # 字幕から楽曲情報を抽出
            return self._extract_songs_from_transcript(transcript_data)
        
        except Exception as e:
            print(f"Transcript extraction error for {video_id}: {e}")
            return []
    
    def _parse_setlist_from_text(self, text: str) -> List[Tuple[str, str, str]]:
        """テキストからセトリ情報を抽出"""
        results = []
        
        # 改行で分割して処理
        lines = text.split('\n')
        
        # タイムスタンプ付きの楽曲情報を探す
        timestamp_patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-:：・]*\s*(.+)',
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)',
            r'【(\d{1,2}:\d{2}(?::\d{2})?)】\s*(.+)',
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    timestamp = match.group(1)
                    song_info = self.text_cleaner.clean_text(match.group(2))
                    
                    if self._is_likely_song(song_info):
                        song_title, artist = self.song_parser.parse_song_info(song_info)
                        genre = self.genre_classifier.classify_genre(song_title, artist)
                        results.append((timestamp, song_title, artist))
        
        return results
    
    def _extract_songs_from_transcript(self, transcript_data: List[Dict]) -> List[Tuple[str, str, str]]:
        """字幕データから楽曲情報を推測"""
        results = []
        
        # 字幕から楽曲タイトルらしいものを抽出
        for entry in transcript_data:
            text = entry.get('text', '')
            timestamp_sec = entry.get('start', 0)
            
            # 秒数をタイムスタンプ形式に変換
            timestamp = self._seconds_to_timestamp(timestamp_sec)
            
            # 楽曲タイトルらしいパターンを検索
            if self._is_song_announcement(text):
                song_info = self._extract_song_from_announcement(text)
                if song_info:
                    song_title, artist = self.song_parser.parse_song_info(song_info)
                    results.append((timestamp, song_title, artist))
        
        return results
    
    def _is_likely_song(self, text: str) -> bool:
        """楽曲情報らしいかどうかを判定"""
        # 基本的な除外パターン
        exclude_patterns = [
            r'^(おつ|お疲|ありがと|thank|good|nice)',
            r'^(配信|stream|chat|コメ)',
            r'^(次|休憩|トイレ|水分)',
            r'^[0-9]+$',
            r'^[!@#$%^&*()_+={}[\]:";\'<>?,./~`-]+$',
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # 楽曲らしいパターン
        song_patterns = [
            r'/',  # アーティスト区切り
            r'feat\.|feat ',
            r'CV\.|CV:',
            r'×',
            r'with',
            r'歌|曲|ソング',
        ]
        
        for pattern in song_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # 基本的に日本語・英語が含まれていればOK
        if re.search(r'[a-zA-Z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return len(text.strip()) > 2  # 最低3文字以上
        
        return False
    
    def _is_song_announcement(self, text: str) -> bool:
        """字幕テキストが楽曲紹介かどうかを判定"""
        announcement_patterns = [
            r'次.*歌|歌.*次',
            r'続いて',
            r'それでは',
            r'今度は',
            r'お次は',
            r'では.*歌',
            r'歌います',
            r'歌わせて',
        ]
        
        for pattern in announcement_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_song_from_announcement(self, text: str) -> Optional[str]:
        """楽曲紹介テキストから楽曲名を抽出"""
        # 楽曲名抽出パターン
        patterns = [
            r'[「『]([^」』]+)[」』]',  # 「」『』で囲まれた部分
            r'次.*歌.*[は：は](.+)',
            r'続いて.*[は：は](.+)',
            r'歌います.*[は：は](.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """秒数をタイムスタンプ形式（MM:SS）に変換"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def scrape_video_content(self, video_id: str) -> List[Dict[str, Any]]:
        """動画コンテンツから楽曲情報を総合的に抽出"""
        all_songs = []
        
        try:
            print(f"Scraping video content for: {video_id}")
        except UnicodeEncodeError:
            print(f"Scraping video content for video ID: {video_id}")
        
        # 1. 説明文から抽出
        print("  Extracting from description...")
        description_songs = self.extract_from_description(video_id)
        
        # 2. 字幕から抽出
        print("  Extracting from transcript...")
        transcript_songs = self.extract_from_transcript(video_id)
        
        # 結果をマージ（重複除去）
        seen_songs = set()
        
        for timestamp, title, artist in description_songs + transcript_songs:
            song_key = f"{title.lower()}_{artist.lower()}"
            if song_key not in seen_songs:
                seen_songs.add(song_key)
                
                genre = self.genre_classifier.classify_genre(title, artist)
                search_term = f"{title} {artist}".strip()
                
                song_data = {
                    'timestamp': timestamp,
                    'title': title,
                    'artist': artist,
                    'search_term': search_term,
                    'genre': genre,
                    'video_id': video_id,
                    'extraction_method': 'video_content'
                }
                all_songs.append(song_data)
        
        print(f"  Found {len(all_songs)} songs from video content")
        return all_songs

def process_videos_with_content_scraping(user_ids: List[str], api_key: str, output_file: str = "video_content_songs.csv"):
    """動画コンテンツスクレイピングでユーザーの動画を処理"""
    if not YOUTUBE_API_AVAILABLE:
        print("YouTube API client not available")
        return
    
    config = Config()
    scraper = VideoContentScraper(config, api_key)
    
    all_songs = []
    
    # ユーザーごとに処理
    for user_id in user_ids:
        print(f"\nProcessing user: {user_id}")
        
        try:
            # ユーザーの動画リストを取得
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # チャンネルの動画を取得
            search_response = youtube.search().list(
                channelId=user_id,
                part='id,snippet',
                maxResults=50,
                order='date',
                type='video'
            ).execute()
            
            videos = search_response.get('items', [])
            
            # 歌枠動画をフィルタリング
            singing_videos = []
            for video in videos:
                title = video['snippet']['title']
                if any(keyword in title.lower() for keyword in ['歌', '歌枠', 'karaoke', 'sing', 'ライブ']):
                    singing_videos.append(video)
            
            print(f"Found {len(singing_videos)} potential singing videos")
            
            # 各動画から楽曲情報を抽出
            for video in singing_videos[:5]:  # 最初の5動画のみテスト
                video_id = video['id']['videoId']
                video_title = video['snippet']['title']
                
                try:
                    print(f"\nProcessing: {video_title}")
                except UnicodeEncodeError:
                    print(f"\nProcessing video: {video_id}")
                
                songs = scraper.scrape_video_content(video_id)
                all_songs.extend(songs)
        
        except Exception as e:
            print(f"Error processing user {user_id}: {e}")
    
    # CSV出力
    if all_songs:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['No', '曲', '歌手-ユニット', '検索用', 'ジャンル', 'タイムスタンプ', '動画ID', '抽出方法']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for i, song in enumerate(all_songs, 1):
                writer.writerow({
                    'No': i,
                    '曲': song['title'],
                    '歌手-ユニット': song['artist'],
                    '検索用': song['search_term'],
                    'ジャンル': song['genre'],
                    'タイムスタンプ': song['timestamp'],
                    '動画ID': song['video_id'],
                    '抽出方法': song['extraction_method']
                })
        
        print(f"\nSaved {len(all_songs)} songs to {output_file}")
    else:
        print("No songs found")

if __name__ == "__main__":
    # APIキーの読み込み
    try:
        with open('api_key.txt', 'r', encoding='utf-8') as f:
            api_key = f.read().strip()
    except FileNotFoundError:
        print("api_key.txt not found")
        exit(1)
    
    # ユーザーIDの読み込み
    try:
        with open('user_ids.json', 'r', encoding='utf-8') as f:
            user_ids = json.load(f)
    except FileNotFoundError:
        print("user_ids.json not found")
        exit(1)
    
    # 動画コンテンツスクレイピング実行
    process_videos_with_content_scraping(user_ids, api_key)