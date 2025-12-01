#!/usr/bin/env python3
"""
アーティストなし（雑談・企画など）のタイムスタンプを抽出
"""

import pandas as pd
from datetime import datetime

# 入力・出力ファイル
INPUT_CSV = 'output/csv/song_timestamps_complete.csv'
OUTPUT_CSV = 'output/csv/song_timestamps_other.csv'

def main():
    print("=" * 80)
    print("アーティストなしタイムスタンプを抽出")
    print("=" * 80)

    # CSVを読み込み
    df = pd.read_csv(INPUT_CSV, encoding='utf-8')
    total = len(df)

    print(f"総件数: {total}件")

    # アーティストが空のものだけ抽出
    df_other = df[
        (df['歌手-ユニット'].isna()) |
        (df['歌手-ユニット'] == '') |
        (df['歌手-ユニット'].str.strip() == '')
    ].copy()

    other_count = len(df_other)

    print(f"アーティストなし: {other_count}件 ({other_count/total*100:.1f}%)")

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if pd.io.common.file_exists(OUTPUT_CSV):
        backup_file = OUTPUT_CSV.replace('.csv', f'_backup_{timestamp}.csv')
        import shutil
        shutil.copy(OUTPUT_CSV, backup_file)
        print(f"バックアップ作成: {backup_file}")

    # 保存
    df_other.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"\n✓ 保存完了: {OUTPUT_CSV}")

    # サンプル表示
    print("\n【サンプル】")
    for _, row in df_other.head(10).iterrows():
        print(f"  • {row['曲']} ({row['配信日']})")

    print(f"\n総件数: {other_count}件")

if __name__ == '__main__':
    main()
