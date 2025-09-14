#!/usr/bin/env python3
"""
YouTube字幕から話題を自動抽出するアナライザー
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from datetime import timedelta
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from dataclasses import dataclass

@dataclass
class TopicSegment:
    """話題セグメント"""
    start_time: float  # 開始時間（秒）
    end_time: float    # 終了時間（秒）
    topic: str         # 話題
    keywords: List[str]  # キーワード
    confidence: float  # 信頼度
    
    @property
    def duration(self) -> float:
        """セグメントの長さ（秒）"""
        return self.end_time - self.start_time
    
    @property
    def start_timestamp(self) -> str:
        """開始時間のタイムスタンプ形式"""
        return self._seconds_to_timestamp(self.start_time)
    
    @property
    def end_timestamp(self) -> str:
        """終了時間のタイムスタンプ形式"""
        return self._seconds_to_timestamp(self.end_time)
    
    @property
    def youtube_link(self) -> str:
        """YouTube リンク（開始時間付き）"""
        return f"&t={int(self.start_time)}"
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """秒数をタイムスタンプに変換"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        hours = minutes // 60
        minutes = minutes % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

class TranscriptTopicAnalyzer:
    def __init__(self):
        """初期化"""
        # 話題転換を示すキーワード
        self.topic_transition_keywords = [
            # 明確な話題転換
            "さて", "それでは", "次に", "続いて", "ところで", "そういえば",
            "話は変わって", "話変わるけど", "別の話", "そうそう",
            
            # 時間的な区切り
            "今度は", "今回は", "最初に", "最後に", "終わりに",
            
            # 質問・応答
            "質問", "聞きたい", "答え", "回答", "コメント",
            
            # ゲーム配信特有
            "ゲーム", "プレイ", "攻略", "レベル", "ステージ", "ボス",
            
            # 歌配信特有
            "歌", "うた", "曲", "リクエスト", "次の", "1曲目", "2曲目",
            
            # 雑談特有
            "最近", "今日", "昨日", "明日", "今度", "前回",
        ]
        
        # 強い話題転換（より確実な区切り）
        self.strong_transition_patterns = [
            r"それでは.*?(?:行|い)きます",
            r"次.*?(?:行|い)きます",
            r"(?:さて|では).*?(?:始|はじ)め",
            r"(?:今度|今回).*?(?:やり|する)",
            r"(?:最初|まず).*?(?:から|は)",
            r"(?:続い|つづい)て.*?(?:は|を)",
            r"(?:話.*?変わ|別.*?話)",
            r"(?:質問|コメント).*?(?:来|き)て",
            r"\d+(?:曲目|番目|つ目)",
        ]
        
        # トピック推定用キーワード辞書
        self.topic_keywords = {
            "ゲーム": ["ゲーム", "プレイ", "攻略", "レベル", "ステージ", "ボス", "キャラ", "アイテム", "RPG", "FPS"],
            "歌・音楽": ["歌", "うた", "曲", "音楽", "歌詞", "メロディ", "リズム", "ボーカル", "楽器", "作詞", "作曲"],
            "雑談": ["最近", "今日", "昨日", "日常", "生活", "思った", "感じた", "話", "おしゃべり"],
            "質問回答": ["質問", "コメント", "答え", "回答", "聞かれ", "教え", "説明"],
            "料理": ["料理", "食べ", "飲み", "レシピ", "作り", "味", "美味しい", "食材"],
            "お知らせ": ["お知らせ", "告知", "予定", "イベント", "配信", "動画", "コラボ", "企画"],
            "感想・レビュー": ["感想", "レビュー", "評価", "良かった", "面白い", "つまらない", "すごい"],
        }
        
        # 無視するセグメント（ノイズ）
        self.ignore_patterns = [
            r"^[あー]+$",  # 「あー」だけ
            r"^[えー]+$",  # 「えー」だけ
            r"^[うー]+$",  # 「うー」だけ
            r"^[んー]+$",  # 「んー」だけ
            r"^[はい]+$",  # 「はい」だけ
            r"^[そう]+$",  # 「そう」だけ
            r"^w+$",       # 「w」だけ
            r"^\.+$",      # ピリオドだけ
            r"^[？！。、]+$",  # 記号だけ
        ]
    
    def get_transcript(self, video_id: str, language: str = 'ja') -> List[Dict]:
        """YouTube動画の字幕を取得"""
        try:
            # 利用可能な字幕をリスト表示
            try:
                transcript_list = YouTubeTranscriptApi().list(video_id)
                print(f"利用可能な字幕: {len(transcript_list)}種類")
                
                # 利用可能な字幕の言語を表示
                languages = []
                for transcript in transcript_list:
                    languages.append(transcript.get('language_code', 'unknown'))
                print(f"言語: {', '.join(languages)}")
                
            except Exception as e:
                print(f"字幕リスト取得でエラー: {e}")
            
            # まず日本語の字幕を直接取得を試す
            try:
                transcript_data = YouTubeTranscriptApi().fetch(video_id, languages=['ja'])
                print(f"日本語字幕を取得しました: {len(transcript_data)}セグメント")
                return transcript_data
            except Exception as e:
                print(f"日本語字幕取得でエラー: {e}")
            
            # 英語字幕を試す
            try:
                transcript_data = YouTubeTranscriptApi().fetch(video_id, languages=['en'])
                print(f"英語字幕を取得しました: {len(transcript_data)}セグメント")
                return transcript_data
            except Exception as e:
                print(f"英語字幕取得でエラー: {e}")
            
            # 自動生成字幕を試す（言語指定なし）
            try:
                transcript_data = YouTubeTranscriptApi().fetch(video_id)
                print(f"自動生成字幕を取得しました: {len(transcript_data)}セグメント")
                return transcript_data
            except Exception as e:
                print(f"自動生成字幕取得でエラー: {e}")
            
            return []
                
        except Exception as e:
            print(f"字幕取得でエラー: {e}")
            return []
    
    def clean_text(self, text: str) -> str:
        """テキストをクリーニング"""
        # HTMLタグを除去
        text = re.sub(r'<[^>]*>', '', text)
        
        # 特殊文字を正規化
        text = re.sub(r'[♪♫♬🎵🎶]', '', text)  # 音楽記号を除去
        text = re.sub(r'\s+', ' ', text)  # 連続する空白を1つに
        
        return text.strip()
    
    def is_topic_transition(self, text: str, prev_text: str = "") -> Tuple[bool, float]:
        """話題転換かどうかを判定"""
        confidence = 0.0
        
        # 強い転換パターンをチェック
        for pattern in self.strong_transition_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                confidence += 0.8
        
        # 転換キーワードをチェック
        for keyword in self.topic_transition_keywords:
            if keyword in text:
                confidence += 0.3
        
        # 文の境界を考慮
        if re.search(r'[。！？].*?(?:さて|それでは|次に|続いて)', text):
            confidence += 0.5
        
        # 前のテキストとの関連性をチェック
        if prev_text:
            # 全く違う内容の場合は転換の可能性
            common_words = set(text.split()) & set(prev_text.split())
            if len(common_words) < 2:
                confidence += 0.2
        
        return confidence > 0.5, min(confidence, 1.0)
    
    def extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        # 名詞と動詞を中心に抽出（簡易版）
        keywords = []
        
        # 基本的なキーワード抽出（正規表現ベース）
        word_patterns = [
            r'[ゲーム配信実況プレイ]+',
            r'[歌うた音楽曲声]+',
            r'[料理食事飯レシピ]+',
            r'[質問回答コメント]+',
            r'[告知お知らせ予定企画]+',
        ]
        
        for pattern in word_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        # 頻出する名詞っぽい部分を抽出
        noun_pattern = r'[ァ-ヶー]+|[ぁ-ん]+|[一-龯]+'
        potential_nouns = re.findall(noun_pattern, text)
        
        # 長さでフィルタリング
        keywords.extend([word for word in potential_nouns if 2 <= len(word) <= 6])
        
        return list(set(keywords))[:5]  # 重複除去して最大5個
    
    def classify_topic(self, text: str, keywords: List[str]) -> str:
        """テキストとキーワードから話題を分類"""
        topic_scores = {}
        
        for topic, topic_keywords in self.topic_keywords.items():
            score = 0
            combined_text = text + " " + " ".join(keywords)
            
            for keyword in topic_keywords:
                if keyword in combined_text:
                    score += 1
            
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        else:
            return "その他"
    
    def should_ignore_segment(self, text: str) -> bool:
        """セグメントを無視すべきかどうか判定"""
        for pattern in self.ignore_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # 短すぎるテキスト
        if len(text.strip()) < 3:
            return True
        
        # 記号や数字のみ
        if re.match(r'^[0-9\s\W]+$', text):
            return True
        
        return False
    
    def merge_short_segments(self, segments: List[TopicSegment], min_duration: float = 30.0) -> List[TopicSegment]:
        """短いセグメントを前後と統合"""
        if not segments:
            return segments
        
        merged = []
        current = segments[0]
        
        for next_segment in segments[1:]:
            # 現在のセグメントが短い場合は次と統合
            if current.duration < min_duration:
                # トピックが同じか、より長いセグメントのトピックを採用
                if current.topic == next_segment.topic or next_segment.duration > current.duration:
                    topic = next_segment.topic
                else:
                    topic = current.topic
                
                # キーワードを統合
                combined_keywords = list(set(current.keywords + next_segment.keywords))[:5]
                
                # 統合されたセグメントを作成
                current = TopicSegment(
                    start_time=current.start_time,
                    end_time=next_segment.end_time,
                    topic=topic,
                    keywords=combined_keywords,
                    confidence=(current.confidence + next_segment.confidence) / 2
                )
            else:
                # 現在のセグメントを確定し、次に進む
                merged.append(current)
                current = next_segment
        
        # 最後のセグメントを追加
        merged.append(current)
        
        return merged
    
    def analyze_topics(self, video_id: str, min_segment_duration: float = 30.0) -> List[TopicSegment]:
        """字幕から話題セグメントを分析"""
        print(f"動画 {video_id} の字幕を分析中...")
        
        # 字幕を取得
        transcript_data = self.get_transcript(video_id)
        if not transcript_data:
            return []
        
        segments = []
        current_segment_start = 0.0
        current_texts = []
        prev_text = ""
        
        for i, entry in enumerate(transcript_data):
            text = self.clean_text(entry['text'])
            start_time = entry['start']
            
            # 無視すべきセグメントをスキップ
            if self.should_ignore_segment(text):
                continue
            
            # 話題転換を判定
            is_transition, confidence = self.is_topic_transition(text, prev_text)
            
            # 話題転換が検出された、またはテキストが蓄積された場合
            if is_transition and current_texts:
                # 現在のセグメントを確定
                combined_text = " ".join(current_texts)
                keywords = self.extract_keywords(combined_text)
                topic = self.classify_topic(combined_text, keywords)
                
                segment = TopicSegment(
                    start_time=current_segment_start,
                    end_time=start_time,
                    topic=topic,
                    keywords=keywords,
                    confidence=confidence
                )
                
                segments.append(segment)
                
                # 新しいセグメントを開始
                current_segment_start = start_time
                current_texts = [text]
            else:
                # テキストを蓄積
                current_texts.append(text)
                if not current_texts or len(current_texts) == 1:
                    current_segment_start = start_time
            
            prev_text = text
        
        # 最後のセグメントを処理
        if current_texts:
            combined_text = " ".join(current_texts)
            keywords = self.extract_keywords(combined_text)
            topic = self.classify_topic(combined_text, keywords)
            
            # 動画の最後の時間を推定
            last_end_time = transcript_data[-1]['start'] + transcript_data[-1].get('duration', 5.0)
            
            segment = TopicSegment(
                start_time=current_segment_start,
                end_time=last_end_time,
                topic=topic,
                keywords=keywords,
                confidence=0.7
            )
            segments.append(segment)
        
        # 短いセグメントを統合
        segments = self.merge_short_segments(segments, min_segment_duration)
        
        print(f"{len(segments)}個の話題セグメントを検出しました")
        return segments
    
    def save_topics_to_csv(self, segments: List[TopicSegment], video_id: str, video_title: str = ""):
        """話題セグメントをCSVに保存"""
        import csv
        
        filename = f"topics_{video_id}.csv"
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "No", "開始時間", "終了時間", "長さ(分)", "話題", "キーワード", 
                "信頼度", "YouTubeリンク"
            ])
            
            for i, segment in enumerate(segments, 1):
                duration_minutes = segment.duration / 60
                youtube_url = f"https://www.youtube.com/watch?v={video_id}{segment.youtube_link}"
                
                writer.writerow([
                    i,
                    segment.start_timestamp,
                    segment.end_timestamp,
                    f"{duration_minutes:.1f}",
                    segment.topic,
                    ", ".join(segment.keywords),
                    f"{segment.confidence:.2f}",
                    youtube_url
                ])
        
        print(f"話題リストをCSVに保存しました: {filename}")
        
        # 統計表示
        topic_counts = {}
        total_duration = 0
        
        for segment in segments:
            topic_counts[segment.topic] = topic_counts.get(segment.topic, 0) + 1
            total_duration += segment.duration
        
        print(f"\n話題別統計:")
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {topic}: {count}セグメント")
        
        print(f"総時間: {total_duration/60:.1f}分")

def main():
    """テスト用メイン関数"""
    analyzer = TranscriptTopicAnalyzer()
    
    # テスト用動画ID
    video_id = input("動画IDまたはYouTube URLを入力してください: ").strip()
    
    # URLから動画IDを抽出
    if "youtube.com" in video_id or "youtu.be" in video_id:
        import re
        match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', video_id)
        if match:
            video_id = match.group(1)
        else:
            print("無効なYouTube URLです")
            return
    
    # 話題分析を実行
    segments = analyzer.analyze_topics(video_id)
    
    if segments:
        # 結果表示
        print(f"\n=== 検出された話題セグメント ===")
        for i, segment in enumerate(segments, 1):
            print(f"{i:2d}. {segment.start_timestamp}-{segment.end_timestamp} "
                  f"({segment.duration/60:.1f}分) {segment.topic}")
            if segment.keywords:
                print(f"     キーワード: {', '.join(segment.keywords)}")
            print(f"     信頼度: {segment.confidence:.2f}")
        
        # CSVに保存
        analyzer.save_topics_to_csv(segments, video_id)
    else:
        print("話題セグメントが見つかりませんでした")

if __name__ == "__main__":
    main()