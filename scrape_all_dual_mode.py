#!/usr/bin/env python3
"""5人全員のチャンネルから歌枠モードと総合モードの両方でスクレイプするスクリプト"""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from extractors.youtube_song_scraper import scrape_channels

# user_ids.jsonからチャンネルIDを読み込み
print("=" * 60)
print("5人全員のチャンネルからスクレイプを開始します")
print("歌枠モードと総合モードの両方を実行します")
print("=" * 60)
print()

with open('user_ids.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

channels = data.get('channels', [])
enabled_channels = [ch for ch in channels if ch.get('enabled', True)]

if not enabled_channels:
    print("[!] 有効なチャンネルが見つかりません")
    sys.exit(1)

print(f"対象チャンネル数: {len(enabled_channels)}")
for i, ch in enumerate(enabled_channels, 1):
    print(f"  {i}. {ch['name']} ({ch['channel_id']})")
print()

# チャンネルIDのリストを作成
channel_ids = [ch['channel_id'] for ch in enabled_channels]

# 1. 歌枠モードでスクレイプ
print("\n" + "=" * 60)
print("【歌枠モード】歌枠のみを抽出します")
print("=" * 60)
scrape_channels(channel_ids, "output/csv/song_timestamps_singing_only.csv", filter_singing_only=True)

# 2. 総合モードでスクレイプ
print("\n" + "=" * 60)
print("【総合モード】すべての動画からタイムスタンプを抽出します")
print("=" * 60)
scrape_channels(channel_ids, "output/csv/song_timestamps_all.csv", filter_singing_only=False)

print("\n" + "=" * 60)
print("スクレイプ完了！")
print("=" * 60)
print()
print("出力ファイル:")
print("  - 歌枠のみ: output/csv/song_timestamps_singing_only.csv")
print("  - 総合: output/csv/song_timestamps_all.csv")
print()
print("次のステップ:")
print("1. export_to_web.py を実行してJSONデータを更新")
print("2. docs/index.html をブラウザで開いて確認")

