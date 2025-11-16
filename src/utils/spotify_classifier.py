#!/usr/bin/env python3
"""
Spotify APIを使ったジャンル自動判定
"""

import json
import os
from typing import Optional, List, Dict
import time

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    print("警告: spotipy がインストールされていません。pip install spotipy を実行してください")


class SpotifyGenreClassifier:
    """Spotify APIを使ったジャンル分類"""

    # Spotifyのジャンルを独自ジャンルにマッピング
    GENRE_MAPPING = {
        # Vocaloid
        'vocaloid': 'Vocaloid',
        'anime': 'アニメ',
        'anime score': 'アニメ',
        'anime rock': 'アニメ',
        'anime rap': 'アニメ',

        # ゲーム
        'video game music': 'ゲーム音楽',
        'game': 'ゲーム音楽',

        # J-POP
        'j-pop': 'J-POP',
        'japanese pop': 'J-POP',
        'jpop': 'J-POP',
        'j-poprock': 'J-POP',

        # ロック
        'j-rock': 'ロック',
        'japanese rock': 'ロック',
        'rock': 'ロック',
        'alternative rock': 'ロック',
        'punk': 'パンク',
        'punk rock': 'パンク',
        'j-punk': 'パンク',

        # オルタナティブ
        'alternative': 'オルタナティブ',
        'indie': 'オルタナティブ',
        'indie rock': 'オルタナティブ',
        'j-indie': 'オルタナティブ',

        # バラード（判定が難しいので後回し）
        'ballad': 'バラード',

        # R&B/ソウル
        'r&b': 'R&B/ソウル',
        'soul': 'R&B/ソウル',
        'j-r&b': 'R&B/ソウル',

        # エレクトロニック
        'electronic': 'エレクトロニック',
        'edm': 'エレクトロニック',
        'electro': 'エレクトロニック',
        'techno': 'エレクトロニック',
        'house': 'エレクトロニック',

        # シティポップ
        'city pop': 'シティポップ',
        'shibuya-kei': 'シティポップ',

        # フォーク
        'folk': 'フォーク',
        'acoustic': 'フォーク',
    }

    def __init__(self, cache_path: str = "config/spotify_cache.json"):
        """
        初期化

        Args:
            cache_path: キャッシュファイルのパス
        """
        self.cache_path = cache_path
        self.cache = self._load_cache()
        self.sp = None

        if SPOTIFY_AVAILABLE:
            self._init_spotify()

    def _init_spotify(self):
        """Spotify APIクライアントを初期化"""
        try:
            # 環境変数から認証情報を取得
            client_id = os.getenv('SPOTIFY_CLIENT_ID')
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

            if not client_id or not client_secret:
                print("警告: SPOTIFY_CLIENT_ID と SPOTIFY_CLIENT_SECRET を環境変数に設定してください")
                print("詳細: https://developer.spotify.com/dashboard")
                return

            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            print("[OK] Spotify API接続成功")

        except Exception as e:
            print(f"警告: Spotify API初期化エラー: {e}")
            self.sp = None

    def _load_cache(self) -> Dict:
        """キャッシュを読み込む"""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告: キャッシュ読み込みエラー: {e}")

        return {}

    def _save_cache(self):
        """キャッシュを保存"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"警告: キャッシュ保存エラー: {e}")

    def get_genre_from_spotify(self, artist: str, song_title: str = "") -> Optional[str]:
        """
        Spotify APIからジャンル情報を取得

        Args:
            artist: アーティスト名
            song_title: 曲名（オプション）

        Returns:
            ジャンル文字列（見つからない場合はNone）
        """
        if not self.sp:
            return None

        # キャッシュチェック
        cache_key = f"{artist}||{song_title}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # レート制限対策
            time.sleep(0.1)

            # 曲名があれば詳細検索、なければアーティスト検索
            if song_title:
                query = f"artist:{artist} track:{song_title}"
                results = self.sp.search(q=query, type='track', limit=1)

                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    artist_id = track['artists'][0]['id']
                else:
                    # 曲が見つからない場合はアーティストのみで検索
                    return self._search_by_artist(artist, cache_key)
            else:
                return self._search_by_artist(artist, cache_key)

            # アーティスト情報からジャンル取得
            artist_info = self.sp.artist(artist_id)
            spotify_genres = artist_info.get('genres', [])

            if not spotify_genres:
                self.cache[cache_key] = None
                return None

            # ジャンルマッピング
            mapped_genre = self._map_spotify_genres(spotify_genres)

            # キャッシュに保存
            self.cache[cache_key] = mapped_genre
            self._save_cache()

            return mapped_genre

        except Exception as e:
            print(f"  エラー: {artist} / {song_title} - {e}")
            return None

    def _search_by_artist(self, artist: str, cache_key: str) -> Optional[str]:
        """アーティスト名のみで検索"""
        try:
            results = self.sp.search(q=f"artist:{artist}", type='artist', limit=1)

            if not results['artists']['items']:
                self.cache[cache_key] = None
                return None

            artist_info = results['artists']['items'][0]
            spotify_genres = artist_info.get('genres', [])

            if not spotify_genres:
                self.cache[cache_key] = None
                return None

            mapped_genre = self._map_spotify_genres(spotify_genres)
            self.cache[cache_key] = mapped_genre
            self._save_cache()

            return mapped_genre

        except Exception as e:
            print(f"  エラー: {artist} - {e}")
            return None

    def _map_spotify_genres(self, spotify_genres: List[str]) -> Optional[str]:
        """
        Spotifyのジャンルリストを独自ジャンルにマッピング

        Args:
            spotify_genres: Spotifyのジャンルリスト

        Returns:
            マッピングされたジャンル（見つからない場合はNone）
        """
        # 優先度順にチェック（最初にマッチしたものを返す）
        priority_order = [
            'Vocaloid', 'アニメ', 'ゲーム音楽',
            'パンク', 'ロック', 'オルタナティブ',
            'シティポップ', 'R&B/ソウル', 'エレクトロニック',
            'フォーク', 'バラード', 'J-POP'
        ]

        # 各Spotifyジャンルをチェック
        for spotify_genre in spotify_genres:
            genre_lower = spotify_genre.lower()

            # マッピングテーブルから検索
            if genre_lower in self.GENRE_MAPPING:
                return self.GENRE_MAPPING[genre_lower]

            # 部分一致チェック
            for key, value in self.GENRE_MAPPING.items():
                if key in genre_lower or genre_lower in key:
                    return value

        return None

    def get_cache_stats(self) -> Dict:
        """キャッシュ統計を取得"""
        genre_counts = {}
        for genre in self.cache.values():
            if genre:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1

        return {
            'total_cached': len(self.cache),
            'found': sum(1 for v in self.cache.values() if v is not None),
            'not_found': sum(1 for v in self.cache.values() if v is None),
            'by_genre': genre_counts
        }


if __name__ == "__main__":
    # テスト
    classifier = SpotifyGenreClassifier()

    if not classifier.sp:
        print("\n環境変数の設定方法:")
        print("=" * 60)
        print("Windows (PowerShell):")
        print('  $env:SPOTIFY_CLIENT_ID="your_client_id"')
        print('  $env:SPOTIFY_CLIENT_SECRET="your_client_secret"')
        print("\nWindows (コマンドプロンプト):")
        print('  set SPOTIFY_CLIENT_ID=your_client_id')
        print('  set SPOTIFY_CLIENT_SECRET=your_client_secret')
        print("\nLinux/Mac:")
        print('  export SPOTIFY_CLIENT_ID="your_client_id"')
        print('  export SPOTIFY_CLIENT_SECRET="your_client_secret"')
        print("=" * 60)
    else:
        print("\nSpotify API テスト")
        print("=" * 60)

        test_cases = [
            ("YOASOBI", "夜に駆ける"),
            ("米津玄師", "Lemon"),
            ("Official髭男dism", "Pretender"),
            ("King Gnu", "白日"),
            ("SHISHAMO", "明日も"),
        ]

        for artist, song in test_cases:
            genre = classifier.get_genre_from_spotify(artist, song)
            print(f"{artist} / {song}")
            print(f"  → {genre if genre else '見つかりませんでした'}\n")

        # 統計表示
        stats = classifier.get_cache_stats()
        print("\nキャッシュ統計")
        print("=" * 60)
        print(f"キャッシュ件数: {stats['total_cached']}")
        print(f"  見つかった: {stats['found']}")
        print(f"  見つからなかった: {stats['not_found']}")
