import pandas as pd
import os
from datetime import datetime

def classify_songs_by_tag(input_file, output_dir='output/csv/tags'):
    """
    曲をジャンルタグごとに分類して別々のCSVファイルに出力する

    Args:
        input_file: 入力CSVファイルのパス
        output_dir: 出力ディレクトリのパス
    """
    # 出力ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)

    # CSVファイルを読み込み（BOM付きUTF-8対応）
    df = pd.read_csv(input_file, encoding='utf-8-sig')

    # ジャンル列のユニークな値を取得
    genres = df['ジャンル'].unique()

    print(f"発見したタグ: {', '.join(genres)}")
    print(f"\n総曲数: {len(df)}")

    # タグごとの統計情報を格納
    stats = []

    # 各ジャンルごとにファイルを作成
    for genre in genres:
        # ジャンルでフィルタリング
        genre_df = df[df['ジャンル'] == genre].copy()

        # 重複を除去（曲名とアーティストが同じものを除外）
        genre_df_unique = genre_df.drop_duplicates(subset=['曲', '歌手-ユニット'], keep='first')

        # ファイル名を生成（安全な文字列に変換）
        safe_genre = genre.replace('/', '_').replace('\\', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f'tag_{safe_genre}_{timestamp}.csv')

        # CSVファイルに出力
        genre_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        # 統計情報を記録
        stats.append({
            'タグ': genre,
            '総出現回数': len(genre_df),
            'ユニーク曲数': len(genre_df_unique),
            'ファイル名': os.path.basename(output_file)
        })

        print(f"\n[{genre}]")
        print(f"  総出現回数: {len(genre_df)}")
        print(f"  ユニーク曲数: {len(genre_df_unique)}")
        print(f"  出力先: {output_file}")

    # 統計サマリーファイルを作成
    stats_df = pd.DataFrame(stats)
    stats_file = os.path.join(output_dir, f'tag_summary_{timestamp}.csv')
    stats_df.to_csv(stats_file, index=False, encoding='utf-8-sig')

    print(f"\n統計サマリー: {stats_file}")

    # タグごとの人気曲TOP3をテキストファイルに出力
    report_file = os.path.join(output_dir, f'tag_report_{timestamp}.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("曲のタグ分類レポート\n")
        f.write(f"生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for genre in genres:
            genre_df = df[df['ジャンル'] == genre]
            genre_df_unique = genre_df.drop_duplicates(subset=['曲', '歌手-ユニット'], keep='first')

            f.write(f"\n■ {genre}\n")
            f.write(f"  総出現回数: {len(genre_df)}回\n")
            f.write(f"  ユニーク曲数: {len(genre_df_unique)}曲\n\n")

            # 確度スコアが高い順にTOP5を表示
            top_songs = genre_df.sort_values('確度スコア', ascending=False).head(5)

            f.write("  代表曲（確度スコア順）:\n")
            for idx, (_, row) in enumerate(top_songs.iterrows(), 1):
                f.write(f"    {idx}. {row['曲']} / {row['歌手-ユニット']} (スコア: {row['確度スコア']})\n")

            f.write("\n" + "-" * 60 + "\n")

    print(f"詳細レポート: {report_file}")

    return stats_df

if __name__ == '__main__':
    # デフォルトの入力ファイル
    input_file = 'output/csv/song_timestamps_enhanced.csv'

    # ファイルが存在するか確認
    if not os.path.exists(input_file):
        print(f"エラー: {input_file} が見つかりません")
        exit(1)

    # タグ分類を実行
    print("曲のタグ分類を開始します...\n")
    stats = classify_songs_by_tag(input_file)

    print("\n" + "=" * 60)
    print("タグ分類が完了しました！")
    print("=" * 60)
