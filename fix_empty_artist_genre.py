#!/usr/bin/env python3
"""
アーティスト欄が空のエントリのジャンルを「その他」に修正するスクリプト
"""

import csv
import os
import sys


def fix_empty_artist_genre(csv_path: str) -> bool:
    """
    アーティスト欄が空のエントリのジャンルを「その他」に修正

    Args:
        csv_path: CSVファイルのパス

    Returns:
        成功したかどうか
    """
    if not os.path.exists(csv_path):
        print(f'[!] ファイルが見つかりません: {csv_path}')
        return False

    print(f'\n[*] CSVファイルを読み込み中: {csv_path}')

    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    print(f'[OK] {len(rows)}行を読み込みました')

    # アーティスト欄が空のエントリをチェック
    fixed_count = 0
    for row in rows:
        artist = row.get('歌手-ユニット', '').strip()
        genre = row.get('ジャンル', '').strip()
        song = row.get('曲', '').strip()

        # アーティストが空欄で、ジャンルがVocaloid/J-POP/アニメの場合
        if not artist and genre in ['Vocaloid', 'J-POP', 'アニメ']:
            row['ジャンル'] = 'その他'
            fixed_count += 1
            try:
                print(f'   [修正] {song} : {genre} → その他')
            except UnicodeEncodeError:
                print(f'   [修正] [表示不可] : {genre} → その他')

    print(f'\n[*] 修正結果: {fixed_count}件のジャンルを「その他」に変更')

    if fixed_count == 0:
        print('[OK] 修正不要でした')
        return True

    # 元のファイルをバックアップ
    backup_path = csv_path + '.bak'
    if os.path.exists(backup_path):
        os.remove(backup_path)
    os.rename(csv_path, backup_path)
    print(f'[OK] バックアップを作成: {backup_path}')

    # CSVに書き出し
    print(f'[*] CSVを出力中: {csv_path}')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f'[OK] {len(rows)}行を出力しました')
    return True


def fix_all_csv_files():
    """全てのCSVファイルを修正"""
    csv_files = [
        'output/csv/song_timestamps_singing_only.csv',
        'output/csv/song_timestamps_other.csv',
    ]

    print('='*70)
    print('[*] アーティスト空欄エントリのジャンル修正')
    print('='*70)

    total_fixed = 0

    for csv_file in csv_files:
        if not os.path.exists(csv_file):
            print(f'\n[!] ファイルが見つかりません: {csv_file}')
            continue

        print(f'\n{"="*70}')
        print(f'[*] 処理中: {csv_file}')
        print('='*70)

        if fix_empty_artist_genre(csv_file):
            print('[OK] 完了')
        else:
            print('[!] エラーが発生しました')

    print(f'\n{"="*70}')
    print('[OK] 全ての処理が完了しました')
    print('='*70)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # コマンドライン引数でファイル指定
        csv_path = sys.argv[1]
        fix_empty_artist_genre(csv_path)
    else:
        # 全CSVファイルを処理
        fix_all_csv_files()
