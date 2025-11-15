#!/usr/bin/env python3
"""
ジャンル分類ユーティリティ（JSON統合版）
"""

import json
import os
from typing import Dict, List, Optional

class GenreClassifier:
    """ジャンル分類クラス"""

    def __init__(self, config_path: str = "config/genre_keywords.json"):
        """
        初期化

        Args:
            config_path: ジャンルキーワード設定ファイルのパス
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.categories = self.config.get("categories", {})
        self.artist_mapping = self.config.get("artist_to_genre", {})

    def _load_config(self) -> Dict:
        """設定ファイルを読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: {self.config_path} が見つかりません。デフォルト設定を使用します")
            return self._default_config()
        except json.JSONDecodeError as e:
            print(f"警告: {self.config_path} の読み込みでエラー: {e}")
            return self._default_config()

    def _default_config(self) -> Dict:
        """デフォルト設定"""
        return {
            "categories": {
                "Vocaloid": {"keywords": ["初音ミク", "ボカロ", "vocaloid"]},
                "アニメ": {"keywords": ["アニメ", "anime", "OP", "ED"]},
                "J-POP": {"keywords": ["jpop", "j-pop"]},
                "その他": {"keywords": []}
            },
            "artist_to_genre": {}
        }

    def classify(self, artist: str, song_title: str = "") -> str:
        """
        アーティスト名と曲名からジャンルを判定

        Args:
            artist: アーティスト名
            song_title: 曲名（省略可）

        Returns:
            ジャンル文字列（Vocaloid/アニメ/J-POP/その他）
        """
        # 優先度1: アーティスト名の完全一致
        if artist in self.artist_mapping:
            return self.artist_mapping[artist]

        # 優先度2: キーワードマッチング
        search_text = f"{artist} {song_title}".lower()

        # Vocaloid判定（最優先）
        if self._check_category_match("Vocaloid", search_text):
            return "Vocaloid"

        # アニメ判定
        if self._check_category_match("アニメ", search_text):
            return "アニメ"

        # J-POP判定
        if self._check_category_match("J-POP", search_text):
            return "J-POP"

        # デフォルトは「その他」
        return "その他"

    def _check_category_match(self, category: str, search_text: str) -> bool:
        """
        カテゴリとのマッチングをチェック

        Args:
            category: カテゴリ名
            search_text: 検索対象テキスト

        Returns:
            マッチしたかどうか
        """
        if category not in self.categories:
            return False

        category_data = self.categories[category]

        # すべてのフィールドをチェック
        for field_name, field_values in category_data.items():
            if not isinstance(field_values, list):
                continue

            for keyword in field_values:
                if keyword.lower() in search_text:
                    return True

        return False

    def get_all_keywords(self, category: str) -> List[str]:
        """
        特定カテゴリの全キーワードを取得

        Args:
            category: カテゴリ名

        Returns:
            キーワードリスト
        """
        if category not in self.categories:
            return []

        all_keywords = []
        category_data = self.categories[category]

        for field_name, field_values in category_data.items():
            if isinstance(field_values, list):
                all_keywords.extend(field_values)

        return all_keywords

    def get_stats(self) -> Dict:
        """
        統計情報を取得

        Returns:
            統計情報辞書
        """
        stats = {
            "version": self.config.get("version", "unknown"),
            "categories": {},
            "artist_mappings": len(self.artist_mapping)
        }

        for category, data in self.categories.items():
            keyword_count = sum(
                len(v) for v in data.values() if isinstance(v, list)
            )
            stats["categories"][category] = keyword_count

        return stats

    def update_artist_mapping(self, artist: str, genre: str):
        """
        アーティストマッピングを更新（学習機能）

        Args:
            artist: アーティスト名
            genre: ジャンル
        """
        self.artist_mapping[artist] = genre

    def save_config(self, output_path: Optional[str] = None):
        """
        設定を保存

        Args:
            output_path: 出力先パス（指定しない場合は元のパスに上書き）
        """
        if output_path is None:
            output_path = self.config_path

        # 設定を更新
        self.config["artist_to_genre"] = self.artist_mapping

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

        print(f"設定を保存しました: {output_path}")


# 後方互換性のための関数
def detect_genre(title: str, artist: str) -> str:
    """
    ジャンルを自動判定（後方互換性用）

    Args:
        title: 曲名
        artist: アーティスト名

    Returns:
        ジャンル文字列
    """
    classifier = GenreClassifier()
    return classifier.classify(artist, title)


if __name__ == "__main__":
    # テスト
    classifier = GenreClassifier()

    print("ジャンル分類テスト")
    print("=" * 60)

    test_cases = [
        ("DECO*27", "ヴァンパイア"),
        ("米津玄師", "Lemon"),
        ("高橋洋子", "残酷な天使のテーゼ"),
        ("YOASOBI", "夜に駆ける"),
        ("Eve feat. 初音ミク", "トーキョーゲットー"),
        ("Official髭男dism", "Pretender"),
        ("King Gnu", "白日"),
    ]

    for artist, song in test_cases:
        genre = classifier.classify(artist, song)
        print(f"{artist} / {song}")
        print(f"  → {genre}\n")

    # 統計表示
    print("\n統計情報")
    print("=" * 60)
    stats = classifier.get_stats()
    print(f"バージョン: {stats['version']}")
    print(f"アーティストマッピング数: {stats['artist_mappings']}")
    print("\nカテゴリ別キーワード数:")
    for category, count in stats['categories'].items():
        print(f"  {category}: {count}")
