#!/usr/bin/env python3
"""
CSVファイルから重複タイムスタンプを検出・除去するスクリプト
"""

import csv
import os
from collections import defaultdict
from typing import List, Dict, Tuple


def detect_duplicates(csv_path: str) -> Tuple[List[Dict], List[Dict]]:
    """
    CSVファイルから重複を検出

    Args:
        csv_path: CSVファイルのパス

    Returns:
        (ユニーク行のリスト, 重複行のリスト)
    """
    if not os.path.exists(csv_path):
        print(f'[!] ファイルが見つかりません: {csv_path}')
        return [], []

    print(f'\n[*] CSVファイルを読み込み中: {csv_path}')

    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    print(f'[OK] {len(rows)}行を読み込みました')

    # 重複判定のキー: (曲名, タイムスタンプ, 動画ID)
    seen = {}
    unique_rows = []
    duplicate_rows = []

    for row in rows:
        key = (
            row.get('曲', '').strip(),
            row.get('タイムスタンプ', '').strip(),
            row.get('動画ID', '').strip()
        )

        if key in seen:
            # 重複を発見
            duplicate_rows.append({
                'original_no': seen[key].get('No', ''),
                'duplicate_no': row.get('No', ''),
                'song': row.get('曲', ''),
                'artist': row.get('歌手-ユニット', ''),
                'timestamp': row.get('タイムスタンプ', ''),
                'video_id': row.get('動画ID', ''),
                'date': row.get('配信日', ''),
            })
        else:
            seen[key] = row
            unique_rows.append(row)

    return unique_rows, duplicate_rows


def remove_duplicates(csv_path: str, output_path: str = None) -> bool:
    """
    CSVファイルから重複を除去

    Args:
        csv_path: 入力CSVファイルのパス
        output_path: 出力CSVファイルのパス（指定しない場合は上書き）

    Returns:
        成功したかどうか
    """
    unique_rows, duplicate_rows = detect_duplicates(csv_path)

    if not unique_rows:
        print('[!] データがありません')
        return False

    # 重複レポート
    print(f'\n[*] 重複チェック結果:')
    print(f'   ユニーク行: {len(unique_rows)}')
    print(f'   重複行: {len(duplicate_rows)}')

    if duplicate_rows:
        print(f'\n[重複一覧]')
        for i, dup in enumerate(duplicate_rows[:20], 1):  # 最初の20件のみ表示
            print(f'{i}. No.{dup["original_no"]}と重複: {dup["song"]} / {dup["artist"]} ({dup["timestamp"]}) - {dup["date"]}')

        if len(duplicate_rows) > 20:
            print(f'   ... 他 {len(duplicate_rows) - 20}件の重複')

    # 出力パスが指定されていない場合は元ファイルに上書き
    if output_path is None:
        output_path = csv_path

    # CSVに書き出し
    print(f'\n[*] CSVを出力中: {output_path}')

    # 元のヘッダーを読み込む
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

    # Noを振り直す
    for i, row in enumerate(unique_rows, 1):
        row['No'] = str(i)

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f'[OK] {len(unique_rows)}行を出力しました')

    if duplicate_rows:
        print(f'[OK] {len(duplicate_rows)}件の重複を除去しました')
    else:
        print('[OK] 重複はありませんでした')

    return True


def check_all_csv_files():
    """全てのCSVファイルをチェック"""
    csv_files = [
        'output/csv/song_timestamps_singing_only.csv',
        'output/csv/song_timestamps_other.csv',
    ]

    print('='*70)
    print('[*] CSVファイルの重複チェック')
    print('='*70)

    total_duplicates = 0

    for csv_file in csv_files:
        if not os.path.exists(csv_file):
            print(f'\n[!] ファイルが見つかりません: {csv_file}')
            continue

        print(f'\n{"="*70}')
        print(f'[*] チェック中: {csv_file}')
        print('='*70)

        unique_rows, duplicate_rows = detect_duplicates(csv_file)
        total_duplicates += len(duplicate_rows)

        if duplicate_rows:
            print(f'\n[重複一覧] ({len(duplicate_rows)}件)')
            for i, dup in enumerate(duplicate_rows[:10], 1):
                try:
                    print(f'{i}. No.{dup["original_no"]}と重複: {dup["song"]} / {dup["artist"]} ({dup["timestamp"]}) - {dup["date"]}')
                except UnicodeEncodeError:
                    print(f'{i}. No.{dup["original_no"]}と重複: [表示不可] ({dup["timestamp"]}) - {dup["date"]}')

            if len(duplicate_rows) > 10:
                print(f'   ... 他 {len(duplicate_rows) - 10}件')
        else:
            print('[OK] 重複なし')

    print(f'\n{"="*70}')
    print(f'[*] 合計: {total_duplicates}件の重複が見つかりました')
    print('='*70)

    if total_duplicates > 0:
        print('\n重複を除去しますか？ (y/n): ', end='')
        response = input().strip().lower()

        if response == 'y':
            print('\n[*] 重複除去を開始します...')
            for csv_file in csv_files:
                if os.path.exists(csv_file):
                    remove_duplicates(csv_file)
            print('\n[OK] 完了！')
        else:
            print('[*] 重複除去をキャンセルしました')


if __name__ == '__main__':
    import sys

    # --autoフラグで自動実行
    auto_mode = '--auto' in sys.argv

    if len(sys.argv) > 1 and sys.argv[1] != '--auto':
        # コマンドライン引数でファイル指定
        csv_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        remove_duplicates(csv_path, output_path)
    else:
        # 全CSVファイルをチェック
        if auto_mode:
            # 自動モード: 確認なしで実行
            csv_files = [
                'output/csv/song_timestamps_singing_only.csv',
                'output/csv/song_timestamps_other.csv',
            ]

            print('='*70)
            print('[*] CSVファイルの重複チェック（自動モード）')
            print('='*70)

            for csv_file in csv_files:
                if os.path.exists(csv_file):
                    print(f'\n[*] 処理中: {csv_file}')
                    remove_duplicates(csv_file)
        else:
            check_all_csv_files()
