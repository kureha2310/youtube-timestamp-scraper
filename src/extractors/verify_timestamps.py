"""
タイムスタンプ抽出漏れ検証ツール
CSVファイルと元の動画データを比較して、抽出漏れを検出する
"""
import json
import os
import re
import csv
from typing import List, Set, Tuple
from dotenv import load_dotenv
from googleapiclient import discovery

# 親ディレクトリをパスに追加
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.infoclass import VideoInfo, CommentInfo

load_dotenv()
API_KEY = os.getenv('API_KEY')
youtube = discovery.build('youtube', 'v3', developerKey=API_KEY)

def extract_all_raw_timestamps(text: str) -> List[Tuple[str, str]]:
    """
    テキストから全てのタイムスタンプを生抽出（フィルタリングなし）
    Returns: [(timestamp, content), ...]
    """
    results = []

    # 複数のパターンで抽出
    patterns = [
        # 基本パターン
        r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:：・･]\s*(.+?)(?=\n|\d{1,2}:\d{2}|$)',
        # 括弧パターン
        r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[）)]\s*(.+?)(?=\n|$)',
        # スペース区切り
        r'(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)(?=\n|\d{1,2}:\d{2}|$)',
        # スラッシュ区切り
        r'(\d{1,2}:\d{2}(?::\d{2})?)\s*/\s*(.+?)(?=\n|$)',
        # HTMLアンカー
        r'<a[^>]*>(\d{1,2}:\d{2}(?::\d{2})?)</a>\s*([^<\n]+)',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
        for match in matches:
            timestamp = match.group(1)
            content = match.group(2).strip()

            # 最低限のフィルタリング（空文字、URL、明らかなゴミ）
            if content and len(content) > 0:
                if not re.search(r'^https?://', content):
                    if not re.match(r'^[\s\d:]+$', content):
                        results.append((timestamp, content))

    return results

def normalize_timestamp(ts: str) -> str:
    """タイムスタンプを正規化（秒数に変換）"""
    parts = ts.split(':')
    try:
        if len(parts) == 2:  # mm:ss
            return str(int(parts[0]) * 60 + int(parts[1]))
        elif len(parts) == 3:  # hh:mm:ss
            return str(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
    except:
        return ts
    return ts

def load_csv_timestamps(csv_path: str) -> Set[Tuple[str, str]]:
    """CSVファイルからタイムスタンプを読み込む"""
    timestamps = set()

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                video_id = row.get('動画ID', '')
                timestamp = row.get('タイムスタンプ', '')
                if video_id and timestamp:
                    # 秒数に正規化
                    normalized = normalize_timestamp(timestamp)
                    timestamps.add((video_id, normalized))
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {e}")

    return timestamps

def get_video_description(video_id: str) -> str:
    """動画の概要欄を取得"""
    try:
        response = youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()

        if response.get('items'):
            return response['items'][0]['snippet'].get('description', '')
    except Exception as e:
        print(f"動画 {video_id} の概要欄取得エラー: {e}")

    return ""

def get_video_comments(video_id: str) -> List[str]:
    """動画のコメントを取得"""
    comments = []

    try:
        request = youtube.commentThreads().list(
            part='snippet,replies',
            maxResults=100,
            videoId=video_id
        )

        while request:
            response = request.execute()

            for item in response.get('items', []):
                # トップレベルコメント
                top_comment = item['snippet']['topLevelComment']['snippet']
                comments.append(top_comment['textDisplay'])

                # 返信コメント
                if 'replies' in item:
                    for reply in item['replies']['comments']:
                        comments.append(reply['snippet']['textDisplay'])

            request = youtube.commentThreads().list_next(request, response)
    except Exception as e:
        print(f"動画 {video_id} のコメント取得エラー: {e}")

    return comments

def verify_timestamps(csv_path: str = 'song_timestamps_complete.csv'):
    """タイムスタンプの抽出漏れを検証"""
    print("=" * 80)
    print("タイムスタンプ抽出漏れ検証ツール")
    print("=" * 80)

    # 1. CSVから既存のタイムスタンプを読み込む
    print("\n1. CSVファイルを読み込み中...")
    csv_timestamps = load_csv_timestamps(csv_path)
    print(f"   CSVに記録されているタイムスタンプ: {len(csv_timestamps)}件")

    # 2. CSVから動画IDのリストを取得
    video_ids = set()
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                video_id = row.get('動画ID', '')
                if video_id:
                    video_ids.add(video_id)
    except Exception as e:
        print(f"エラー: {e}")
        return

    print(f"   対象動画数: {len(video_ids)}件")

    # 3. 各動画について検証
    print("\n2. 各動画のタイムスタンプを検証中...")

    all_missing = []

    for i, video_id in enumerate(sorted(video_ids), 1):
        print(f"\n   [{i}/{len(video_ids)}] 動画ID: {video_id}")

        # 概要欄とコメントを取得
        description = get_video_description(video_id)
        comments = get_video_comments(video_id)

        # タイムスタンプを生抽出
        raw_timestamps_desc = extract_all_raw_timestamps(description)
        raw_timestamps_comments = []

        for comment in comments:
            raw_timestamps_comments.extend(extract_all_raw_timestamps(comment))

        all_raw = raw_timestamps_desc + raw_timestamps_comments

        print(f"      概要欄: {len(raw_timestamps_desc)}件")
        print(f"      コメント: {len(raw_timestamps_comments)}件")
        print(f"      合計: {len(all_raw)}件")

        # CSVと比較して漏れを検出
        missing = []
        for ts, content in all_raw:
            normalized_ts = normalize_timestamp(ts)

            if (video_id, normalized_ts) not in csv_timestamps:
                # 5秒以内の近似も許容
                found = False
                ts_int = int(normalized_ts)
                for offset in range(-5, 6):
                    if (video_id, str(ts_int + offset)) in csv_timestamps:
                        found = True
                        break

                if not found:
                    missing.append((ts, content))

        if missing:
            print(f"      [!] 抽出漏れ: {len(missing)}件")
            all_missing.extend([(video_id, ts, content) for ts, content in missing])

            # 最初の5件を表示
            for ts, content in missing[:5]:
                try:
                    # エンコードエラーを避けるため、安全に表示
                    safe_content = content[:50].encode('cp932', errors='ignore').decode('cp932')
                    print(f"         - {ts} {safe_content}...")
                except:
                    print(f"         - {ts} [表示不可]...")

            if len(missing) > 5:
                print(f"         ... 他{len(missing) - 5}件")
        else:
            print(f"      [OK] 抽出漏れなし")

    # 4. レポート出力
    print("\n" + "=" * 80)
    print("検証結果サマリー")
    print("=" * 80)
    print(f"CSVに記録されたタイムスタンプ: {len(csv_timestamps)}件")
    print(f"検出された抽出漏れ: {len(all_missing)}件")

    if all_missing:
        print("\n抽出漏れの詳細を missing_timestamps.csv に出力します...")

        with open('missing_timestamps.csv', 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['動画ID', 'タイムスタンプ', '内容'])

            for video_id, ts, content in all_missing:
                writer.writerow([video_id, ts, content])

        print("[OK] missing_timestamps.csv を作成しました")

        # 動画IDごとの統計
        print("\n動画別の抽出漏れ:")
        video_missing_counts = {}
        for video_id, ts, content in all_missing:
            video_missing_counts[video_id] = video_missing_counts.get(video_id, 0) + 1

        for video_id, count in sorted(video_missing_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {video_id}: {count}件")
    else:
        print("\n[OK] 抽出漏れは検出されませんでした！")

if __name__ == "__main__":
    verify_timestamps()
