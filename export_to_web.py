#!/usr/bin/env python3
"""
CSVデータをWeb表示用のJSON形式に変換するスクリプト
"""

import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from utils.youtube_channel_info import get_multiple_channels_info

# 入力・出力パス
CSV_INPUT = 'output/csv/song_timestamps_complete.csv'
JSON_OUTPUT = 'docs/data/timestamps.json'
CHANNELS_OUTPUT = 'docs/data/channels.json'

# チャンネルID一覧
CHANNEL_IDS = [
    'UCHM_SLi7s0AJ8UBmm3pWN6Q',  # ふくもつく
    'UCmM2LkAA9WYFZor1k_szNew',  # 九文字ポルポ
    'UCMf7-2iEzioOK6t_T7mVvDQ',  # 月儚リン
    'UCiVwDkYw01KbZwZl5s7b9IQ',  # 琉華メイファン
    'UCgaaW1hyIQQ6rQg0cfPASsA',  # 狛ノヰみつ
]


def csv_to_json():
    """CSVをJSONに変換"""
    print('[*] CSVファイルを読み込み中...')

    if not os.path.exists(CSV_INPUT):
        print(f'[!] CSVファイルが見つかりません: {CSV_INPUT}')
        return

    timestamps = []

    with open(CSV_INPUT, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # 空行をスキップ
            if not row.get('曲'):
                continue

            timestamps.append({
                'No': row.get('No', ''),
                '曲': row.get('曲', ''),
                '歌手-ユニット': row.get('歌手-ユニット', ''),
                '検索用': row.get('検索用', ''),
                'ジャンル': row.get('ジャンル', ''),
                'タイムスタンプ': row.get('タイムスタンプ', ''),
                '配信日': row.get('配信日', ''),
                '動画ID': row.get('動画ID', ''),
                '確度スコア': row.get('確度スコア', '')
            })

    print(f'[OK] {len(timestamps)}件のタイムスタンプを読み込みました')

    # JSON出力
    output_data = {
        'last_updated': datetime.now().strftime('%Y/%m/%d %H:%M'),
        'total_count': len(timestamps),
        'timestamps': timestamps
    }

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)

    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f'[OK] JSONファイルを出力しました: {JSON_OUTPUT}')


def export_channel_info():
    """チャンネル情報をJSON出力"""
    print('\n[*] チャンネル情報を取得中...')

    channels_data = get_multiple_channels_info(CHANNEL_IDS)

    if not channels_data:
        print('[!] チャンネル情報の取得に失敗しました')
        return

    # 簡略化したデータ構造
    simplified_data = [
        {
            'id': ch['id'],
            'name': ch['title'],
            'thumbnail': ch['thumbnail']
        }
        for ch in channels_data
    ]

    os.makedirs(os.path.dirname(CHANNELS_OUTPUT), exist_ok=True)

    with open(CHANNELS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(simplified_data, f, ensure_ascii=False, indent=2)

    print(f'[OK] チャンネル情報を出力しました: {CHANNELS_OUTPUT}')

    for ch in simplified_data:
        print(f'   - {ch["name"]}')


if __name__ == '__main__':
    print('='*70)
    print('[*] Web表示用データを生成します')
    print('='*70)

    csv_to_json()
    export_channel_info()

    print('\n' + '='*70)
    print('[OK] 完了！')
    print('='*70)
    print(f'\n次のステップ:')
    print(f'1. docs/index.html をブラウザで開いてローカルテスト')
    print(f'2. GitHub Pagesで公開する場合は設定を行ってください')
