#!/usr/bin/env python3
"""
ライブ配信の字幕からタイムスタンプを生成 + ライブチャット取得
"""

import json
import os
import csv
import re
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

@dataclass
class TranscriptTimestamp:
    """字幕から生成されたタイムスタンプ"""
    start_time: float  # 開始時間（秒）
    end_time: float    # 終了時間（秒） 
    text: str         # 内容
    confidence: float  # 信頼度
    
    @property
    def timestamp_text(self) -> str:
        """タイムスタンプ形式の文字列"""
        return self._seconds_to_timestamp(self.start_time)
    
    @property
    def youtube_url_param(self) -> str:
        """YouTube URL用のタイムスタンプパラメータ"""
        return f"t={int(self.start_time)}"
    
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

@dataclass
class LiveChatMessage:
    """ライブチャットメッセージ"""
    timestamp: str      # 送信時刻
    author: str        # 送信者名
    message: str       # メッセージ内容
    video_offset: float  # 動画開始からの時間（秒）

class LiveTranscriptExtractor:
    def __init__(self):
        """初期化"""
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise RuntimeError(".envファイルにAPI_KEYが設定されていません")
        
        self.youtube = discovery.build('youtube', 'v3', developerKey=self.api_key)
    
    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """動画情報を取得"""
        try:
            response = self.youtube.videos().list(
                part='snippet,liveStreamingDetails',
                id=video_id,
                fields='items(snippet(publishedAt,title,description),liveStreamingDetails)'
            ).execute()
            
            items = response.get('items', [])
            if not items:
                print(f"動画が見つかりませんでした: {video_id}")
                return None
            
            return items[0]
            
        except Exception as e:
            print(f"動画情報取得でエラー: {e}")
            return None
    
    def get_transcript(self, video_id: str) -> List[Dict]:
        """字幕を取得"""
        try:
            print("字幕を取得中...")
            
            # 日本語字幕を優先
            for lang in ['ja', 'en']:
                try:
                    # fetchメソッドで字幕を取得
                    transcript_data = YouTubeTranscriptApi().fetch(video_id, languages=[lang])
                    print(f"{lang}字幕を取得しました: {len(transcript_data)}セグメント")
                    return transcript_data
                except Exception as e:
                    print(f"{lang}字幕取得でエラー: {e}")
                    continue
            
            print("字幕が取得できませんでした")
            return []
            
        except Exception as e:
            print(f"字幕取得でエラー: {e}")
            return []
    
    def get_live_chat_messages(self, video_id: str) -> List[LiveChatMessage]:
        """ライブチャットメッセージを取得"""
        try:
            print("ライブチャット情報を確認中...")
            
            # まず動画の詳細情報を取得
            video_response = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=video_id
            ).execute()
            
            if not video_response.get('items'):
                print("動画情報が取得できませんでした")
                return []
            
            live_details = video_response['items'][0].get('liveStreamingDetails', {})
            active_live_chat_id = live_details.get('activeLiveChatId')
            
            if not active_live_chat_id:
                print("この動画はライブ配信ではないか、チャットが無効です")
                # アーカイブされたライブ配信のチャット取得を試す
                return self._get_archived_chat_messages(video_id)
            
            print(f"ライブチャットID: {active_live_chat_id}")
            return self._fetch_live_chat_messages(active_live_chat_id)
            
        except Exception as e:
            print(f"ライブチャット取得でエラー: {e}")
            return []
    
    def _get_archived_chat_messages(self, video_id: str) -> List[LiveChatMessage]:
        """アーカイブされたライブ配信のチャットを取得（制限あり）"""
        print("アーカイブされた配信のチャット取得を試行中...")
        
        # YouTube Data APIではアーカイブされたライブチャットの直接取得は制限されている
        # 代替として、通常のコメントからライブ配信時のものをフィルタリング
        try:
            comments = []
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="time"
            )
            
            while request and len(comments) < 500:  # 最大500件
                response = request.execute()
                
                for item in response.get('items', []):
                    comment = item['snippet']['topLevelComment']['snippet']
                    
                    # ライブ配信中のコメントかどうかの簡易判定
                    # （公開時刻に近い時刻のコメントをライブコメントと仮定）
                    comments.append(LiveChatMessage(
                        timestamp=comment.get('publishedAt', ''),
                        author=comment.get('authorDisplayName', ''),
                        message=comment.get('textDisplay', ''),
                        video_offset=0.0  # 正確なオフセット計算は困難
                    ))
                
                request = self.youtube.commentThreads().list_next(request, response)
            
            print(f"アーカイブコメントを取得: {len(comments)}件")
            return comments
            
        except Exception as e:
            print(f"アーカイブチャット取得でエラー: {e}")
            return []
    
    def _fetch_live_chat_messages(self, live_chat_id: str) -> List[LiveChatMessage]:
        """アクティブなライブチャットからメッセージを取得"""
        messages = []
        next_page_token = None
        
        try:
            for _ in range(10):  # 最大10ページ取得
                response = self.youtube.liveChatMessages().list(
                    liveChatId=live_chat_id,
                    part="snippet",
                    pageToken=next_page_token
                ).execute()
                
                for item in response.get('items', []):
                    snippet = item['snippet']
                    message_text = ''
                    
                    # メッセージタイプに応じて内容を取得
                    if snippet['type'] == 'textMessageEvent':
                        message_text = snippet['textMessageDetails']['messageText']
                    elif snippet['type'] == 'superChatEvent':
                        message_text = snippet.get('superChatDetails', {}).get('userComment', '')
                    
                    if message_text:
                        messages.append(LiveChatMessage(
                            timestamp=snippet['publishedAt'],
                            author=snippet['authorDetails']['displayName'],
                            message=message_text,
                            video_offset=float(snippet.get('displayTimeMs', 0)) / 1000.0
                        ))
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
                # レート制限回避
                import time
                time.sleep(1)
            
            print(f"ライブチャットメッセージを取得: {len(messages)}件")
            return messages
            
        except Exception as e:
            print(f"ライブチャット取得でエラー: {e}")
            return []
    
    def create_timestamps_from_transcript(self, transcript_data: List[Dict], 
                                        segment_length: float = 60.0,
                                        use_topic_detection: bool = True) -> List[TranscriptTimestamp]:
        """字幕から一定間隔でタイムスタンプを生成"""
        if not transcript_data:
            return []
        
        timestamps = []
        current_start = 0.0
        current_texts = []
        prev_text = ""
        
        for entry in transcript_data:
            start_time = entry.start
            text = entry.text.strip()
            duration = getattr(entry, 'duration', 3.0)
            
            should_break = False
            
            if use_topic_detection:
                # 話題転換を検出
                if self.detect_topic_transition(text, prev_text) and current_texts:
                    should_break = True
                # 最小時間制限（30秒以上）+ 最大時間制限（3分以下）
                elif (start_time - current_start >= 30.0 and 
                      start_time - current_start >= segment_length * 0.5 and current_texts):
                    should_break = True
                # 強制区切り（最大時間）
                elif start_time - current_start >= segment_length * 3 and current_texts:
                    should_break = True
            else:
                # 従来の固定時間区切り
                if start_time - current_start >= segment_length and current_texts:
                    should_break = True
            
            if should_break:
                # 現在のセグメントを確定
                combined_text = ' '.join(current_texts)
                confidence = self._calculate_text_confidence(combined_text)
                
                timestamps.append(TranscriptTimestamp(
                    start_time=current_start,
                    end_time=start_time,
                    text=self._clean_and_summarize_text(combined_text),
                    confidence=confidence
                ))
                
                # 新しいセグメント開始
                current_start = start_time
                current_texts = [text]
            else:
                current_texts.append(text)
            
            prev_text = text
        
        # 最後のセグメント
        if current_texts:
            end_time = transcript_data[-1].start + getattr(transcript_data[-1], 'duration', 3.0)
            combined_text = ' '.join(current_texts)
            
            timestamps.append(TranscriptTimestamp(
                start_time=current_start,
                end_time=end_time,
                text=self._clean_and_summarize_text(combined_text),
                confidence=self._calculate_text_confidence(combined_text)
            ))
        
        return timestamps
    
    def create_macro_summary(self, transcript_data: List[Dict], 
                           interval_minutes: float = 10.0) -> List[TranscriptTimestamp]:
        """10分間隔でマクロな概要を生成"""
        if not transcript_data:
            return []
        
        interval_seconds = interval_minutes * 60
        macro_timestamps = []
        current_start = 0.0
        segment_index = 0
        
        # 全体の長さを計算
        total_duration = transcript_data[-1].start + getattr(transcript_data[-1], 'duration', 3.0)
        
        while current_start < total_duration:
            end_time = min(current_start + interval_seconds, total_duration)
            
            # この区間のテキストを集める
            interval_texts = []
            for entry in transcript_data:
                if current_start <= entry.start < end_time:
                    interval_texts.append(entry.text.strip())
            
            if interval_texts:
                # 区間内の主要トピックを分析（セグメント番号も渡す）
                combined_text = ' '.join(interval_texts)
                summary = self._create_macro_topic_summary(combined_text, interval_minutes, segment_index)
                
                macro_timestamps.append(TranscriptTimestamp(
                    start_time=current_start,
                    end_time=end_time,
                    text=summary,
                    confidence=0.8
                ))
            
            current_start = end_time
            segment_index += 1
        
        return macro_timestamps
    
    def _create_macro_topic_summary(self, text: str, duration_minutes: float, segment_index: int = 0) -> str:
        """10分間のテキストからマクロな概要を生成（重複回避機能付き）"""
        
        # 具体的な内容やアクションを抽出
        content_patterns = {
            # 具体的な内容検出
            '配信開始・挨拶': [r'はじめ|スタート|開始|こんにちは|おはよう|始まり'],
            '記念話': [r'半年.*記念|デビュー.*半年|6.*月|6ヶ月'],
            '告知・イベント': [r'ぶいかふぇ|イベント|告知|お知らせ|企画'],
            '体調・調子': [r'体調|声.*調子|喉|疲れ|元気'],
            'BGM・音楽変更': [r'BGM.*変更|音楽.*変更|曲.*変更|メロディ'],
            '寝落ち・睡眠話': [r'寝落ち|眠い|寝る|睡眠|起きる'],
            'ゲーム話': [r'ゲーム|プレイ|遊び|レベル'],
            '12時間配信話': [r'12時間|長時間|マラソン配信'],
            '色紙企画': [r'色紙|企画|名前.*書|書く'],
            '日常・最近の話': [r'最近|今日|昨日|日常|普段'],
            '感謝・お礼': [r'ありがとう|感謝|お礼|嬉しい'],
            'リスナー交流': [r'初見|コメント.*読|名前.*呼|交流'],
            '配信環境・設定': [r'設定|環境|音量|画質|配信'],
        }
        
        # コンテンツ密度を測定
        content_scores = {}
        for category, patterns in content_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            if score > 0:
                content_scores[category] = score
        
        # 特定の時間帯による特徴を検出
        time_based_content = []
        if segment_index == 0:  # 開始10分
            time_based_content = ['配信開始・挨拶']
        elif segment_index <= 2:  # 最初の30分
            if '記念話' in content_scores:
                time_based_content = ['記念話・デビュー半年']
        elif segment_index >= 10:  # 1時間40分以降
            if '寝落ち・睡眠話' in content_scores:
                time_based_content = ['長時間配信・疲労話']
        
        # 実際のテキスト内容から具体的な内容を抽出
        specific_content = []
        
        # マシュマロやイベント告知
        if re.search(r'マシュマロ|ぶいかふぇ', text, re.IGNORECASE):
            specific_content.append('告知・イベント紹介')
        
        # 色紙企画について
        if re.search(r'色紙.*企画|名前.*書', text, re.IGNORECASE):
            specific_content.append('色紙企画・リスナー名前書き')
        
        # wiki言及
        if re.search(r'wiki|ウィキ', text, re.IGNORECASE):
            specific_content.append('非公式wiki紹介')
            
        # 初見歓迎
        if re.search(r'初見.*歓迎|はじめて.*方', text, re.IGNORECASE):
            specific_content.append('初見さん歓迎・交流')
            
        # 体調関連の具体的内容
        if re.search(r'声.*調子|喉.*痛|体調.*悪', text, re.IGNORECASE):
            specific_content.append('体調・声の調子について')
            
        # BGM変更や音楽関連
        if re.search(r'BGM.*変更|音楽.*変え|曲.*変', text, re.IGNORECASE):
            specific_content.append('BGM・音楽切り替え')
        elif re.search(r'BGM|音楽.*流|メロディ', text, re.IGNORECASE):
            specific_content.append('音楽・BGM話')
            
        # 配信時間・疲労
        if re.search(r'疲れ|長時間|12時間.*大変', text, re.IGNORECASE):
            specific_content.append('長時間配信の疲労話')
            
        # ゲーム関連
        if re.search(r'ゲーム.*話|プレイ.*話', text, re.IGNORECASE):
            specific_content.append('ゲームの話題')
            
        # 上位3つの具体的内容を選択
        final_content = []
        
        # 特定時間帯の内容を優先
        if time_based_content:
            final_content.extend(time_based_content[:1])
            
        # 具体的内容を追加
        if specific_content:
            remaining_slots = 2 - len(final_content)
            final_content.extend(specific_content[:remaining_slots])
            
        # まだ足りない場合は一般的なトピックから
        if len(final_content) < 2 and content_scores:
            remaining_slots = 2 - len(final_content)
            top_general = sorted(content_scores.items(), key=lambda x: x[1], reverse=True)
            for topic, score in top_general[:remaining_slots]:
                if topic not in final_content:
                    final_content.append(topic)
        
        # 結果生成（自然な文章形式で）
        if final_content:
            # 重複を除去
            unique_content = []
            for item in final_content:
                if item not in unique_content:
                    unique_content.append(item)
            
            # 自然な文章に変換
            return self._convert_to_natural_sentence(unique_content[:2])
        else:
            return f"通常の雑談と視聴者との交流"
    
    def _convert_to_natural_sentence(self, content_list: List[str]) -> str:
        """トピックリストを自然な文章に変換"""
        if not content_list:
            return "雑談と交流"
        
        # 各トピックを文章形式に変換
        sentence_parts = []
        
        for content in content_list:
            if content == '配信開始・挨拶':
                sentence_parts.append('配信開始の挨拶')
            elif content == '記念話・デビュー半年':
                sentence_parts.append('デビュー半年記念の話')
            elif content == '色紙企画・リスナー名前書き':
                sentence_parts.append('リスナーの名前を色紙に書く企画')
            elif content == '告知・イベント紹介':
                sentence_parts.append('イベントの告知・紹介')
            elif content == '長時間配信・疲労話':
                sentence_parts.append('長時間配信による疲労の話')
            elif content == 'BGM・音楽切り替え':
                sentence_parts.append('BGMや音楽の切り替え')
            elif content == '音楽・BGM話':
                sentence_parts.append('音楽やBGMについての話')
            elif content == 'ゲームの話題':
                sentence_parts.append('ゲームに関する話題')
            elif content == '体調・声の調子について':
                sentence_parts.append('体調や声の調子について')
            elif content == '配信環境・設定':
                sentence_parts.append('配信環境や設定の話')
            elif content == '初見さん歓迎・交流':
                sentence_parts.append('初見さんの歓迎と交流')
            elif content == '感謝・お礼':
                sentence_parts.append('視聴者への感謝とお礼')
            elif content == '日常・最近の話':
                sentence_parts.append('日常や最近の出来事')
            elif content == 'リスナー交流':
                sentence_parts.append('リスナーとの交流')
            elif content == '寝落ち・睡眠話':
                sentence_parts.append('寝落ちや睡眠の話')
            elif content == '12時間配信話':
                sentence_parts.append('12時間配信についての話')
            elif content == '長時間配信の疲労話':
                sentence_parts.append('長時間配信の疲労について')
            else:
                sentence_parts.append(content)
        
        # 文章を自然に組み合わせ
        if len(sentence_parts) == 1:
            return sentence_parts[0]
        elif len(sentence_parts) == 2:
            # 内容によって接続詞を変える
            first, second = sentence_parts[0], sentence_parts[1]
            
            # 同じカテゴリの場合
            if ('配信' in first and '配信' in second) or ('音楽' in first and '音楽' in second):
                return f"{first}と{second}"
            # 異なるアクティビティの場合
            elif any(x in first for x in ['企画', '告知', 'ゲーム']) and any(x in second for x in ['感謝', '交流', '話']):
                return f"{first}、{second}"
            # 一般的な組み合わせ
            else:
                return f"{first}、{second}"
        else:
            return '、'.join(sentence_parts[:2])
    
    def _clean_and_summarize_text(self, text: str, max_length: int = 80) -> str:
        """テキストをクリーニングして要約"""
        # HTMLタグ除去
        text = re.sub(r'<[^>]*>', '', text)
        
        # 連続する空白を1つに
        text = re.sub(r'\s+', ' ', text).strip()
        
        # インテリジェント要約を試行
        summary = self._create_smart_summary(text)
        if summary:
            return summary
        
        # 長すぎる場合は省略
        if len(text) > max_length:
            text = text[:max_length-3] + '...'
        
        return text
    
    def _create_smart_summary(self, text: str) -> str:
        """テキストからスマートな要約タイトルを生成"""
        # 短すぎる場合はそのまま
        if len(text) < 15:
            return text
        
        # まず重要な情報を抽出
        extracted_info = self._extract_meaningful_content(text)
        if extracted_info:
            return extracted_info
        
        # 文章の最初の部分を整形して使用
        cleaned_text = self._clean_sentence_for_title(text)
        if cleaned_text:
            return cleaned_text
        
        return None  # デフォルト処理にフォールバック
    
    def _extract_meaningful_content(self, text: str) -> str:
        """意味のある内容を抽出して文章化"""
        
        # 具体的な話題パターンを文章で抽出
        topic_extractions = [
            # 記念・お祝い関連
            (r'(?:半年|記念|おめでとう|デビュー)', lambda: self._extract_celebration_content(text)),
            
            # 配信時間・予定関連  
            (r'(?:12時間|時間|長時間|予定)', lambda: self._extract_schedule_content(text)),
            
            # 体調・声関連
            (r'(?:声|喉|体調|晴れない)', lambda: self._extract_health_content(text)),
            
            # BGM・音響関連
            (r'(?:BGM|音楽|音|歌|曲)', lambda: self._extract_audio_content(text)),
            
            # 寝落ち・睡眠関連
            (r'(?:寝落ち|寝る|睡眠)', lambda: self._extract_sleep_content(text)),
            
            # コメント・リスナー関連
            (r'(?:コメント|ありがとう|おめでとう)', lambda: self._extract_comment_content(text)),
            
            # ゲーム関連
            (r'(?:ゲーム|プレイ)', lambda: self._extract_game_content(text)),
        ]
        
        for pattern, extractor in topic_extractions:
            if re.search(pattern, text, re.IGNORECASE):
                result = extractor()
                if result:
                    return result
        
        return None
    
    def _extract_celebration_content(self, text: str) -> str:
        """お祝い関連の内容を抽出"""
        if 'デビュー' in text and '半年' in text:
            return "デビュー半年おめでとうのコメントについて"
        elif '半年' in text and '記念' in text:
            return "半年記念配信についての話"
        elif 'おめでとう' in text:
            return "お祝いコメントへの返答"
        return None
    
    def _extract_schedule_content(self, text: str) -> str:
        """配信時間・予定関連の内容を抽出"""
        time_match = re.search(r'(\d+)時間', text)
        if time_match:
            hours = time_match.group(1)
            return f"{hours}時間配信についての説明"
        elif '予定' in text and '告知' in text:
            return "配信予定の告知"
        elif '長時間' in text:
            return "長時間配信についての話"
        return None
    
    def _extract_health_content(self, text: str) -> str:
        """体調・声関連の内容を抽出"""
        if '声' in text and '晴れない' in text:
            return "夜配信で声が晴れないことについて"
        elif '声' in text and '夜' in text:
            return "夜の配信での声の調子について"
        elif '体調' in text:
            return "体調についての話"
        return None
    
    def _extract_audio_content(self, text: str) -> str:
        """BGM・音響関連の内容を抽出"""
        # より具体的な音楽・BGM関連の分析
        if 'BGM' in text:
            if '変え' in text or '変更' in text:
                return "BGM変更についての話"
            elif 'リクエスト' in text:
                return "BGMリクエストについて"
            elif '音量' in text or 'ボリューム' in text:
                return "BGM音量調整について"
            elif '好き' in text or '気に入' in text:
                return "BGMの感想・評価"
            elif '何' in text and ('曲' in text or '音楽' in text):
                return "BGMの楽曲について"
            else:
                return "BGMについての話"
        
        elif '音楽' in text:
            if '聞く' in text or '聴く' in text:
                return "音楽鑑賞について"
            elif '歌' in text:
                return "歌・音楽についての話"
            elif 'ジャンル' in text:
                return "音楽ジャンルについて"
            elif '好き' in text:
                return "好きな音楽について"
            else:
                return "音楽全般の話"
        
        elif '歌' in text:
            if 'リクエスト' in text:
                return "歌のリクエストについて"
            elif '歌う' in text or 'うた' in text:
                return "歌配信についての話"
            elif '上手' in text or '下手' in text:
                return "歌の上手さについて"
            else:
                return "歌についての話"
        
        elif '曲' in text:
            if 'リクエスト' in text:
                return "楽曲リクエストについて"
            elif '何' in text and ('曲' in text):
                return "楽曲選択について"
            elif '好き' in text:
                return "好きな楽曲について"
            else:
                return "楽曲についての話"
        
        return None
    
    def _extract_sleep_content(self, text: str) -> str:
        """寝落ち・睡眠関連の内容を抽出"""
        if '寝落ち' in text and '予定' in text:
            return "寝落ち予定についての話"
        elif '寝落ち' in text and ('リスナー' in text or 'みんな' in text):
            return "視聴者の寝落ちについて"
        elif '寝る' in text and '時' in text:
            return "就寝時間についての話"
        return None
    
    def _extract_comment_content(self, text: str) -> str:
        """コメント関連の内容を抽出"""
        # 人名を抽出
        name_match = re.search(r'([ァ-ヶーぁ-んa-zA-Z0-9_]+)さん', text)
        if name_match:
            name = name_match.group(1)
            if 'ありがとう' in text:
                return f"{name}さんへのお礼"
            elif 'おめでとう' in text:
                return f"{name}さんからのお祝いコメント"
            else:
                return f"{name}さんへの返答"
        
        # 一般的なコメント内容
        if 'おめでとう' in text and 'ありがとう' in text:
            return "お祝いコメントへのお礼"
        elif 'コメント' in text and 'ありがとう' in text:
            return "コメントへのお礼"
        return None
    
    def _extract_game_content(self, text: str) -> str:
        """ゲーム関連の内容を抽出"""
        game_match = re.search(r'[ァ-ヶー]{3,10}', text)
        if game_match:
            game_name = game_match.group(0)
            return f"{game_name}について"
        elif 'ゲーム' in text and 'プレイ' in text:
            return "ゲームプレイについて"
        return None
    
    def _clean_sentence_for_title(self, text: str) -> str:
        """文章を整形してタイトル化"""
        # 最初の意味のある文を抽出
        sentences = re.split(r'[。！？]', text)
        
        for sentence in sentences[:2]:  # 最初の2文を確認
            sentence = sentence.strip()
            if len(sentence) < 10:  # 短すぎる文はスキップ
                continue
            if len(sentence) > 60:  # 長すぎる場合は切り詰め
                sentence = sentence[:57] + "..."
            
            # 無意味な文章をフィルタリング
            if self._is_meaningful_sentence(sentence):
                return sentence
        
        return None
    
    def _is_meaningful_sentence(self, sentence: str) -> bool:
        """意味のある文章かどうか判定"""
        # 短すぎるものを除外
        if len(sentence) < 5:
            return False
        
        # 意味のないパターンを除外
        meaningless_patterns = [
            r'^[あーえーうーんー]+$',  # 「あー」だけなど
            r'^[はいそうですね]+$',    # 「はい」「そう」だけ
            r'^[wwwW\.]+$',          # 笑いだけ
        ]
        
        for pattern in meaningless_patterns:
            if re.match(pattern, sentence):
                return False
        
        return True
    
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """重要なフレーズを抽出"""
        # 名詞句っぽいパターンを抽出
        phrases = []
        
        # カタカナ語（ゲーム名、専門用語など）
        katakana_words = re.findall(r'[ァ-ヶー]{2,8}', text)
        phrases.extend(katakana_words[:2])
        
        # 「〜する」「〜やる」などの動作
        action_patterns = [
            r'([ぁ-ん]{2,6})(?:する|やる|行く)',
            r'([ぁ-ん]{2,6})(?:します|やります)',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            phrases.extend(matches[:1])
        
        # 重複除去
        return list(dict.fromkeys(phrases))  # 順序を保持して重複除去
    
    def _calculate_text_confidence(self, text: str) -> float:
        """テキストの信頼度を計算（簡易版）"""
        confidence = 0.5  # ベース信頼度
        
        # 文章の完成度をチェック
        if '。' in text or '!' in text or '?' in text:
            confidence += 0.2
        
        # 長さをチェック
        if 10 <= len(text) <= 100:
            confidence += 0.2
        
        # 特定の話題キーワードがあるかチェック
        topic_keywords = ['ゲーム', '歌', '音楽', '質問', 'コメント', '配信', '今日', '次']
        for keyword in topic_keywords:
            if keyword in text:
                confidence += 0.1
                break
        
        return min(confidence, 1.0)
    
    def detect_topic_transition(self, text: str, prev_text: str = "") -> bool:
        """話題転換を検出"""
        # 話題転換キーワード
        transition_keywords = [
            "さて", "それでは", "次に", "続いて", "ところで", "そういえば",
            "話は変わって", "話変わるけど", "別の話", "そうそう",
            "今度は", "今回は", "最初に", "最後に", "終わりに",
            "質問", "コメント", "リクエスト", "次の曲", "1曲目", "2曲目",
            "ゲーム", "プレイ", "レベル", "ステージ"
        ]
        
        # 強い転換パターン
        strong_patterns = [
            r"それでは.*?(?:行|い)きます",
            r"次.*?(?:行|い)きます", 
            r"(?:さて|では).*?(?:始|はじ)め",
            r"(?:今度|今回).*?(?:やり|する)",
            r"(?:最初|まず).*?(?:から|は)",
            r"(?:続い|つづい)て.*?(?:は|を)",
            r"\d+(?:曲目|番目|つ目)",
        ]
        
        # 強いパターンをチェック
        for pattern in strong_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # キーワードをチェック
        for keyword in transition_keywords:
            if keyword in text:
                return True
        
        return False
    
    def save_timestamps_csv(self, timestamps: List[TranscriptTimestamp], 
                           video_id: str, video_title: str = "") -> str:
        """タイムスタンプをCSVに保存"""
        filename = f"transcript_timestamps_{video_id}.csv"
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "No", "開始時間", "終了時間", "長さ(分)", "内容", 
                "信頼度", "YouTubeリンク"
            ])
            
            for i, ts in enumerate(timestamps, 1):
                duration_minutes = (ts.end_time - ts.start_time) / 60
                youtube_url = f"https://www.youtube.com/watch?v={video_id}&{ts.youtube_url_param}"
                
                writer.writerow([
                    i,
                    ts.timestamp_text,
                    ts._seconds_to_timestamp(ts.end_time),
                    f"{duration_minutes:.1f}",
                    ts.text,
                    f"{ts.confidence:.2f}",
                    youtube_url
                ])
        
        print(f"タイムスタンプをCSVに保存: {filename}")
        return filename
    
    def save_macro_summary_csv(self, macro_summary: List[TranscriptTimestamp], 
                              video_id: str, video_title: str = "") -> str:
        """マクロ概要をCSVに保存"""
        filename = f"macro_summary_{video_id}.csv"
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "No", "開始時間", "終了時間", "長さ(分)", "概要", 
                "信頼度", "YouTubeリンク"
            ])
            
            for i, macro in enumerate(macro_summary, 1):
                duration_minutes = (macro.end_time - macro.start_time) / 60
                youtube_url = f"https://www.youtube.com/watch?v={video_id}&{macro.youtube_url_param}"
                
                writer.writerow([
                    i,
                    macro.timestamp_text,
                    macro._seconds_to_timestamp(macro.end_time),
                    f"{duration_minutes:.0f}",
                    macro.text,
                    f"{macro.confidence:.2f}",
                    youtube_url
                ])
        
        print(f"マクロ概要をCSVに保存: {filename}")
        return filename
    
    def save_chat_csv(self, chat_messages: List[LiveChatMessage], 
                     video_id: str) -> str:
        """チャットメッセージをCSVに保存"""
        filename = f"live_chat_{video_id}.csv"
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "No", "時刻", "投稿者", "メッセージ", "動画時間(秒)"
            ])
            
            for i, msg in enumerate(chat_messages, 1):
                writer.writerow([
                    i,
                    msg.timestamp,
                    msg.author,
                    msg.message,
                    f"{msg.video_offset:.1f}"
                ])
        
        print(f"ライブチャットをCSVに保存: {filename}")
        return filename
    
    def extract_video_timestamps(self, video_id: str):
        """メイン実行関数"""
        print(f"\n動画ID: {video_id}")
        print("="*60)
        
        # 1. 動画情報取得
        video_info = self.get_video_info(video_id)
        if not video_info:
            return
        
        title = video_info['snippet']['title']
        print(f"タイトル: {title}")
        
        # ライブ配信かどうか判定
        live_details = video_info.get('liveStreamingDetails', {})
        is_live = bool(live_details)
        print(f"ライブ配信: {'はい' if is_live else 'いいえ'}")
        
        # 2. 字幕からタイムスタンプ生成
        transcript_data = self.get_transcript(video_id)
        timestamps = []
        
        if transcript_data:
            # 話題検出を使うかユーザーに選択させる
            use_topic = input("\n話題で区切りますか？ (Y/n): ").strip().lower() != 'n'
            
            if use_topic:
                print("話題転換を検出してタイムスタンプを生成中...")
                timestamps = self.create_timestamps_from_transcript(
                    transcript_data, segment_length=120.0, use_topic_detection=True
                )
            else:
                print("60秒間隔でタイムスタンプを生成中...")
                timestamps = self.create_timestamps_from_transcript(
                    transcript_data, segment_length=60.0, use_topic_detection=False
                )
            
            # マクロな概要も生成
            print("10分間隔の概要を生成中...")
            macro_summary = self.create_macro_summary(transcript_data)
            print(f"生成されたタイムスタンプ: {len(timestamps)}個")
            
            # 結果表示
            print(f"\nタイムスタンプ一覧:")
            print("-" * 60)
            for i, ts in enumerate(timestamps[:10], 1):  # 最初の10個を表示
                duration = (ts.end_time - ts.start_time) / 60
                print(f"{i:2d}. {ts.timestamp_text} ({duration:.1f}分) {ts.text}")
            
            if len(timestamps) > 10:
                print(f"    ... 他 {len(timestamps) - 10} 個")
        
        # 3. ライブチャット取得（ライブ配信の場合）
        chat_messages = []
        if is_live:
            chat_messages = self.get_live_chat_messages(video_id)
        
        # 4. 保存
        if timestamps:
            self.save_timestamps_csv(timestamps, video_id, title)
        
        if 'macro_summary' in locals() and macro_summary:
            self.save_macro_summary_csv(macro_summary, video_id, title)
            
            # マクロ概要を表示
            print(f"\n10分間隔の概要:")
            print("-" * 60)
            for i, macro in enumerate(macro_summary, 1):
                duration = (macro.end_time - macro.start_time) / 60
                print(f"{i:2d}. {macro.timestamp_text} ({duration:.0f}分) {macro.text}")
        
        if chat_messages:
            self.save_chat_csv(chat_messages, video_id)
        
        # 5. 結果サマリー
        print(f"\n完了!")
        print(f"   詳細タイムスタンプ: {len(timestamps)}個")
        if 'macro_summary' in locals() and macro_summary:
            print(f"   10分間隔の概要: {len(macro_summary)}個")
        print(f"   ライブチャット: {len(chat_messages)}件")
        
        return {
            'timestamps': timestamps,
            'macro_summary': macro_summary if 'macro_summary' in locals() else [],
            'chat_messages': chat_messages,
            'video_info': video_info
        }

def extract_video_id(video_input: str) -> Optional[str]:
    """動画URLまたはIDから動画IDを抽出"""
    video_input = video_input.strip()
    
    # 既に動画IDの形式の場合
    if len(video_input) == 11 and re.match(r'^[a-zA-Z0-9_-]+$', video_input):
        return video_input
    
    # YouTube URLの場合
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'[?&]v=([a-zA-Z0-9_-]{11})',
        r'/([a-zA-Z0-9_-]{11})(?:\?|&|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_input)
        if match:
            return match.group(1)
    
    return None

def main():
    """メイン関数"""
    try:
        extractor = LiveTranscriptExtractor()
        
        # 動画URL/ID入力
        video_input = input("動画URLまたは動画IDを入力してください: ").strip()
        
        # 動画IDを抽出
        video_id = extract_video_id(video_input)
        if not video_id:
            print("無効な動画URLまたはIDです")
            return
        
        # 実行
        extractor.extract_video_timestamps(video_id)
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()