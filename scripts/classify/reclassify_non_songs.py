#!/usr/bin/env python3
"""
非楽曲エントリを「歌枠」から「それ以外」に移動するスクリプト
"""

import csv
import sys

# export_to_web.py の判定関数をインポート
sys.path.insert(0, '.')
from export_to_web import is_non_song_entry

CSV_SINGING = 'output/csv/song_timestamps_singing_only.csv'
CSV_OTHER = 'output/csv/song_timestamps_other.csv'

def reclassify_non_songs():
    """非楽曲エントリを再分類"""
    print('=' * 70)
    print('[*] 非楽曲エントリを再分類します')
    print('=' * 70)

    # 歌枠CSVを読み込み
    singing_entries = []
    non_song_entries = []

    print(f'\n[*] {CSV_SINGING} を読み込み中...')
    with open(CSV_SINGING, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            song_title = row.get('曲', '').strip()
            if is_non_song_entry(song_title):
                non_song_entries.append(row)
                print(f'   [移動] {song_title}')
            else:
                singing_entries.append(row)

    print(f'\n[OK] 歌枠: {len(singing_entries)}件, 非楽曲: {len(non_song_entries)}件')

    # それ以外CSVを読み込み
    print(f'\n[*] {CSV_OTHER} を読み込み中...')
    other_entries = []
    with open(CSV_OTHER, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            other_entries.append(row)

    print(f'[OK] {len(other_entries)}件のそれ以外エントリを読み込みました')

    # マージ
    print(f'\n[*] 非楽曲エントリをそれ以外に追加...')
    other_entries.extend(non_song_entries)

    # 保存
    print(f'\n[*] 更新したCSVを保存中...')

    # 歌枠CSV（非楽曲を除外）
    with open(CSV_SINGING, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(singing_entries)
    print(f'[OK] {CSV_SINGING} を更新 ({len(singing_entries)}件)')

    # その他CSV（非楽曲を追加）
    with open(CSV_OTHER, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(other_entries)
    print(f'[OK] {CSV_OTHER} を更新 ({len(other_entries)}件)')

    print('\n' + '=' * 70)
    print('[OK] 完了！')
    print('=' * 70)
    print(f'\n結果:')
    print(f'  - 歌枠: {len(singing_entries)}件')
    print(f'  - それ以外: {len(other_entries)}件 (うち{len(non_song_entries)}件が非楽曲)')
    print(f'\n次のステップ:')
    print(f'  python export_to_web.py')


if __name__ == '__main__':
    reclassify_non_songs()
