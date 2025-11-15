#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')

from src.utils.youtube_channel_info import get_multiple_channels_info

channel_ids = [
    "UCHM_SLi7s0AJ8UBmm3pWN6Q",  # ふくもつく
    "UCmM2LkAA9WYFZor1k_szNew",  # 九文字ポルポ
    "UCMf7-2iEzioOK6t_T7mVvDQ",  # ?
    "UCiVwDkYw01KbZwZl5s7b9IQ",  # ?
    "UCgaaW1hyIQQ6rQg0cfPASsA",  # ?
]

print("チャンネル情報を取得中...")
channels = get_multiple_channels_info(channel_ids)

for i, ch in enumerate(channels, 1):
    print(f"\n{i}. {ch['title']}")
    print(f"   ID: {ch['id']}")
    print(f"   サムネイル: {ch['thumbnail'][:60]}...")
