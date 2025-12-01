#!/usr/bin/env python3
"""
3チャンネルのテストスクレイプスクリプト
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from extractors.youtube_song_scraper import scrape_channels

# user_ids.jsonから全チャンネルを読み込み
import json
with open('user_ids.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    channel_ids = [ch['channel_id'] for ch in data['channels'] if ch.get('enabled', True)]

print("="*60)
print("テストスクレイプ開始")
print("="*60)
print(f"対象チャンネル: {len(channel_ids)}件")
for i, ch in enumerate(data['channels'], 1):
    if ch.get('enabled', True):
        print(f"  {i}. {ch['name']} ({ch['channel_id']})")
print("="*60)
print()

# スクレイプ実行
scrape_channels(channel_ids, output_file="output/csv/song_timestamps_complete.csv")

print("\n" + "="*60)
print("テスト完了！")
print("="*60)
