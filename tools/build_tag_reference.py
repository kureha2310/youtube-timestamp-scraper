import pandas as pd
import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime

# GenreClassifierをインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from utils.genre_classifier import GenreClassifier

def build_tag_reference(input_file='output/csv/song_timestamps_enhanced.csv'):
    """
    既存データからタグ判定用の参照リストを構築し、genre_keywords.jsonを更新
    """
    print(f"CSVファイルを読み込み中: {input_file}")

    # データ読み込み
    df = pd.read_csv(input_file, encoding='utf-8-sig')

    # アーティスト → タグのマッピング
    artist_to_tag = {}
    artist_tag_counts = defaultdict(Counter)

    for _, row in df.iterrows():
        artist = row['歌手-ユニット']
        tag = row['ジャンル']
        artist_tag_counts[artist][tag] += 1

    # 各アーティストで最も多いタグを採用
    for artist, tag_counts in artist_tag_counts.items():
        most_common_tag = tag_counts.most_common(1)[0][0]
        artist_to_tag[artist] = most_common_tag

    # タグごとのアーティストリスト
    tag_to_artists = defaultdict(list)
    for artist, tag in artist_to_tag.items():
        tag_to_artists[tag].append(artist)

    # 統計情報
    stats = {
        '総アーティスト数': len(artist_to_tag),
        'タグ別アーティスト数': {tag: len(artists) for tag, artists in tag_to_artists.items()},
        '生成日時': datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    }

    print(f"\n統計:")
    print(f"  総アーティスト数: {stats['総アーティスト数']}")
    for tag, count in stats['タグ別アーティスト数'].items():
        print(f"  {tag}: {count}アーティスト")

    # GenreClassifierを使って既存のgenre_keywords.jsonを更新
    classifier = GenreClassifier()

    # 学習したアーティストマッピングをマージ
    for artist, tag in artist_to_tag.items():
        classifier.update_artist_mapping(artist, tag)

    # 更新した設定を保存
    classifier.save_config()

    print(f"\ngenre_keywords.json のアーティストマッピングを更新しました")

    # 結果をまとめる（後方互換性のため）
    reference_data = {
        'artist_to_tag': artist_to_tag,
        'tag_to_artists': dict(tag_to_artists),
        'stats': stats
    }

    return reference_data

def save_as_json(data, output_file='config/tag_reference.json'):
    """JSONファイルとして保存"""
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"JSONファイル保存: {output_file}")

def save_as_python(data, output_file='config/tag_reference.py'):
    """Pythonファイルとして保存（直接importできる形式）"""
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('# -*- coding: utf-8 -*-\n')
        f.write(f"# タグ判定用参照データ\n")
        f.write(f"# 生成日時: {data['stats']['生成日時']}\n\n")

        # アーティスト→タグ辞書
        f.write('# アーティスト名からタグを判定\n')
        f.write('ARTIST_TO_TAG = {\n')
        for artist, tag in sorted(data['artist_to_tag'].items()):
            f.write(f'    "{artist}": "{tag}",\n')
        f.write('}\n\n')

        # タグ→アーティストリスト
        f.write('# タグごとのアーティスト一覧\n')
        f.write('TAG_TO_ARTISTS = {\n')
        for tag, artists in data['tag_to_artists'].items():
            f.write(f'    "{tag}": [\n')
            for artist in sorted(artists):
                f.write(f'        "{artist}",\n')
            f.write('    ],\n')
        f.write('}\n\n')

        # キーワードルール
        f.write('# キーワードベースの判定ルール\n')
        f.write('KEYWORD_RULES = {\n')
        for tag, keywords in data['keyword_rules'].items():
            f.write(f'    "{tag}": [\n')
            for keyword in keywords:
                f.write(f'        "{keyword}",\n')
            f.write('    ],\n')
        f.write('}\n\n')

        # 判定関数
        f.write('# タグ判定関数\n')
        f.write('def get_tag(artist_name, song_name=""):\n')
        f.write('    """\n')
        f.write('    アーティスト名と曲名からタグを判定\n')
        f.write('    \n')
        f.write('    Args:\n')
        f.write('        artist_name: アーティスト名\n')
        f.write('        song_name: 曲名（省略可）\n')
        f.write('    \n')
        f.write('    Returns:\n')
        f.write('        タグ文字列（Vocaloid/J-POP/アニメ/その他）\n')
        f.write('    """\n')
        f.write('    # まずアーティスト名で完全一致検索\n')
        f.write('    if artist_name in ARTIST_TO_TAG:\n')
        f.write('        return ARTIST_TO_TAG[artist_name]\n')
        f.write('    \n')
        f.write('    # キーワードベースで判定\n')
        f.write('    search_text = f"{artist_name} {song_name}"\n')
        f.write('    for tag, keywords in KEYWORD_RULES.items():\n')
        f.write('        for keyword in keywords:\n')
        f.write('            if keyword in search_text:\n')
        f.write('                return tag\n')
        f.write('    \n')
        f.write('    # デフォルトは「その他」\n')
        f.write('    return "その他"\n')

    print(f"Pythonファイル保存: {output_file}")

if __name__ == '__main__':
    print("タグ判定用参照データを構築中...\n")
    print("=" * 60)

    # データ構築（genre_keywords.jsonを自動更新）
    reference_data = build_tag_reference()

    # 統計表示
    print("\n" + "=" * 60)
    print("構築完了！")
    print("=" * 60)

    # 後方互換性のために旧形式のJSONとPythonファイルも保存
    print("\n後方互換性のために旧形式ファイルも保存します...")
    save_as_json(reference_data)
    save_as_python(reference_data)

    print("\n" + "=" * 60)
    print("使用例:")
    print("  from src.utils.genre_classifier import GenreClassifier")
    print("  classifier = GenreClassifier()")
    print('  genre = classifier.classify("DECO*27", "ヴァンパイア")')
    print('  print(genre)  # => "Vocaloid"')
    print("\n  または後方互換:")
    print("  from config.tag_reference import get_tag")
    print('  tag = get_tag("DECO*27", "ヴァンパイア")')
    print('  print(tag)  # => "Vocaloid"')
    print("=" * 60)
