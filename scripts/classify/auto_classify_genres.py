#!/usr/bin/env python3
"""
Spotify APIを使った自動ジャンル判定スクリプト
「その他」に分類されている楽曲を自動的に再分類します
"""

import pandas as pd
from datetime import datetime
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.spotify_classifier import SpotifyGenreClassifier
from src.utils.genre_classifier import GenreClassifier


def auto_classify_genres(
    input_csv: str = "output/csv/song_timestamps_complete.csv",
    output_csv: str = None,
    target_genre: str = "その他",
    dry_run: bool = False
):
    """
    Spotify APIを使って自動的にジャンルを判定

    Args:
        input_csv: 入力CSVファイル
        output_csv: 出力CSVファイル（Noneの場合は上書き）
        target_genre: 再分類対象のジャンル（デフォルト: その他）
        dry_run: Trueの場合は実際には保存せず、結果のみ表示
    """
    if output_csv is None:
        output_csv = input_csv

    print("=" * 80)
    print("Spotify APIを使った自動ジャンル判定")
    print("=" * 80)
    print(f"入力ファイル: {input_csv}")
    print(f"出力ファイル: {output_csv}")
    print(f"対象ジャンル: {target_genre}")
    if dry_run:
        print("【ドライランモード】実際には保存しません")
    print()

    # CSVを読み込み
    try:
        df = pd.read_csv(input_csv, encoding='utf-8')
    except Exception as e:
        print(f"エラー: CSVファイルの読み込みに失敗しました: {e}")
        return

    total_count = len(df)
    target_count = len(df[df['ジャンル'] == target_genre])

    print(f"総件数: {total_count}件")
    print(f"{target_genre}: {target_count}件")
    print()

    # 分類器を初期化
    spotify_classifier = SpotifyGenreClassifier()
    fallback_classifier = GenreClassifier()

    if not spotify_classifier.sp:
        print("警告: Spotify API接続に失敗しました")
        print("環境変数 SPOTIFY_CLIENT_ID と SPOTIFY_CLIENT_SECRET を設定してください")
        print()
        return

    # バックアップ作成
    if not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = input_csv.replace('.csv', f'_backup_{timestamp}.csv')
        df.to_csv(backup_file, index=False, encoding='utf-8')
        print(f"バックアップ作成: {backup_file}\n")

    # 再分類処理
    changes = []
    not_found = []

    print(f"Spotify APIでジャンル判定中...")
    print("-" * 80)

    for idx, row in df.iterrows():
        current_genre = row['ジャンル']

        # 対象ジャンル以外はスキップ
        if current_genre != target_genre:
            continue

        artist = row['歌手-ユニット']
        song_title = row['曲']

        # アーティスト情報がない場合はスキップ
        if pd.isna(artist) or not artist or artist.lower() in ['nan', '-', 'none', '']:
            continue

        # Spotify APIで検索
        new_genre = spotify_classifier.get_genre_from_spotify(artist, song_title)

        if new_genre:
            # ジャンルが見つかった
            df.at[idx, 'ジャンル'] = new_genre
            changes.append({
                'index': idx,
                'song': song_title,
                'artist': artist,
                'old_genre': current_genre,
                'new_genre': new_genre,
                'source': 'Spotify'
            })
            try:
                print(f"  [{idx}] {song_title} / {artist}")
                print(f"      {current_genre} → {new_genre} (Spotify)")
            except UnicodeEncodeError:
                print(f"  [{idx}] (特殊文字を含む曲)")
                print(f"      {current_genre} → {new_genre} (Spotify)")
        else:
            # Spotify APIで見つからなかった場合、既存の分類器で再試行
            fallback_genre = fallback_classifier.classify(artist, song_title)
            if fallback_genre != current_genre and fallback_genre != "その他":
                df.at[idx, 'ジャンル'] = fallback_genre
                changes.append({
                    'index': idx,
                    'song': song_title,
                    'artist': artist,
                    'old_genre': current_genre,
                    'new_genre': fallback_genre,
                    'source': 'Fallback'
                })
                try:
                    print(f"  [{idx}] {song_title} / {artist}")
                    print(f"      {current_genre} → {fallback_genre} (キーワード)")
                except UnicodeEncodeError:
                    print(f"  [{idx}] (特殊文字を含む曲)")
                    print(f"      {current_genre} → {fallback_genre} (キーワード)")
            else:
                not_found.append({
                    'index': idx,
                    'song': song_title,
                    'artist': artist
                })

    print()
    print("=" * 80)
    print(f"判定完了: {len(changes)}件を再分類")
    print("=" * 80)

    # 変更サマリー
    if changes:
        print("\n【変更サマリー】")
        genre_changes = {}
        for change in changes:
            key = f"{change['old_genre']} → {change['new_genre']}"
            genre_changes[key] = genre_changes.get(key, 0) + 1

        for key, count in sorted(genre_changes.items(), key=lambda x: -x[1]):
            print(f"  {key}: {count}件")

    # 見つからなかった楽曲
    if not_found:
        print(f"\n【判定できなかった楽曲】 {len(not_found)}件")
        print("以下の楽曲は手動で分類が必要です:")
        for item in not_found[:10]:  # 最初の10件のみ表示
            print(f"  [{item['index']}] {item['song']} / {item['artist']}")
        if len(not_found) > 10:
            print(f"  ... 他 {len(not_found) - 10}件")

    # 新しいジャンル分布
    print("\n【新しいジャンル分布】")
    genre_counts = df['ジャンル'].value_counts()
    for genre, count in genre_counts.items():
        print(f"  {genre}: {count}件")

    # 保存
    if not dry_run:
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"\n[OK] 更新完了: {output_csv}")
    else:
        print("\n【ドライランモード】実際には保存していません")

    # Spotifyキャッシュ統計
    print("\n【Spotifyキャッシュ統計】")
    cache_stats = spotify_classifier.get_cache_stats()
    print(f"  キャッシュ件数: {cache_stats['total_cached']}")
    print(f"  見つかった: {cache_stats['found']}")
    print(f"  見つからなかった: {cache_stats['not_found']}")

    print()
    return df, changes, not_found


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Spotify APIを使った自動ジャンル判定')
    parser.add_argument(
        '--input',
        default='output/csv/song_timestamps_complete.csv',
        help='入力CSVファイル'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='出力CSVファイル（指定しない場合は上書き）'
    )
    parser.add_argument(
        '--target',
        default='その他',
        help='再分類対象のジャンル（デフォルト: その他）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='ドライラン（実際には保存しない）'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='すべてのCSVファイルを処理'
    )

    args = parser.parse_args()

    if args.all:
        # すべてのファイルを処理
        files = [
            'output/csv/song_timestamps_complete.csv',
            'output/csv/song_timestamps_singing_only.csv'
        ]
        for file in files:
            if os.path.exists(file):
                print(f"\n処理中: {file}")
                auto_classify_genres(
                    input_csv=file,
                    output_csv=None,
                    target_genre=args.target,
                    dry_run=args.dry_run
                )
                print("\n" + "=" * 80 + "\n")
    else:
        # 単一ファイルを処理
        auto_classify_genres(
            input_csv=args.input,
            output_csv=args.output,
            target_genre=args.target,
            dry_run=args.dry_run
        )
