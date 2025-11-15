#!/usr/bin/env python3
"""
YouTubeチャンネルから特定文字列を検索するスクリプト
コメント、字幕、ライブチャットから検索してタイミングをまとめる
"""

import json
import os
import csv
import time
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPT_AVAILABLE = True
except ImportError:
    print("[!] youtube-transcript-api が見つかりません。字幕検索には必要です。")
    print("    インストール: pip install youtube-transcript-api")
    TRANSCRIPT_AVAILABLE = False

try:
    from chat_downloader import ChatDownloader
    CHAT_DOWNLOADER_AVAILABLE = True
except ImportError:
    print("[!] chat-downloader が見つかりません。ライブチャット検索には必要です。")
    print("    インストール: pip install chat-downloader")
    CHAT_DOWNLOADER_AVAILABLE = False


@dataclass
class SearchResult:
    """検索結果データクラス"""
    video_id: str
    video_title: str
    published_at: str
    source_type: str  # 'comment', 'transcript', 'live_chat'
    timestamp: str  # 動画内のタイムスタンプ
    matched_text: str
    context: str  # 前後のテキスト
    video_url: str


class TextSearchExtractor:
    """チャンネルから特定文字列を検索"""

    def __init__(self):
        """初期化"""
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise RuntimeError(".envファイルにAPI_KEYが設定されていません")

        self.youtube = discovery.build('youtube', 'v3', developerKey=self.api_key)
        self.results: List[SearchResult] = []

    def get_channel_videos(self, channel_id: str, max_videos: int = 50) -> List[Dict]:
        """チャンネルの動画一覧を取得"""
        print(f"\n[*] チャンネルの動画を取得中: {channel_id}")

        videos = []

        try:
            # チャンネルのアップロードプレイリストIDを取得
            channel_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()

            if not channel_response.get('items'):
                print(f"[!] チャンネルが見つかりません: {channel_id}")
                return []

            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # プレイリストから動画を取得
            next_page_token = None

            while len(videos) < max_videos:
                playlist_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_videos - len(videos)),
                    pageToken=next_page_token
                ).execute()

                for item in playlist_response.get('items', []):
                    snippet = item['snippet']
                    videos.append({
                        'video_id': snippet['resourceId']['videoId'],
                        'title': snippet['title'],
                        'published_at': snippet['publishedAt']
                    })

                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break

                time.sleep(0.5)  # API制限対策

            print(f"[OK] {len(videos)}件の動画を取得しました")
            return videos

        except HttpError as e:
            print(f"[!] API エラー: {e}")
            return []
        except Exception as e:
            print(f"[!] エラー: {e}")
            return []

    def search_in_comments(self, video_id: str, video_title: str, published_at: str,
                          search_text: str, max_comments: int = 100) -> List[SearchResult]:
        """コメント内を検索"""
        results = []
        search_lower = search_text.lower()

        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_comments, 100),
                textFormat="plainText"
            )

            while request and len(results) < max_comments:
                response = request.execute()

                for item in response.get('items', []):
                    comment = item['snippet']['topLevelComment']['snippet']
                    text = comment['textDisplay']

                    # 検索文字列が含まれているかチェック
                    if search_lower in text.lower():
                        # タイムスタンプを探す
                        timestamp = self._extract_timestamp_from_text(text)

                        results.append(SearchResult(
                            video_id=video_id,
                            video_title=video_title,
                            published_at=published_at,
                            source_type='comment',
                            timestamp=timestamp or '0:00',
                            matched_text=search_text,
                            context=text[:200],  # 最初の200文字
                            video_url=f"https://www.youtube.com/watch?v={video_id}" +
                                     (f"&t={self._timestamp_to_seconds(timestamp)}" if timestamp else "")
                        ))

                request = self.youtube.commentThreads().list_next(request, response)
                time.sleep(0.3)

        except HttpError as e:
            if e.resp.status == 403:
                pass  # コメント無効
            else:
                print(f"[!] コメント取得エラー ({video_id}): {e}")
        except Exception as e:
            print(f"[!] エラー ({video_id}): {e}")

        return results

    def search_in_transcript(self, video_id: str, video_title: str, published_at: str,
                            search_text: str) -> List[SearchResult]:
        """字幕内を検索"""
        if not TRANSCRIPT_AVAILABLE:
            return []

        results = []
        search_lower = search_text.lower()

        try:
            # 字幕を取得
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # 日本語優先で取得
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['ja', 'en'])
            except:
                transcript = transcript_list.find_generated_transcript(['ja', 'en'])

            if not transcript:
                return []

            transcript_data = transcript.fetch()

            # 検索
            for entry in transcript_data:
                text = entry.get('text', '')

                if search_lower in text.lower():
                    start_time = entry.get('start', 0)
                    timestamp = self._seconds_to_timestamp(start_time)

                    results.append(SearchResult(
                        video_id=video_id,
                        video_title=video_title,
                        published_at=published_at,
                        source_type='transcript',
                        timestamp=timestamp,
                        matched_text=search_text,
                        context=text,
                        video_url=f"https://www.youtube.com/watch?v={video_id}&t={int(start_time)}"
                    ))

        except Exception as e:
            # 字幕が無い動画は多いので、エラーは表示しない
            pass

        return results

    def search_in_live_chat(self, video_id: str, video_title: str, published_at: str,
                           search_text: str) -> List[SearchResult]:
        """ライブチャット内を検索（アーカイブされたチャット）"""
        if not CHAT_DOWNLOADER_AVAILABLE:
            return []

        results = []
        search_lower = search_text.lower()

        try:
            # ChatDownloaderを使用してチャットを取得
            url = f"https://www.youtube.com/watch?v={video_id}"
            chat = ChatDownloader().get_chat(url)

            # チャットメッセージを検索
            for message in chat:
                # メッセージテキストを取得
                text = message.get('message', '')

                if not text:
                    continue

                # 検索文字列が含まれているかチェック
                if search_lower in text.lower():
                    # タイムスタンプを取得（秒単位）
                    time_in_seconds = message.get('time_in_seconds', 0)
                    timestamp = self._seconds_to_timestamp(time_in_seconds)

                    results.append(SearchResult(
                        video_id=video_id,
                        video_title=video_title,
                        published_at=published_at,
                        source_type='live_chat',
                        timestamp=timestamp,
                        matched_text=search_text,
                        context=text[:200],  # 最初の200文字
                        video_url=f"https://www.youtube.com/watch?v={video_id}&t={int(time_in_seconds)}"
                    ))

        except Exception as e:
            # チャットが無い動画やエラーは静かに無視
            pass

        return results

    def search_channel(self, channel_id: str, search_text: str,
                      search_comments: bool = True,
                      search_transcripts: bool = True,
                      search_live_chat: bool = False,
                      max_videos: int = 50) -> List[SearchResult]:
        """チャンネル全体を検索"""
        print(f"\n{'='*70}")
        print(f"[*] 検索開始")
        print(f"    チャンネルID: {channel_id}")
        print(f"    検索文字列: {search_text}")
        print(f"    検索対象: ", end='')
        search_targets = []
        if search_comments:
            search_targets.append("コメント")
        if search_transcripts:
            search_targets.append("字幕")
        if search_live_chat:
            search_targets.append("ライブチャット")
        print(", ".join(search_targets))
        print(f"{'='*70}\n")

        # 動画一覧を取得
        videos = self.get_channel_videos(channel_id, max_videos)

        if not videos:
            print("[!] 動画が見つかりませんでした")
            return []

        all_results = []

        # 各動画を検索
        for i, video in enumerate(videos, 1):
            video_id = video['video_id']
            video_title = video['title']
            published_at = video['published_at']

            # エンコーディングエラーを回避
            try:
                safe_title = video_title[:50].encode('cp932', errors='ignore').decode('cp932')
            except:
                safe_title = video_id

            print(f"\r[{i}/{len(videos)}] {safe_title}...", end='', flush=True)

            # コメント検索
            if search_comments:
                comment_results = self.search_in_comments(
                    video_id, video_title, published_at, search_text
                )
                all_results.extend(comment_results)

            # 字幕検索
            if search_transcripts:
                transcript_results = self.search_in_transcript(
                    video_id, video_title, published_at, search_text
                )
                all_results.extend(transcript_results)

            # ライブチャット検索
            if search_live_chat:
                live_chat_results = self.search_in_live_chat(
                    video_id, video_title, published_at, search_text
                )
                all_results.extend(live_chat_results)

            time.sleep(0.5)  # API制限対策

        print(f"\n\n[OK] 検索完了: {len(all_results)}件のヒット")

        return all_results

    def save_to_csv(self, results: List[SearchResult], filename: str = None):
        """結果をCSVに保存"""
        if not results:
            print("[!] 保存する結果がありません")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_results_{timestamp}.csv"

        # outputディレクトリに保存
        output_dir = os.path.join('output', 'csv')
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        print(f"\n[*] CSV保存中: {filepath}")

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow([
                'No', '動画タイトル', '動画ID', '公開日',
                '検索元', 'タイムスタンプ', '検索文字列',
                'コンテキスト', '動画URL'
            ])

            # データ
            for i, result in enumerate(results, 1):
                # 日付をJSTに変換
                try:
                    dt = datetime.fromisoformat(result.published_at.replace('Z', '+00:00'))
                    date_str = dt.astimezone(timezone(timedelta(hours=9))).strftime('%Y/%m/%d')
                except:
                    date_str = result.published_at

                # 検索元の日本語化
                source_map = {
                    'comment': 'コメント',
                    'transcript': '字幕',
                    'live_chat': 'ライブチャット'
                }
                source_jp = source_map.get(result.source_type, result.source_type)

                writer.writerow([
                    i,
                    result.video_title,
                    result.video_id,
                    date_str,
                    source_jp,
                    result.timestamp,
                    result.matched_text,
                    result.context[:100],  # コンテキストは最初の100文字
                    result.video_url
                ])

        print(f"[OK] {len(results)}件を保存しました")
        print(f"     ファイル: {filepath}")

        # 統計表示
        self._print_statistics(results)

    def _print_statistics(self, results: List[SearchResult]):
        """統計情報を表示"""
        print(f"\n{'='*70}")
        print(f"[*] 検索結果統計")
        print(f"{'='*70}")

        # 検索元別
        source_counts = {}
        for result in results:
            source_counts[result.source_type] = source_counts.get(result.source_type, 0) + 1

        source_map = {
            'comment': 'コメント',
            'transcript': '字幕',
            'live_chat': 'ライブチャット'
        }

        print("\n検索元別:")
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            source_jp = source_map.get(source, source)
            print(f"   {source_jp}: {count}件")

        # 動画別
        video_counts = {}
        for result in results:
            video_counts[result.video_id] = video_counts.get(result.video_id, 0) + 1

        print(f"\n動画別ヒット数 (上位5件):")
        sorted_videos = sorted(video_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for video_id, count in sorted_videos:
            # タイトルを取得
            title = next((r.video_title for r in results if r.video_id == video_id), video_id)
            print(f"   {title[:50]}... ({count}件)")

        print(f"{'='*70}\n")

    def _extract_timestamp_from_text(self, text: str) -> Optional[str]:
        """テキストからタイムスタンプを抽出"""
        # タイムスタンプパターン: MM:SS または HH:MM:SS
        patterns = [
            r'(\d{1,2}:\d{2}:\d{2})',  # HH:MM:SS
            r'(\d{1,2}:\d{2})',        # MM:SS
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _timestamp_to_seconds(self, timestamp: str) -> int:
        """タイムスタンプを秒数に変換"""
        if not timestamp:
            return 0

        parts = timestamp.split(':')
        try:
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass

        return 0

    def _seconds_to_timestamp(self, seconds: float) -> str:
        """秒数をタイムスタンプに変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"


def main():
    """メイン実行関数"""
    print("\n" + "="*70)
    print("YouTube チャンネル内 文字列検索ツール")
    print("="*70 + "\n")

    try:
        extractor = TextSearchExtractor()

        # チャンネルID入力
        print("チャンネルIDを入力してください:")
        channel_id = input("> ").strip()

        if not channel_id:
            print("[!] チャンネルIDが入力されていません")
            return

        # 検索文字列入力
        print("\n検索する文字列を入力してください:")
        search_text = input("> ").strip()

        if not search_text:
            print("[!] 検索文字列が入力されていません")
            return

        # 検索対象選択
        print("\n検索対象を選択してください:")
        print("1. コメント")
        print("2. 字幕")
        print("3. コメント + 字幕")
        print("4. すべて (コメント + 字幕 + ライブチャット)")

        choice = input("> ").strip()

        search_comments = choice in ['1', '3', '4']
        search_transcripts = choice in ['2', '3', '4']
        search_live_chat = choice == '4'

        # 検索する動画数
        print("\n検索する動画数を入力してください (デフォルト: 50):")
        max_videos_input = input("> ").strip()
        max_videos = int(max_videos_input) if max_videos_input else 50

        # 検索実行
        results = extractor.search_channel(
            channel_id=channel_id,
            search_text=search_text,
            search_comments=search_comments,
            search_transcripts=search_transcripts,
            search_live_chat=search_live_chat,
            max_videos=max_videos
        )

        # 結果保存
        if results:
            extractor.save_to_csv(results)

            # 結果をプレビュー表示
            print("\n[*] 検索結果プレビュー (最初の5件):")
            print("-" * 70)
            for i, result in enumerate(results[:5], 1):
                print(f"\n{i}. {result.video_title}")
                print(f"   検索元: {result.source_type} | タイムスタンプ: {result.timestamp}")
                print(f"   コンテキスト: {result.context[:80]}...")
                print(f"   URL: {result.video_url}")
        else:
            print("\n[!] 該当する結果が見つかりませんでした")

    except KeyboardInterrupt:
        print("\n\n[!] 中断されました")
    except Exception as e:
        print(f"\n[!] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
