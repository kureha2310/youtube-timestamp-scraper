#!/usr/bin/env python3
"""既存のJSONデータと新しいCSVデータをマージするスクリプト"""

import json
import csv
from collections import OrderedDict

# JSONから既存データを読み込み
print("[*] JSONファイルから既存データを読み込み中...")
with open('docs/data/timestamps.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

existing_timestamps = json_data.get('timestamps', [])
print(f"[OK] 既存データ: {len(existing_timestamps)}曲")

# 新しいCSVデータを読み込み
print("[*] 新しいCSVファイルを読み込み中...")
new_timestamps = []
with open('output/csv/song_timestamps_complete.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('曲'):
            new_timestamps.append(row)
print(f"[OK] 新しいデータ: {len(new_timestamps)}曲")

# 既存データの動画IDとタイムスタンプのセットを作成（重複チェック用）
existing_keys = set()
for ts in existing_timestamps:
    video_id = ts.get('動画ID', '')
    timestamp = ts.get('タイムスタンプ', '')
    song = ts.get('曲', '')
    key = (video_id, timestamp, song)
    existing_keys.add(key)

# 新しいデータで既存にないものだけを追加
added_count = 0
for ts in new_timestamps:
    video_id = ts.get('動画ID', '')
    timestamp = ts.get('タイムスタンプ', '')
    song = ts.get('曲', '')
    key = (video_id, timestamp, song)
    
    if key not in existing_keys:
        # CSV形式からJSON形式に変換
        json_ts = {
            'No': str(len(existing_timestamps) + added_count + 1),
            '曲': song,
            '歌手-ユニット': ts.get('歌手-ユニット', ''),
            '検索用': ts.get('検索用', ''),
            'ジャンル': ts.get('ジャンル', ''),
            'タイムスタンプ': timestamp,
            '配信日': ts.get('配信日', ''),
            '動画ID': video_id,
            '確度スコア': ts.get('確度スコア', ''),
            'チャンネルID': ''  # 後で追加される
        }
        existing_timestamps.append(json_ts)
        existing_keys.add(key)
        added_count += 1

print(f"[OK] 追加された曲: {added_count}曲")
print(f"[OK] 合計: {len(existing_timestamps)}曲")

# CSVファイルに書き戻す
print("[*] CSVファイルに書き戻し中...")
with open('output/csv/song_timestamps_complete.csv', 'w', encoding='utf-8-sig', newline='') as f:
    fieldnames = ['No', '曲', '歌手-ユニット', '検索用', 'ジャンル', 'タイムスタンプ', '配信日', '動画ID', '確度スコア']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    
    for i, ts in enumerate(existing_timestamps, 1):
        writer.writerow({
            'No': str(i),
            '曲': ts.get('曲', ''),
            '歌手-ユニット': ts.get('歌手-ユニット', ''),
            '検索用': ts.get('検索用', ''),
            'ジャンル': ts.get('ジャンル', ''),
            'タイムスタンプ': ts.get('タイムスタンプ', ''),
            '配信日': ts.get('配信日', ''),
            '動画ID': ts.get('動画ID', ''),
            '確度スコア': ts.get('確度スコア', '')
        })

print(f"[OK] CSVファイルを更新しました: output/csv/song_timestamps_complete.csv")
print()
print("次のステップ:")
print("1. export_to_web.py を実行してJSONデータを更新（チャンネルIDを追加）")

