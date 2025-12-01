#!/usr/bin/env python3
"""チャンネルごとの曲数を確認するスクリプト"""

import json
from collections import Counter

# データを読み込み
with open('docs/data/timestamps.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

timestamps = data['timestamps']

# チャンネルIDごとの曲数を集計
channel_counts = Counter()
for ts in timestamps:
    channel_id = ts.get('チャンネルID', '')
    if channel_id:
        channel_counts[channel_id] += 1

# チャンネル名のマッピング
channel_names = {
    'UCHM_SLi7s0AJ8UBmm3pWN6Q': 'ふくもつく',
    'UCmM2LkAA9WYFZor1k_szNew': '九文字ポルポ',
    'UCMf7-2iEzioOK6t_T7mVvDQ': '月儚リン',
    'UCiVwDkYw01KbZwZl5s7b9IQ': '琉華メイファン',
    'UCgaaW1hyIQQ6rQg0cfPASsA': '狛ノヰみつ（みっちゃん）',
}

print("=" * 60)
print("チャンネルごとの曲数")
print("=" * 60)

for channel_id, count in sorted(channel_counts.items(), key=lambda x: -x[1]):
    name = channel_names.get(channel_id, '不明')
    print(f"{name:20} ({channel_id}): {count:4}曲")

print("=" * 60)
print(f"合計: {sum(channel_counts.values())}曲")
print(f"チャンネルIDなし: {len([ts for ts in timestamps if not ts.get('チャンネルID')])}曲")

# みっちゃんの曲を確認
mitsu_id = 'UCgaaW1hyIQQ6rQg0cfPASsA'
mitsu_songs = [ts for ts in timestamps if ts.get('チャンネルID') == mitsu_id]

print("\n" + "=" * 60)
print(f"みっちゃん（{mitsu_id}）の曲: {len(mitsu_songs)}曲")
print("=" * 60)

if mitsu_songs:
    print("最初の10曲:")
    for i, song in enumerate(mitsu_songs[:10], 1):
        print(f"  {i}. {song.get('曲', '-')} / {song.get('歌手-ユニット', '-')}")
else:
    print("みっちゃんの曲が見つかりませんでした。")
    print("\nCSVファイルを確認して、みっちゃんのチャンネルからスクレイプする必要があるかもしれません。")

