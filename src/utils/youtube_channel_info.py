#!/usr/bin/env python3
"""
YouTubeチャンネル情報取得モジュール
YouTube Data API v3を使用してチャンネル情報（名前、サムネイル等）を取得
"""

import os
from typing import Dict, Optional, List
from googleapiclient import discovery
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')

if not API_KEY:
    raise RuntimeError("`.env` に API_KEY がありません。YouTube Data API v3 のAPIキーを設定してください。")

youtube = discovery.build('youtube', 'v3', developerKey=API_KEY)


def get_channel_info(channel_id: str) -> Optional[Dict[str, str]]:
    """
    チャンネルIDから詳細情報を取得

    Args:
        channel_id: YouTubeチャンネルID

    Returns:
        Dict: チャンネル情報 {
            'id': チャンネルID,
            'title': チャンネル名,
            'thumbnail': サムネイルURL (高解像度),
            'description': チャンネル説明,
            'subscriber_count': 登録者数
        }
        取得失敗時はNone
    """
    try:
        request = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        )
        response = request.execute()

        if not response.get('items'):
            print(f"[!] チャンネルID {channel_id} が見つかりません")
            return None

        channel = response['items'][0]
        snippet = channel['snippet']
        statistics = channel.get('statistics', {})

        # サムネイル画像URL（優先度順に取得）
        thumbnails = snippet.get('thumbnails', {})
        thumbnail_url = (
            thumbnails.get('high', {}).get('url') or
            thumbnails.get('medium', {}).get('url') or
            thumbnails.get('default', {}).get('url') or
            ''
        )

        return {
            'id': channel_id,
            'title': snippet.get('title', '不明なチャンネル'),
            'thumbnail': thumbnail_url,
            'description': snippet.get('description', ''),
            'subscriber_count': statistics.get('subscriberCount', '0')
        }

    except Exception as e:
        print(f"[!] チャンネル情報取得エラー ({channel_id}): {e}")
        return None


def get_multiple_channels_info(channel_ids: List[str]) -> List[Dict[str, str]]:
    """
    複数のチャンネル情報を一括取得

    Args:
        channel_ids: チャンネルIDのリスト

    Returns:
        List[Dict]: チャンネル情報のリスト
    """
    results = []

    # YouTube APIは1リクエストで最大50チャンネル取得可能
    # 安全のため10件ずつ処理
    batch_size = 10

    for i in range(0, len(channel_ids), batch_size):
        batch = channel_ids[i:i+batch_size]

        try:
            request = youtube.channels().list(
                part='snippet,statistics',
                id=','.join(batch)
            )
            response = request.execute()

            for channel in response.get('items', []):
                snippet = channel['snippet']
                statistics = channel.get('statistics', {})
                thumbnails = snippet.get('thumbnails', {})

                thumbnail_url = (
                    thumbnails.get('high', {}).get('url') or
                    thumbnails.get('medium', {}).get('url') or
                    thumbnails.get('default', {}).get('url') or
                    ''
                )

                results.append({
                    'id': channel['id'],
                    'title': snippet.get('title', '不明なチャンネル'),
                    'thumbnail': thumbnail_url,
                    'description': snippet.get('description', ''),
                    'subscriber_count': statistics.get('subscriberCount', '0')
                })

        except Exception as e:
            print(f"[!] バッチ取得エラー: {e}")
            continue

    return results


def update_channel_name(channel_id: str) -> Optional[str]:
    """
    チャンネルIDから名前のみを取得（軽量版）

    Args:
        channel_id: YouTubeチャンネルID

    Returns:
        str: チャンネル名（取得失敗時はNone）
    """
    info = get_channel_info(channel_id)
    return info['title'] if info else None


if __name__ == "__main__":
    # テスト用
    import sys

    if len(sys.argv) > 1:
        channel_id = sys.argv[1]
        print(f"\n[*] チャンネル情報取得: {channel_id}")
        info = get_channel_info(channel_id)

        if info:
            print(f"[OK] チャンネル名: {info['title']}")
            print(f"[OK] サムネイル: {info['thumbnail']}")
            print(f"[OK] 登録者数: {info['subscriber_count']}")
        else:
            print("[!] 取得失敗")
    else:
        print("使い方: python youtube_channel_info.py <チャンネルID>")
