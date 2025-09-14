"""
APIキーなしで動画の字幕のみから楽曲情報を抽出するスクリプト
"""
import json
import re
from typing import List, Dict, Any, Tuple, Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPT_AVAILABLE = True
except ImportError:
    print("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
    TRANSCRIPT_AVAILABLE = False

from enhanced_extractor import Config, EnhancedGenreClassifier, EnhancedSongParser, EnhancedTextCleaner

class TranscriptOnlyScraper:
    def __init__(self, config: Config):
        self.config = config
        self.genre_classifier = EnhancedGenreClassifier(config)
        self.song_parser = EnhancedSongParser(config)
        self.text_cleaner = EnhancedTextCleaner(config)
    
    def extract_video_id_from_url(self, url: str) -> Optional[str]:
        """YouTube URLから動画IDを抽出"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'^([a-zA-Z0-9_-]+)$'  # 直接IDを指定した場合
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_transcript(self, video_id: str) -> List[Dict]:
        """動画の字幕を取得"""
        if not TRANSCRIPT_AVAILABLE:
            print("youtube-transcript-api is not installed")
            return []
        
        try:
            # v1.2.2のAPI使用方法
            # 字幕リストを取得
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)
            
            # 利用可能な字幕から日本語を優先して選択
            selected_transcript = None
            
            # 日本語を優先
            for transcript in transcript_list:
                if transcript.language_code == 'ja':
                    selected_transcript = transcript
                    print("Found Japanese transcript")
                    break
            
            # 日本語がない場合は英語
            if not selected_transcript:
                for transcript in transcript_list:
                    if transcript.language_code == 'en':
                        selected_transcript = transcript
                        print("Found English transcript")
                        break
            
            # どちらもない場合は最初の利用可能な字幕
            if not selected_transcript and transcript_list:
                selected_transcript = transcript_list[0]
                print(f"Using transcript in language: {selected_transcript.language_code}")
            
            if selected_transcript:
                return selected_transcript.fetch()
            else:
                print("No transcript available")
                return []
        
        except Exception as e:
            print(f"Error getting transcript for {video_id}: {e}")
            return []
    
    def extract_songs_from_transcript(self, transcript_data: List[Dict], video_id: str) -> List[Dict[str, Any]]:
        """字幕データから楽曲情報を抽出"""
        songs = []
        
        print(f"Analyzing {len(transcript_data)} transcript entries...")
        
        for i, entry in enumerate(transcript_data):
            text = entry.text.strip() if hasattr(entry, 'text') else str(entry).strip()
            start_time = entry.start if hasattr(entry, 'start') else 0
            
            # タイムスタンプを作成
            timestamp = self._seconds_to_timestamp(start_time)
            
            # 楽曲情報の可能性をチェック
            if self._is_song_mention(text):
                song_info = self._extract_song_info(text)
                if song_info:
                    song_title, artist = self.song_parser.parse_song_info(song_info)
                    genre = self.genre_classifier.classify_genre(song_title, artist)
                    
                    songs.append({
                        'timestamp': timestamp,
                        'title': song_title,
                        'artist': artist,
                        'search_term': f"{song_title} {artist}".strip(),
                        'genre': genre,
                        'video_id': video_id,
                        'confidence': self._calculate_confidence(text),
                        'original_text': text
                    })
        
        # 重複除去
        unique_songs = []
        seen = set()
        
        for song in songs:
            key = f"{song['title'].lower()}_{song['artist'].lower()}"
            if key not in seen:
                seen.add(key)
                unique_songs.append(song)
        
        return unique_songs
    
    def _is_song_mention(self, text: str) -> bool:
        """テキストが楽曲に関する言及かどうかを判定（改良版）"""
        # より包括的な楽曲関連パターン
        song_patterns = [
            r'[「『]([^」』]+)[」』]',  # 括弧で囲まれた楽曲名
            r'次.*歌|歌.*次',
            r'続いて',
            r'それでは',
            r'今度は',
            r'お次は',
            r'歌います',
            r'歌わせて',
            r'歌った',
            r'歌う',
            r'歌って',
            r'リクエスト',
            r'歌枠|うたわく',
            r'カラオケ|からおけ',
            r'cover|カバー',
            r'original|オリジナル',
            r'ボカロ|vocaloid',
            r'アニソン|anime',
            r'楽曲|曲',
            r'ソング|song',
            r'プロジェクト',  # 楽曲プロジェクト名
            r'ミックス|mix',  # 楽曲ミックス
        ]
        
        for pattern in song_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # アーティスト名や楽曲らしい要素
        if any(sep in text for sep in ['/', 'feat.', 'CV.', '×', 'with']):
            return True
        
        # 短いテキストで音楽的な要素がある場合
        if len(text.strip()) < 50:  # 短い文章
            music_indicators = ['歌', 'うた', '曲', 'song', 'sing', 'music']
            if any(indicator in text.lower() for indicator in music_indicators):
                return True
        
        return False
    
    def _extract_song_info(self, text: str) -> Optional[str]:
        """テキストから楽曲情報を抽出（改良版）"""
        # 括弧で囲まれた部分を抽出
        bracket_match = re.search(r'[「『]([^」』]+)[」』]', text)
        if bracket_match:
            return bracket_match.group(1)
        
        # "次は〜"のような形式（より柔軟に）
        next_patterns = [
            r'次.*[はに：は、](.+)',
            r'続いて.*[はに：は、](.+)',
            r'歌います.*[はに：は、](.+)',
            r'歌わせて.*[はに：は、](.+)',
            r'歌った.*[はに：は、](.+)',
            r'歌う.*[はに：は、](.+)',
            r'プロジェクト.*[はに：は、](.+)',
            r'リクエスト.*[はに：は、](.+)',
            r'オリジナル.*[はに：は、](.+)',
        ]
        
        for pattern in next_patterns:
            match = re.search(pattern, text)
            if match:
                extracted = match.group(1).strip()
                # 不要な部分を除去
                extracted = re.sub(r'[。、！？\.\!\?]+$', '', extracted)
                if len(extracted) > 1:
                    return extracted
        
        # 楽曲らしい単語が含まれている短いテキスト
        if len(text.strip()) < 100:  # 短めのテキスト
            music_keywords = ['歌', '曲', 'ソング', 'song', 'ミックス', 'mix', 'プロジェクト', 'オリジナル']
            if any(keyword in text for keyword in music_keywords):
                # 楽曲名らしい部分を抽出
                cleaned_text = re.sub(r'^[はい、そうね。]+', '', text)  # 相槌を除去
                cleaned_text = re.sub(r'[。、！？\.\!\?]+$', '', cleaned_text)  # 句読点を除去
                if len(cleaned_text.strip()) > 2:
                    return cleaned_text.strip()
        
        # テキスト全体が楽曲情報の可能性
        if self._looks_like_song_title(text):
            return text
        
        return None
    
    def _looks_like_song_title(self, text: str) -> bool:
        """テキストが楽曲タイトルらしいかどうかを判定（緩和版）"""
        # 明らかに楽曲でないもの（最小限）
        exclude_patterns = [
            r'^(はい|そう|うん|ええ|よし)$',  # 単体の相槌のみ
            r'^(www|ww|w)$',  # 笑いの表現のみ
            r'^[0-9]+$',  # 数字のみ
            r'^[!@#$%^&*()_+={}[\]:";\'<>?,./~`\s-]+$',  # 記号のみ
            r'^[\s\u3000]+$',  # 空白のみ
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # 長さ制限を緩和（短すぎるか長すぎる場合のみ除外）
        text_len = len(text.strip())
        if text_len < 1 or text_len > 100:  # より緩い制限
            return False
        
        # 基本的に文字が含まれていればOK
        if re.search(r'[a-zA-Z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return True
        
        return False
    
    def _calculate_confidence(self, text: str) -> float:
        """楽曲情報の信頼度を計算（0.0-1.0）"""
        confidence = 0.5  # ベース値
        
        # 括弧で囲まれている場合は高信頼度
        if re.search(r'[「『][^」』]+[」』]', text):
            confidence += 0.3
        
        # 楽曲紹介のキーワードがある場合
        if re.search(r'次.*歌|歌.*次|続いて|歌います', text):
            confidence += 0.2
        
        # アーティスト情報がある場合
        if '/' in text or 'feat.' in text:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """秒数をタイムスタンプ形式（MM:SS）に変換"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def scrape_single_video(self, video_url: str) -> List[Dict[str, Any]]:
        """単一の動画から楽曲情報を抽出"""
        video_id = self.extract_video_id_from_url(video_url)
        if not video_id:
            print(f"Invalid YouTube URL: {video_url}")
            return []
        
        print(f"Processing video: {video_id}")
        
        # 字幕を取得
        transcript_data = self.get_transcript(video_id)
        if not transcript_data:
            print("No transcript available")
            return []
        
        # 楽曲情報を抽出
        songs = self.extract_songs_from_transcript(transcript_data, video_id)
        
        print(f"Found {len(songs)} potential songs")
        return songs

def main():
    """メイン実行関数"""
    if not TRANSCRIPT_AVAILABLE:
        print("Please install youtube-transcript-api: pip install youtube-transcript-api")
        return
    
    config = Config()
    scraper = TranscriptOnlyScraper(config)
    
    # 動画URLを入力
    print("YouTube URL or Video ID を入力してください:")
    video_input = input().strip()
    
    if not video_input:
        print("No input provided")
        return
    
    # 楽曲情報を抽出
    songs = scraper.scrape_single_video(video_input)
    
    # 結果を表示
    if songs:
        print(f"\n=== Found {len(songs)} songs ===")
        for i, song in enumerate(songs, 1):
            print(f"{i}. [{song['timestamp']}] {song['title']}")
            if song['artist']:
                print(f"   Artist: {song['artist']}")
            print(f"   Genre: {song['genre']}")
            print(f"   Confidence: {song['confidence']:.2f}")
            print(f"   Original: {song['original_text'][:50]}...")
            print()
        
        # CSV出力オプション
        save_csv = input("Save to CSV? (y/n): ").strip().lower()
        if save_csv == 'y':
            import csv
            output_file = f"transcript_songs_{songs[0]['video_id']}.csv"
            
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['No', '曲', '歌手-ユニット', '検索用', 'ジャンル', 'タイムスタンプ', '動画ID', '信頼度']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for i, song in enumerate(songs, 1):
                    writer.writerow({
                        'No': i,
                        '曲': song['title'],
                        '歌手-ユニット': song['artist'],
                        '検索用': song['search_term'],
                        'ジャンル': song['genre'],
                        'タイムスタンプ': song['timestamp'],
                        '動画ID': song['video_id'],
                        '信頼度': song['confidence']
                    })
            
            print(f"Saved to {output_file}")
    else:
        print("No songs found")

if __name__ == "__main__":
    main()