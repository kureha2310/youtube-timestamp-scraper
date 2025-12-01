#!/usr/bin/env python3
"""
CSVデータのジャンルを再分類するスクリプト
"""

import pandas as pd
import sys
import os
from datetime import datetime

# UTF-8出力設定
sys.stdout.reconfigure(encoding='utf-8')

# src.utilsをインポートパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.genre_classifier import GenreClassifier


def reclassify_csv(input_file: str, output_file: str = None):
    """
    CSVファイルのジャンルを再分類

    Args:
        input_file: 入力CSVファイルパス
        output_file: 出力CSVファイルパス（Noneなら入力ファイルを上書き）
    """
    if output_file is None:
        output_file = input_file

    print(f"ジャンル再分類を開始します...")
    print(f"入力ファイル: {input_file}")
    print(f"出力ファイル: {output_file}")

    # CSVを読み込み
    try:
        df = pd.read_csv(input_file, encoding='utf-8-sig')
    except Exception as e:
        print(f"エラー: CSVファイルの読み込みに失敗しました: {e}")
        return False

    print(f"\n総件数: {len(df)}件")

    # 現在のジャンル分布
    print("\n【現在のジャンル分布】")
    current_distribution = df['ジャンル'].value_counts()
    for genre, count in current_distribution.items():
        print(f"  {genre}: {count}件")

    # バックアップ作成
    if output_file == input_file:
        backup_file = input_file.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        df.to_csv(backup_file, index=False, encoding='utf-8-sig')
        print(f"\nバックアップ作成: {backup_file}")

    # 分類器を初期化
    classifier = GenreClassifier()

    # ジャンル再分類
    print("\nジャンル再分類中...")
    new_genres = []
    changes_count = 0

    for idx, row in df.iterrows():
        artist = str(row['歌手-ユニット']) if pd.notna(row['歌手-ユニット']) else ''
        song = str(row['曲']) if pd.notna(row['曲']) else ''
        old_genre = row['ジャンル']

        # 新しいジャンルを分類
        new_genre = classifier.classify(artist, song)
        new_genres.append(new_genre)

        # 変更があった場合
        if new_genre != old_genre:
            changes_count += 1
            if changes_count <= 10:  # 最初の10件だけ表示
                print(f"  [{idx+1}] {song} / {artist}")
                print(f"      {old_genre} → {new_genre}")

    # ジャンル列を更新
    df['ジャンル'] = new_genres

    print(f"\n変更件数: {changes_count}件")

    # 新しいジャンル分布
    print("\n【新しいジャンル分布】")
    new_distribution = df['ジャンル'].value_counts()
    for genre, count in new_distribution.items():
        print(f"  {genre}: {count}件")

    # CSVに保存
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ 更新完了: {output_file}")

    # サンプル表示
    print("\n【分類サンプル】")
    for genre in ['Vocaloid', 'アニメ', 'J-POP']:
        samples = df[df['ジャンル'] == genre][['曲', '歌手-ユニット']].head(3)
        if len(samples) > 0:
            print(f"\n{genre}:")
            for _, row in samples.iterrows():
                print(f"  • {row['曲']} / {row['歌手-ユニット']}")

    return True


def main():
    """メイン処理"""
    # 再分類するCSVファイル
    csv_files = [
        'output/csv/song_timestamps_complete.csv',
        'output/csv/song_timestamps_singing_only.csv',
    ]

    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print("\n" + "=" * 80)
            success = reclassify_csv(csv_file)
            if not success:
                print(f"エラー: {csv_file} の処理に失敗しました")
        else:
            print(f"スキップ: {csv_file} が見つかりません")

    print("\n" + "=" * 80)
    print("すべての処理が完了しました！")
    print("\n次のステップ:")
    print("1. export_to_web.py を実行してJSONを再生成")
    print("2. frontendをビルドして確認")


if __name__ == '__main__':
    main()
