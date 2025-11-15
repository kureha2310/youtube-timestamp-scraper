#!/usr/bin/env python3
"""
CSVデータをWeb表示用のJSON形式に変換するスクリプト
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from googleapiclient.discovery import build

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from utils.youtube_channel_info import get_multiple_channels_info

load_dotenv()

# 入力・出力パス
CSV_INPUT_SINGING = 'output/csv/song_timestamps_complete.csv'  # 歌枠のみ（既存ファイル使用）
CSV_INPUT_ALL = 'output/csv/song_timestamps_complete.csv'  # 総合（既存ファイル使用）
JSON_OUTPUT_SINGING = 'docs/data/timestamps_singing.json'
JSON_OUTPUT_ALL = 'docs/data/timestamps_all.json'
CHANNELS_OUTPUT = 'docs/data/channels.json'

# チャンネルID一覧
CHANNEL_IDS = [
    'UCHM_SLi7s0AJ8UBmm3pWN6Q',  # ふくもつく
    'UCmM2LkAA9WYFZor1k_szNew',  # 九文字ポルポ
    'UCMf7-2iEzioOK6t_T7mVvDQ',  # 月儚リン
    'UCiVwDkYw01KbZwZl5s7b9IQ',  # 琉華メイファン
    'UCgaaW1hyIQQ6rQg0cfPASsA',  # 狛ノヰみつ
]


def get_channel_id_from_video_id(video_id: str, youtube) -> Optional[str]:
    """動画IDからチャンネルIDを取得"""
    try:
        request = youtube.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if response.get('items'):
            return response['items'][0]['snippet']['channelId']
        return None
    except Exception as e:
        print(f"[!] 動画ID {video_id} からチャンネルID取得エラー: {e}")
        return None


def build_video_to_channel_map(timestamps: list, youtube) -> Dict[str, str]:
    """動画IDからチャンネルIDへのマッピングを作成"""
    print('\n[*] 動画IDからチャンネルIDを取得中...')
    
    # ユニークな動画IDを取得
    unique_video_ids = list(set([ts['動画ID'] for ts in timestamps if ts.get('動画ID')]))
    print(f'   ユニークな動画数: {len(unique_video_ids)}')
    
    video_to_channel = {}
    
    # YouTube APIは1リクエストで最大50動画取得可能
    batch_size = 50
    for i in range(0, len(unique_video_ids), batch_size):
        batch = unique_video_ids[i:i+batch_size]
        print(f'   処理中: {i+1}-{min(i+batch_size, len(unique_video_ids))}/{len(unique_video_ids)}')
        
        try:
            request = youtube.videos().list(
                part='snippet',
                id=','.join(batch)
            )
            response = request.execute()
            
            for item in response.get('items', []):
                video_id = item['id']
                channel_id = item['snippet']['channelId']
                video_to_channel[video_id] = channel_id
        except Exception as e:
            print(f'   [!] バッチ処理エラー: {e}')
            continue
    
    print(f'[OK] {len(video_to_channel)}件の動画IDからチャンネルIDを取得しました')
    return video_to_channel


def csv_to_json(csv_input: str, json_output: str, mode_name: str = ""):
    """CSVをJSONに変換"""
    print(f'\n[*] {mode_name}CSVファイルを読み込み中...')

    if not os.path.exists(csv_input):
        print(f'[!] CSVファイルが見つかりません: {csv_input}')
        return

    timestamps = []

    with open(csv_input, 'r', encoding='utf-8-sig') as f:
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

    # YouTube APIを初期化
    api_key = os.getenv('API_KEY')
    if not api_key:
        print('[!] API_KEYが設定されていません。チャンネルIDを取得できません。')
        video_to_channel = {}
    else:
        youtube = build('youtube', 'v3', developerKey=api_key)
        video_to_channel = build_video_to_channel_map(timestamps, youtube)
    
    # チャンネルIDを追加
    for ts in timestamps:
        video_id = ts.get('動画ID', '')
        if video_id and video_id in video_to_channel:
            ts['チャンネルID'] = video_to_channel[video_id]
        else:
            ts['チャンネルID'] = ''

    # JSON出力
    output_data = {
        'last_updated': datetime.now().strftime('%Y/%m/%d %H:%M'),
        'total_count': len(timestamps),
        'timestamps': timestamps
    }

    os.makedirs(os.path.dirname(json_output), exist_ok=True)

    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f'[OK] JSONファイルを出力しました: {json_output}')


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

    # 歌枠モードと総合モードの両方を処理
    csv_to_json(CSV_INPUT_SINGING, JSON_OUTPUT_SINGING, '[歌枠モード] ')
    csv_to_json(CSV_INPUT_ALL, JSON_OUTPUT_ALL, '[総合モード] ')
    export_channel_info()

    print('\n' + '='*70)
    print('[OK] 完了！')
    print('='*70)
    print(f'\n出力ファイル:')
    print(f'  - 歌枠のみ: {JSON_OUTPUT_SINGING}')
    print(f'  - 総合: {JSON_OUTPUT_ALL}')
    print(f'\n次のステップ:')
    print(f'1. docs/index.html をブラウザで開いてローカルテスト')
    print(f'2. GitHub Pagesで公開する場合は設定を行ってください')
