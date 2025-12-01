#!/usr/bin/env python3
"""みっちゃんのチャンネルからスクレイプするスクリプト"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from extractors.youtube_song_scraper import scrape_channels

# みっちゃんのチャンネルID
MITSU_CHANNEL_ID = 'UCgaaW1hyIQQ6rQg0cfPASsA'

print("=" * 60)
print("みっちゃん（狛ノヰみつ）のチャンネルからスクレイプを開始します")
print(f"チャンネルID: {MITSU_CHANNEL_ID}")
print("=" * 60)
print()

# スクレイプ実行
scrape_channels([MITSU_CHANNEL_ID])

print()
print("=" * 60)
print("スクレイプ完了！")
print("=" * 60)
print()
print("次のステップ:")
print("1. export_to_web.py を実行してJSONデータを更新")
print("2. docs/index.html をブラウザで開いて確認")

