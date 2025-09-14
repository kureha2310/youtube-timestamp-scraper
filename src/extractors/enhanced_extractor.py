import json
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Config:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    @property
    def genres(self) -> Dict[str, Any]:
        return self.data.get('genres', {})
    
    @property
    def singing_detection(self) -> Dict[str, Any]:
        return self.data.get('singing_detection', {})
    
    @property
    def timestamp_extraction(self) -> Dict[str, Any]:
        return self.data.get('timestamp_extraction', {})
    
    @property
    def text_cleaning(self) -> Dict[str, Any]:
        return self.data.get('text_cleaning', {})

class EnhancedTextCleaner:
    def __init__(self, config: Config):
        self.config = config
        self.cleaning_config = config.text_cleaning
    
    def normalize_characters(self, text: str) -> str:
        """全角文字を半角に正規化"""
        char_map = self.cleaning_config.get('normalize_chars', {})
        for full, half in char_map.items():
            text = text.replace(full, half)
        return text
    
    def remove_html_tags(self, text: str) -> str:
        """HTMLタグとエスケープ文字を除去"""
        # 全てのHTMLタグを除去（より包括的）
        text = re.sub(r'<[^>]*>', '', text)
        
        # HTMLエスケープ文字を元に戻す
        text = text.replace('&amp;', '&')
        text = text.replace('&#39;', "'")
        text = text.replace('&quot;', '"')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        
        return text
    
    def remove_numbering(self, text: str) -> str:
        """先頭のナンバリングを除去"""
        patterns = self.cleaning_config.get('numbering_patterns', [])
        for pattern in patterns:
            text = re.sub(pattern, '', text)
        return text.strip()
    
    def clean_text(self, text: str) -> str:
        """包括的なテキストクリーニング"""
        # 1. 基本的な正規化
        text = self.normalize_characters(text)
        
        # 2. HTMLタグとエスケープ文字の処理
        text = self.remove_html_tags(text)
        
        # 3. 先頭ナンバリングの除去
        text = self.remove_numbering(text)
        
        # 4. 余分な空白を除去
        text = ' '.join(text.split())
        
        return text.strip()

class EnhancedTimestampExtractor:
    def __init__(self, config: Config):
        self.config = config
        self.extraction_config = config.timestamp_extraction
        self.text_cleaner = EnhancedTextCleaner(config)
    
    def extract_html_timestamps(self, text: str) -> List[Tuple[str, str]]:
        """HTMLアンカー形式のタイムスタンプを抽出"""
        results = []
        
        # より柔軟なHTMLアンカーパターン
        patterns = [
            r'<a[^>]*>(\d{1,2}:\d{2}(?::\d{2})?)</a>\s*([^<\n]+)',
            r'(\d{1,2}:\d{2}(?::\d{2})?)(?:</a>)?\s*([^<\n\r]+?)(?=\s*<|$)',
            r'<a[^>]*href="[^"]*[&?]t=\d+"[^>]*>(\d{1,2}:\d{2}(?::\d{2})?)</a>\s*(.+?)(?=<|$)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                timestamp = match.group(1)
                content = self.text_cleaner.clean_text(match.group(2))
                
                if self.is_valid_timestamp(timestamp, content):
                    results.append((timestamp, content))
        
        return results
    
    def extract_plain_timestamps(self, text: str) -> List[Tuple[str, str]]:
        """プレーンテキスト形式のタイムスタンプを抽出（改善版）"""
        results = []
        patterns = [
            self.extraction_config['patterns']['plain_timestamp'],
            self.extraction_config['patterns']['flexible_timestamp'],
            self.extraction_config['patterns']['japanese_timestamp']
        ]
        
        # より多くの可能なパターンを追加（曲名のみにも対応）
        additional_patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:：・･]\s*(.+?)(?=\n|$)',
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)(?=\n|\d{1,2}:\d{2}|$)',
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[）)]\s*(.+?)(?=\n|$)',
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*(.+?)(?=\s+\d{1,2}:\d{2}|\n|$)',
            # 曲名のみのパターンを追加
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*(.+?)$',  # 行末まで
            r'(\d{1,2}:\d{2}(?::\d{2})?)[\s\t]*(.+?)(?=\s*\d{1,2}:\d{2}|$)',  # より柔軟
            r'(\d{1,2}:\d{2}(?::\d{2})?)[^\w]*(.+?)(?=\n|$)',  # 記号区切りも許可
        ]
        
        all_patterns = patterns + additional_patterns
        
        # テキスト全体と行ごとの両方で処理
        for pattern in all_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                timestamp = match.group(1)
                content = self.text_cleaner.clean_text(match.group(2))
                
                if self.is_valid_timestamp(timestamp, content):
                    # 重複チェック
                    duplicate = False
                    for existing_ts, existing_content in results:
                        if existing_ts == timestamp and existing_content.lower() == content.lower():
                            duplicate = True
                            break
                    
                    if not duplicate:
                        results.append((timestamp, content))
        
        # 行ごとに処理（元の処理も残す）
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern in all_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    timestamp = match.group(1)
                    content = self.text_cleaner.clean_text(match.group(2))
                    
                    if self.is_valid_timestamp(timestamp, content):
                        # 重複チェック
                        duplicate = False
                        for existing_ts, existing_content in results:
                            if existing_ts == timestamp and existing_content.lower() == content.lower():
                                duplicate = True
                                break
                        
                        if not duplicate:
                            results.append((timestamp, content))
        
        return results
    
    def is_valid_timestamp(self, timestamp: str, content: str) -> bool:
        """タイムスタンプの妥当性をチェック（曲名のみでも許可）"""
        if not content or len(content.strip()) < 1:  # 1文字でもOK
            return False
        
        # HTMLタグが残っている場合は無効
        if '<' in content or '>' in content:
            return False
        
        # 必要最小限の除外パターンのみ
        critical_invalid = [
            r'^https?://',  # URLは除外
            r'UCY85ViSyTU5Wy_bwsUVjkdA',  # チャンネルIDは除外
            r'youtube\.com/watch',  # YouTube URLは除外
            r'^www\.',
            r'href=',
            r'</a>',
            r'<a ',
        ]
        
        for pattern in critical_invalid:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        # 明らかに楽曲でないものを除外（最小限）
        obvious_non_music = [
            r'^(おつ|お疲|ありがと|thank|thanks|good|nice|www|ww|w$)',
            r'^(配信|stream|chat|コメ|comment|次|next)',
            r'^[0-9]+$',  # 数字のみは除外
            r'^[!@#$%^&*()_+={}[\]:";\'<>?,./~`-]+$',  # 記号のみは除外
        ]
        
        for pattern in obvious_non_music:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        # 基本的に文字が含まれていればOK（曲名のみでも許可）
        if re.search(r'[a-zA-Z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', content):
            return True
        
        return False
    
    def extract_all_timestamps(self, text: str) -> List[Tuple[str, str]]:
        """テキストからすべてのタイムスタンプを抽出"""
        results = []
        
        # HTMLアンカー形式
        html_results = self.extract_html_timestamps(text)
        
        # プレーンテキスト形式（HTMLが見つからない場合のみ）
        if not html_results:
            plain_results = self.extract_plain_timestamps(text)
            results.extend(plain_results)
        else:
            results.extend(html_results)
        
        # より厳密な重複除去
        seen = set()
        unique_results = []
        for timestamp, content in results:
            # より詳細な正規化キー
            normalized_timestamp = timestamp.lower().strip()
            normalized_content = re.sub(r'\s+', ' ', content.lower().strip())
            
            key = (normalized_timestamp, normalized_content)
            if key not in seen:
                seen.add(key)
                unique_results.append((timestamp, content))
        
        return unique_results

class EnhancedGenreClassifier:
    def __init__(self, config: Config):
        self.config = config
        self.genres_config = config.genres
    
    def classify_genre(self, song_title: str, artist: str) -> str:
        """楽曲のジャンルを分類"""
        combined_text = f"{song_title} {artist}".lower()
        
        # 各ジャンルをチェック
        for genre_name, genre_data in self.genres_config.items():
            if self._matches_genre(combined_text, song_title.lower(), genre_data):
                return self._get_display_name(genre_name)
        
        return "その他"
    
    def _matches_genre(self, combined_text: str, title: str, genre_data: Dict) -> bool:
        """ジャンルにマッチするかチェック"""
        # アーティストをチェック
        for artist in genre_data.get('artists', []):
            if artist.lower() in combined_text:
                return True
        
        # プロデューサー/グループをチェック
        for producer in genre_data.get('producers', []) + genre_data.get('groups', []):
            if producer.lower() in combined_text:
                return True
        
        # タイトルをチェック
        for song_title in genre_data.get('titles', []):
            if song_title.lower() in title:
                return True
        
        # キーワードをチェック
        for keyword in genre_data.get('keywords', []):
            if keyword.lower() in combined_text:
                return True
        
        return False
    
    def _get_display_name(self, genre_name: str) -> str:
        """ジャンル名の表示形式を取得"""
        display_names = {
            'vocaloid': 'Vocaloid',
            'anime': 'アニメ',
            'jpop': 'J-POP',
            'utaite': '歌い手'
        }
        return display_names.get(genre_name, genre_name.capitalize())

class EnhancedSongParser:
    def __init__(self, config: Config):
        self.config = config
        self.text_cleaner = EnhancedTextCleaner(config)
    
    def parse_song_info(self, text: str) -> Tuple[str, str]:
        """楽曲情報（タイトル、アーティスト）を解析"""
        text = self.text_cleaner.clean_text(text)
        
        # 様々な区切り文字で分割を試行
        separators = ['/', ' / ', '／', ' ／ ', 'feat.', 'feat ', 'CV.', 'CV:', 'by ', ' - ', '－']
        
        for separator in separators:
            if separator in text:
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    song_title = parts[0].strip()
                    artist = parts[1].strip()
                    
                    # 不要な記号や文字を除去
                    artist = self._clean_artist_name(artist)
                    
                    if song_title and artist:
                        return song_title, artist
        
        # 区切り文字が見つからない場合は全体を楽曲タイトルとして扱う
        return text.strip(), ""
    
    def _clean_artist_name(self, artist: str) -> str:
        """アーティスト名をクリーニング"""
        # 括弧内の情報を除去（ただし、重要な情報は保持）
        artist = re.sub(r'\([^)]*cover[^)]*\)', '', artist, flags=re.IGNORECASE)
        artist = re.sub(r'\([^)]*version[^)]*\)', '', artist, flags=re.IGNORECASE)
        
        # 余分な記号を除去
        artist = re.sub(r'^[・･\-\s]+', '', artist)
        artist = re.sub(r'[・･\-\s]+$', '', artist)
        
        return artist.strip()

# 使用例とテスト用の関数
def test_enhanced_extractor():
    """拡張抽出機能のテスト"""
    config = Config()
    extractor = EnhancedTimestampExtractor(config)
    classifier = EnhancedGenreClassifier(config)
    parser = EnhancedSongParser(config)
    
    # テストケース
    test_texts = [
        '<a href="...&t=413">6:53</a> 1.サイハテ/小林オニキス feat. 初音ミク',
        '1:07:50 9.炉心融解/iroha(sasaki) feat. 鏡音リン',
        '15:30　残酷な天使のテーゼ / 高橋洋子',
        '22:45：God knows / 涼宮ハルヒ(平野綾)',
        '30:15・夜に駆ける/YOASOBI'
    ]
    
    for text in test_texts:
        timestamps = extractor.extract_all_timestamps(text)
        print(f"入力: {text}")
        for ts, content in timestamps:
            song, artist = parser.parse_song_info(content)
            genre = classifier.classify_genre(song, artist) if artist else "その他"
            print(f"  {ts} - {song} / {artist} ({genre})")
        print()

if __name__ == "__main__":
    test_enhanced_extractor()