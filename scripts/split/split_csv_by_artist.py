#!/usr/bin/env python3
"""
CSVデータを歌手の有無で分割するスクリプト
- 歌手あり → song_timestamps_singing_only.csv
- 歌手なし → song_timestamps_other.csv
"""

import csv
import os
from datetime import datetime

# 入力ファイル
INPUT_CSV = 'output/csv/song_timestamps_complete.csv'

# 出力ファイル
OUTPUT_SINGING = 'output/csv/song_timestamps_singing_only.csv'
OUTPUT_OTHER = 'output/csv/song_timestamps_other.csv'


def split_csv():
    """CSVを歌手の有無で分割"""
    print('='*70)
    print('[*] CSVファイルを分割します')
    print('='*70)

    if not os.path.exists(INPUT_CSV):
        print(f'[!] 入力ファイルが見つかりません: {INPUT_CSV}')
        return

    singing_data = []
    other_data = []

    # CSVを読み込み
    with open(INPUT_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            # 歌手-ユニット列が空白かチェック
            artist = row.get('歌手-ユニット', '').strip()

            if artist:
                # 歌手あり
                singing_data.append(row)
            else:
                # 歌手なし
                other_data.append(row)

    print(f'\n[*] 読み込み完了')
    print(f'   総データ数: {len(singing_data) + len(other_data)}件')
    print(f'   歌枠データ: {len(singing_data)}件')
    print(f'   その他データ: {len(other_data)}件')

    # 歌枠データを出力
    os.makedirs(os.path.dirname(OUTPUT_SINGING), exist_ok=True)
    with open(OUTPUT_SINGING, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(singing_data)

    print(f'\n[OK] 歌枠データを出力: {OUTPUT_SINGING}')

    # その他データを出力
    with open(OUTPUT_OTHER, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(other_data)

    print(f'[OK] その他データを出力: {OUTPUT_OTHER}')

    # 統計情報
    print('\n' + '='*70)
    print('[*] 分割完了')
    print('='*70)
    print(f'\n歌枠データ ({len(singing_data)}件):')
    print(f'  → {OUTPUT_SINGING}')
    print(f'\nその他データ ({len(other_data)}件):')
    print(f'  → {OUTPUT_OTHER}')
    print(f'\n合計: {len(singing_data) + len(other_data)}件')


if __name__ == '__main__':
    split_csv()
