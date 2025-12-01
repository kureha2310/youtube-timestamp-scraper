#!/usr/bin/env python3
"""5人全員のチャンネルから同時にスクレイプするスクリプト"""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from extractors.youtube_song_scraper import scrape_channels

# user_ids.jsonからチャンネルIDを読み込み
print("=" * 60)
print("5人全員のチャンネルからスクレイプを開始します")
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

# モード選択
print("スクレイプモードを選択してください:")
print("1. 差分更新（前回以降の動画のみ・高速）")
print("2. 全件取得（すべての動画・低速）")
mode_choice = input("\n選択 (1/2): ").strip()

incremental = True
if mode_choice == "2":
    incremental = False
    print("\n全件取得モードで実行します")
else:
    print("\n差分更新モードで実行します")

# スクレイプ実行
print("スクレイプを開始します...")
print()
scrape_channels(channel_ids, incremental=incremental)

print()
print("=" * 60)
print("スクレイプ完了！")
print("=" * 60)
print()
print("次のステップ:")
print("1. export_to_web.py を実行してJSONデータを更新")
print("2. docs/index.html をブラウザで開いて確認")

