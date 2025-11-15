#!/usr/bin/env python3
"""
既存のCSVファイルのジャンル列を再分類するスクリプト
"""

import csv
import sys
import os
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.genre_classifier import GenreClassifier


def reclassify_csv(input_file: str, output_file: str = None):
    """
    CSVファイルのジャンル列を再分類

    Args:
        input_file: 入力CSVファイルのパス
        output_file: 出力CSVファイルのパス（指定しない場合は上書き）
    """
    if not os.path.exists(input_file):
        print(f"エラー: {input_file} が見つかりません")
        return

    # ジャンル分類器を初期化
    classifier = GenreClassifier()

    # CSVファイルを読み込み
    print(f"読み込み中: {input_file}")
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"総行数: {len(rows)}")

    # ジャンルを再分類
    updated_count = 0
    for row in rows:
        song_title = row.get('曲', '')
        artist = row.get('歌手-ユニット', '')
        old_genre = row.get('ジャンル', '')

        # 新しいジャンルを判定
        new_genre = classifier.classify(artist, song_title)

        if old_genre != new_genre:
            updated_count += 1
            print(f"  更新: {song_title} / {artist}")
            print(f"    {old_genre} → {new_genre}")

        row['ジャンル'] = new_genre

    # 出力ファイル名を決定
    if output_file is None:
        # バックアップを作成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = input_file.replace('.csv', f'_backup_{timestamp}.csv')
        os.rename(input_file, backup_file)
        print(f"\nバックアップ作成: {backup_file}")
        output_file = input_file

    # CSVファイルに出力
    print(f"\n出力中: {output_file}")
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        # ヘッダーを取得
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(rows)

    print(f"\n完了！")
    print(f"  総行数: {len(rows)}")
    print(f"  更新数: {updated_count}")

    # ジャンル別統計
    genre_stats = {}
    for row in rows:
        genre = row['ジャンル']
        genre_stats[genre] = genre_stats.get(genre, 0) + 1

    print(f"\nジャンル別統計:")
    for genre, count in sorted(genre_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {genre}: {count}曲")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='CSVファイルのジャンル列を再分類')
    parser.add_argument('input_file', nargs='?',
                        default='output/csv/song_timestamps_complete.csv',
                        help='入力CSVファイル（デフォルト: output/csv/song_timestamps_complete.csv）')
    parser.add_argument('-o', '--output',
                        help='出力CSVファイル（指定しない場合は上書き）')

    args = parser.parse_args()

    reclassify_csv(args.input_file, args.output)
