#!/usr/bin/env python3
"""
YouTubeタイムスタンプ抽出ツール - メインスクリプト
使い方に応じて適切な機能を選択できます
"""

import sys
import json
import os
from typing import Optional
from dotenv import load_dotenv

def show_menu():
    """メニューを表示"""
    print("\n" + "="*60)
    print("YouTube タイムスタンプ抽出ツール")
    print("="*60)
    print("1. 単一動画のタイムスタンプ抽出")
    print("2. チャンネル選択してスクレイプ (NEW!)")
    print("3. チャンネル一括抽出（全チャンネル）")
    print("4. トランスクリプトのみ抽出")
    print("5. 一括トランスクリプト抽出")
    print("6. チャンネル管理 (追加/削除/一覧)")
    print("7. 設定ファイル確認/作成")
    print("0. 終了")
    print("="*60)

def check_api_key() -> bool:
    """APIキーの存在確認"""
    load_dotenv()
    api_key = os.getenv('API_KEY')
    if not api_key:
        print("\n[!] エラー: .envファイルにAPI_KEYが設定されていません")
        print("YouTube Data API v3のAPIキーを取得して設定してください")
        print("\n設定方法:")
        print("1. .envファイルを作成")
        print("2. API_KEY=あなたのAPIキー を追加")
        return False
    print(f"[OK] APIキー確認済み: {api_key[:10]}...")
    return True

def check_config_files():
    """設定ファイルの確認/作成"""
    print("\n設定ファイルを確認中...")
    
    # config.json
    if not os.path.exists('config.json'):
        print("config.jsonを作成中...")
        config_data = {
            "singing_detection": {
                "include_keywords": ["歌", "うた", "歌枠", "カラオケ", "music", "song", "singing"],
                "exclude_keywords": ["ゲーム", "雑談", "料理", "game", "chat"],
                "bonus_patterns": ["[歌うたウタ]", "[歌枠うたわく]"],
                "minimum_score": 2,
                "minimum_score_override": 4
            },
            "timestamp_extraction": {
                "patterns": {
                    "plain_timestamp": r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:：・･]?\s*(.+?)(?=\n|\d{1,2}:\d{2}|$)",
                    "flexible_timestamp": r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[）)]\s*(.+?)(?=\n|$)",
                    "japanese_timestamp": r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[：・]\s*(.+?)(?=\n|$)"
                }
            },
            "text_cleaning": {
                "normalize_chars": {
                    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
                    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
                    "（": "(", "）": ")", "［": "[", "］": "]"
                },
                "numbering_patterns": [
                    r"^\d+\.\s*",
                    r"^\d+\)\s*",
                    r"^\d+[-–—]\s*",
                    r"^第?\d+[曲首]\s*"
                ]
            },
            "genres": {
                "vocaloid": {
                    "artists": ["初音ミク", "鏡音リン", "鏡音レン", "巡音ルカ", "MEIKO", "KAITO", "IA", "GUMI"],
                    "producers": ["ボカロP", "DECO*27", "ハチ", "米津玄師"],
                    "keywords": ["ボカロ", "vocaloid", "ミク", "ボーカロイド"]
                },
                "anime": {
                    "keywords": ["アニメ", "anime", "OP", "ED", "主題歌", "挿入歌"],
                    "titles": ["残酷な天使のテーゼ", "God knows", "only my railgun"]
                },
                "jpop": {
                    "artists": ["YOASOBI", "あいみょん", "米津玄師", "LiSA"],
                    "keywords": ["jpop", "j-pop", "ポップス"]
                }
            },
            "api": {
                "max_results_per_request": 50,
                "max_comments_per_video": 100,
                "retry_delay": 1.0
            }
        }
        
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        print("[OK] config.json を作成しました")
    else:
        print("[OK] config.json が存在します")
    
    # user_ids.json
    if not os.path.exists('user_ids.json'):
        print("user_ids.jsonを作成中...")
        sample_users = [
            "UCxxxxxxxxxxxxxxxxxxxxxx"  # サンプルチャンネルID
        ]
        with open('user_ids.json', 'w', encoding='utf-8') as f:
            json.dump(sample_users, f, ensure_ascii=False, indent=2)
        print("[OK] user_ids.json を作成しました（サンプル）")
        print("   実際のチャンネルIDに編集してください")
    else:
        with open('user_ids.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        print(f"[OK] user_ids.json が存在します（{len(users)}チャンネル）")

def run_single_video():
    """単一動画のタイムスタンプ抽出"""
    if not check_api_key():
        return
    
    print("\n単一動画のタイムスタンプ抽出を開始します...")
    
    # 動画URLまたは動画IDの入力
    video_input = input("\n動画URLまたは動画IDを入力してください: ").strip()
    
    if not video_input:
        print("動画URLまたはIDが入力されていません")
        return
    
    # 動画IDを抽出
    video_id = extract_video_id(video_input)
    if not video_id:
        print("無効な動画URLまたはIDです")
        return
    
    print(f"動画ID: {video_id}")
    
    # 話題分析オプション
    analyze_topics = input("\n字幕から話題も分析しますか？ (y/N): ").strip().lower() == 'y'
    
    try:
        from src.extractors.single_video_extractor import SingleVideoExtractor
        extractor = SingleVideoExtractor()
        extractor.extract_video_timestamps(video_id, analyze_topics=analyze_topics)
    except ImportError:
        print("single_video_extractor.py が見つかりません")
        print("   このスクリプトを作成する必要があります")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

def extract_video_id(video_input: str) -> Optional[str]:
    """動画URLまたはIDから動画IDを抽出"""
    video_input = video_input.strip()
    
    # 既に動画IDの形式の場合
    if len(video_input) == 11 and video_input.isalnum():
        return video_input
    
    # YouTube URLの場合
    import re
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'[?&]v=([a-zA-Z0-9_-]{11})',
        r'/([a-zA-Z0-9_-]{11})(?:\?|&|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_input)
        if match:
            return match.group(1)
    
    return None

def run_bulk_extraction():
    """チャンネル一括抽出（強化版）"""
    if not check_api_key():
        return
    
    print("\nチャンネル一括抽出（強化版）を開始します...")
    
    try:
        from src.extractors.youtube_scraper_enhanced import main
        main()
    except ImportError as e:
        print(f"[!] youtube_scraper_enhanced.py が見つかりません: {e}")
    except Exception as e:
        print(f"[!] エラーが発生しました: {e}")

def run_transcript_only():
    """トランスクリプトのみ抽出"""
    if not check_api_key():
        return
    
    print("\nトランスクリプトのみ抽出を開始します...")
    
    try:
        from src.extractors.transcript_only_scraper import main
        main()
    except ImportError:
        print("[!] transcript_only_scraper.py が見つかりません")
    except Exception as e:
        print(f"[!] エラーが発生しました: {e}")

def run_bulk_transcript():
    """一括トランスクリプト抽出"""
    if not check_api_key():
        return

    print("\n一括トランスクリプト抽出を開始します...")

    try:
        from src.extractors.bulk_transcript_scraper import main
        main()
    except ImportError:
        print("[!] bulk_transcript_scraper.py が見つかりません")
    except Exception as e:
        print(f"[!] エラーが発生しました: {e}")

def run_channel_scrape():
    """チャンネル選択してスクレイプ"""
    if not check_api_key():
        return

    print("\nチャンネルを選択してスクレイプを開始します...")

    try:
        from src.utils.channel_manager import select_channels
        from src.extractors.youtube_song_scraper import scrape_channels

        # チャンネル選択
        selected_channels = select_channels()

        if not selected_channels:
            return

        # 選択したチャンネルをスクレイプ
        channel_ids = [ch['channel_id'] for ch in selected_channels]
        scrape_channels(channel_ids)

    except ImportError as e:
        print(f"[!] モジュールが見つかりません: {e}")
    except Exception as e:
        print(f"[!] エラーが発生しました: {e}")

def manage_channels():
    """チャンネル管理メニュー"""
    from src.utils.channel_manager import (
        list_channels, add_channel, remove_channel, toggle_channel
    )

    while True:
        print("\n" + "="*60)
        print("[*] チャンネル管理")
        print("="*60)
        print("1. チャンネル一覧表示")
        print("2. チャンネル追加")
        print("3. チャンネル削除")
        print("4. チャンネル有効/無効切り替え")
        print("0. 戻る")
        print("="*60)

        choice = input("\n選択してください (0-4): ").strip()

        if choice == "0":
            break
        elif choice == "1":
            list_channels()
        elif choice == "2":
            name = input("\nチャンネル名を入力: ").strip()
            channel_id = input("チャンネルIDを入力: ").strip()
            if name and channel_id:
                add_channel(name, channel_id)
            else:
                print("[!] 名前とIDを入力してください")
        elif choice == "3":
            channel_id = input("\n削除するチャンネルIDを入力: ").strip()
            if channel_id:
                remove_channel(channel_id)
            else:
                print("[!] チャンネルIDを入力してください")
        elif choice == "4":
            channel_id = input("\n切り替えるチャンネルIDを入力: ").strip()
            if channel_id:
                toggle_channel(channel_id)
            else:
                print("[!] チャンネルIDを入力してください")
        else:
            print("[!] 無効な選択です")

        input("\nEnterキーを押して続行...")

def main():
    """メイン関数"""
    while True:
        show_menu()

        try:
            choice = input("\n選択してください (0-7): ").strip()
        except KeyboardInterrupt:
            print("\n\n 終了します")
            break

        if choice == "0":
            print("\n 終了します")
            break
        elif choice == "1":
            run_single_video()
        elif choice == "2":
            run_channel_scrape()
        elif choice == "3":
            run_bulk_extraction()
        elif choice == "4":
            run_transcript_only()
        elif choice == "5":
            run_bulk_transcript()
        elif choice == "6":
            manage_channels()
        elif choice == "7":
            check_config_files()
        else:
            print("[!] 無効な選択です。0-7を入力してください。")

        input("\nEnterキーを押して続行...")

if __name__ == "__main__":
    main()