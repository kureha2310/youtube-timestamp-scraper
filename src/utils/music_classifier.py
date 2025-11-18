#!/usr/bin/env python3
"""
音楽タイムスタンプ判別モジュール
曲かどうかを判定し、アーティスト情報を補完する
"""

import re
import time
import requests
from typing import Optional, Dict


class MusicClassifier:
    """音楽タイムスタンプの判別と補完を行うクラス"""

    # 歌以外のキーワード（これらが含まれる場合は「その他」と判定）
    NON_MUSIC_KEYWORDS = [
        '待機', '開始', '終了', '配信', '雑談', 'ゲーム', 'スタート', 'エンディング',
        'お知らせ', 'トーク', '休憩', '終わり', 'おわり', 'はじまり', '始まり',
        'クリア', 'ミッション', 'ステージ', 'レベル', 'チャプター', 'パート',
        '質問', 'Q&A', 'マシュマロ', 'スパチャ', 'コメント', '返信',
        '自己紹介', '挨拶', 'あいさつ', 'ルール', '説明',
        '企画', 'コラボ', 'お便り', 'おたより', '告知',
        '読み上げ', '紹介', 'しょうかい', '参加', 'さんか',
        '登場', 'とうじょう', '出演', 'しゅつえん',
        # 追加: 雑談・説明系
        'の話', 'について', 'とは', '〜とは', '紹介', '募集', '決め',
        # 追加: ラーメン・食べ物系
        'ラーメン', '中華そば', 'そば', 'つけ麺', '製麺', 'スープ', '店舗',
        '博物館', '食堂', 'カップ麺', '背脂', '味玉', 'どんぶり',
        # 追加: ゲーム系
        '昇格', '対決', '拡張', '初', 'part', 'パート', 'ルーレット',
        'マイク', '事情', '活用', '方法', '確認', 'タグ',
        # 追加: 状態・行動
        '声入り', '寝起き', '意気込み', '披露', 'フラグ', '回収',
        '再生', '同時視聴', '記念', 'マロ', 'ましゅまろ',
        # 追加: 短い一般語
        '可愛い', 'かわいい', 'かわちい', 'うわー', 'いやー', 'にゃ',
        'おっけい', 'loading', 'Zzz',
    ]

    # 「〜の話」「〜について」などのパターン（正規表現）
    NON_MUSIC_PATTERNS = [
        r'.+の話$',
        r'.+について$',
        r'.+とは？?$',
        r'.+事情$',
        r'.+方法$',
        r'part\s*\d+',
        r'パート\s*\d+',
        r'ルーレット',
        r'^声入り',
        r'削る$',
        r'^問目',
        r'^枚目',
    ]

    def __init__(self, request_delay: float = 3.0):
        """
        Args:
            request_delay: iTunes APIリクエスト間の待機秒数（デフォルト3秒）
        """
        self.request_delay = request_delay
        self.last_request_time = 0

    def _contains_non_music_keyword(self, title: str) -> bool:
        """タイトルに歌以外のキーワードが含まれるかチェック"""
        title_lower = title.lower()

        # キーワードチェック
        for keyword in self.NON_MUSIC_KEYWORDS:
            if keyword in title_lower:
                return True

        # パターンチェック（正規表現）
        for pattern in self.NON_MUSIC_PATTERNS:
            if re.search(pattern, title_lower):
                return True

        # 短すぎるタイトル（3文字以下）は除外
        if len(title.strip()) <= 3:
            return True

        # 絵文字だらけのタイトルは除外
        emoji_count = sum(1 for c in title if ord(c) > 0x1F000)
        if emoji_count > len(title) * 0.3:  # 30%以上が絵文字
            return True

        return False

    def search_itunes(self, song_title: str) -> Optional[Dict[str, str]]:
        """
        iTunes APIで曲を検索してアーティスト情報を取得

        Args:
            song_title: 検索する曲名

        Returns:
            見つかった場合: {'artist': 'アーティスト名', 'track': '曲名'}
            見つからない場合: None
        """
        # レート制限対策: 前回のリクエストから一定時間待機
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)

        try:
            url = "https://itunes.apple.com/search"
            params = {
                "term": song_title,
                "media": "music",
                "entity": "song",
                "limit": 3,
                "country": "JP",  # 日本のストアを優先
            }

            response = requests.get(url, params=params, timeout=10)
            self.last_request_time = time.time()

            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get('results', [])

            if not results:
                return None

            # 最初の結果を返す
            first_result = results[0]
            return {
                'artist': first_result.get('artistName', ''),
                'track': first_result.get('trackName', song_title)
            }

        except Exception as e:
            print(f"  [!] iTunes API検索エラー: {e}")
            return None

    def classify_timestamp(self, song_title: str, artist: str, use_itunes: bool = True) -> Dict[str, any]:
        """
        タイムスタンプが歌かどうかを判別し、必要に応じてアーティスト情報を補完

        Args:
            song_title: 曲名
            artist: アーティスト名（空文字列の場合あり）
            use_itunes: iTunes APIを使用するか

        Returns:
            {
                'is_music': bool,  # 歌かどうか
                'artist': str,     # 補完されたアーティスト名（元のままの場合もあり）
                'title': str,      # 曲名（必要に応じて補完）
                'source': str      # 'original' / 'itunes' / 'keyword_check'
            }
        """
        # アーティスト名がある場合は歌として扱う
        if artist and artist.strip():
            return {
                'is_music': True,
                'artist': artist,
                'title': song_title,
                'source': 'original'
            }

        # アーティスト名がない場合
        # 1. キーワードチェック（歌以外のキーワードが含まれる？）
        if self._contains_non_music_keyword(song_title):
            return {
                'is_music': False,
                'artist': '',
                'title': song_title,
                'source': 'keyword_check'
            }

        # 2. iTunes APIで検索（use_itunesがTrueの場合のみ）
        if use_itunes:
            try:
                print(f"  [iTunes検索] {song_title}")
            except UnicodeEncodeError:
                print(f"  [iTunes検索] [encoding error]")
            result = self.search_itunes(song_title)

            if result:
                try:
                    print(f"    → 見つかりました: {result['artist']}")
                except UnicodeEncodeError:
                    print(f"    → 見つかりました")
                return {
                    'is_music': True,
                    'artist': result['artist'],
                    'title': result['track'],
                    'source': 'itunes'
                }
            else:
                print(f"    → 見つかりませんでした")

        # 3. iTunes APIでも見つからない → デフォルトで歌として扱う（アーティスト不明）
        return {
            'is_music': True,
            'artist': '',
            'title': song_title,
            'source': 'not_found'
        }


if __name__ == "__main__":
    # テスト
    classifier = MusicClassifier()

    test_cases = [
        ("紅蓮華", "LiSA"),  # アーティストあり
        ("紅蓮華", ""),       # アーティストなし（iTunes検索される）
        ("配信開始", ""),     # 歌以外
        ("待機画面", ""),     # 歌以外
    ]

    print("=== テスト実行 ===\n")
    for title, artist in test_cases:
        print(f"入力: {title} / {artist}")
        result = classifier.classify_timestamp(title, artist, use_itunes=True)
        print(f"結果: {result}\n")
