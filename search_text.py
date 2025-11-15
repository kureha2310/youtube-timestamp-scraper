#!/usr/bin/env python3
"""
YouTubeチャンネル内 文字列検索ツール
チャンネルIDと検索文字列を指定して、コメント・字幕・ライブチャットから検索
"""

import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from extractors.text_search_extractor import TextSearchExtractor


def print_banner():
    """バナー表示"""
    print("\n" + "="*70)
    print("  YouTube チャンネル内 文字列検索ツール")
    print("="*70 + "\n")


def print_usage():
    """使い方を表示"""
    print("使い方:")
    print("  1. 対話モード (推奨):")
    print("     python search_text.py")
    print()
    print("  2. コマンドライン引数モード:")
    print("     python search_text.py <チャンネルID> <検索文字列> [オプション]")
    print()
    print("オプション:")
    print("  --comments     コメントのみ検索")
    print("  --transcripts  字幕のみ検索")
    print("  --all         すべて検索 (コメント + 字幕)")
    print("  --max-videos N  検索する動画数 (デフォルト: 50)")
    print()
    print("例:")
    print('  python search_text.py UCxxxxx "検索したい文字列" --all --max-videos 100')
    print()


def interactive_mode():
    """対話モード"""
    print_banner()

    try:
        extractor = TextSearchExtractor()

        # チャンネルID入力
        print("チャンネルIDを入力してください:")
        print("(例: UCxxxxxxxxxxxxxxxxxxxxxx)")
        channel_id = input("> ").strip()

        if not channel_id:
            print("[!] チャンネルIDが入力されていません")
            return

        # 検索文字列入力
        print("\n検索する文字列を入力してください:")
        print("(例: 特定の曲名、用語、フレーズなど)")
        search_text = input("> ").strip()

        if not search_text:
            print("[!] 検索文字列が入力されていません")
            return

        # 検索対象選択
        print("\n検索対象を選択してください:")
        print("1. コメント")
        print("2. 字幕")
        print("3. コメント + 字幕 (推奨)")
        print("4. すべて (コメント + 字幕 + ライブチャット)")

        choice = input("> ").strip()

        if choice not in ['1', '2', '3', '4']:
            print("[!] 無効な選択です。デフォルト (3. コメント + 字幕) で実行します")
            choice = '3'

        search_comments = choice in ['1', '3', '4']
        search_transcripts = choice in ['2', '3', '4']
        search_live_chat = choice == '4'

        # 検索する動画数
        print("\n検索する動画数を入力してください:")
        print("(推奨: 50, 最大: 500)")
        max_videos_input = input("> ").strip()

        try:
            max_videos = int(max_videos_input) if max_videos_input else 50
            if max_videos <= 0:
                max_videos = 50
            if max_videos > 500:
                print("[!] 最大500件までです。500件で実行します")
                max_videos = 500
        except ValueError:
            print("[!] 無効な数値です。デフォルト (50) で実行します")
            max_videos = 50

        # 確認
        print("\n" + "="*70)
        print("[*] 検索条件")
        print("="*70)
        print(f"  チャンネルID: {channel_id}")
        print(f"  検索文字列: {search_text}")
        print(f"  検索対象: ", end='')
        targets = []
        if search_comments:
            targets.append("コメント")
        if search_transcripts:
            targets.append("字幕")
        if search_live_chat:
            targets.append("ライブチャット")
        print(", ".join(targets))
        print(f"  検索動画数: 最大{max_videos}件")
        print("="*70)

        print("\nこの条件で検索を開始しますか？ (y/N)")
        confirm = input("> ").strip().lower()

        if confirm != 'y':
            print("[!] キャンセルしました")
            return

        # 検索実行
        results = extractor.search_channel(
            channel_id=channel_id,
            search_text=search_text,
            search_comments=search_comments,
            search_transcripts=search_transcripts,
            search_live_chat=search_live_chat,
            max_videos=max_videos
        )

        # 結果保存
        if results:
            extractor.save_to_csv(results)

            # 結果をプレビュー表示
            print("\n[*] 検索結果プレビュー (最初の5件):")
            print("-" * 70)
            for i, result in enumerate(results[:5], 1):
                source_map = {
                    'comment': 'コメント',
                    'transcript': '字幕',
                    'live_chat': 'ライブチャット'
                }
                source_jp = source_map.get(result.source_type, result.source_type)

                print(f"\n{i}. {result.video_title[:60]}")
                print(f"   検索元: {source_jp} | タイムスタンプ: {result.timestamp}")
                print(f"   コンテキスト: {result.context[:80]}...")
                print(f"   URL: {result.video_url}")

            if len(results) > 5:
                print(f"\n   ... 他 {len(results) - 5} 件")

            print("\n[OK] 完了しました！")
        else:
            print("\n[!] 該当する結果が見つかりませんでした")

    except KeyboardInterrupt:
        print("\n\n[!] 中断されました")
    except Exception as e:
        print(f"\n[!] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def command_line_mode(args):
    """コマンドライン引数モード"""
    if len(args) < 2:
        print("[!] エラー: チャンネルIDと検索文字列が必要です")
        print()
        print_usage()
        return

    channel_id = args[0]
    search_text = args[1]

    # オプション解析
    search_comments = True
    search_transcripts = True
    search_live_chat = False
    max_videos = 50

    i = 2
    while i < len(args):
        arg = args[i]

        if arg == '--comments':
            search_comments = True
            search_transcripts = False
            search_live_chat = False
        elif arg == '--transcripts':
            search_comments = False
            search_transcripts = True
            search_live_chat = False
        elif arg == '--all':
            search_comments = True
            search_transcripts = True
            search_live_chat = False
        elif arg == '--max-videos':
            if i + 1 < len(args):
                try:
                    max_videos = int(args[i + 1])
                    i += 1
                except ValueError:
                    print(f"[!] 警告: 無効な --max-videos 値: {args[i + 1]}")
            else:
                print("[!] 警告: --max-videos には値が必要です")
        elif arg == '--help':
            print_usage()
            return
        else:
            print(f"[!] 警告: 不明なオプション: {arg}")

        i += 1

    # 検索実行
    try:
        print_banner()
        extractor = TextSearchExtractor()

        results = extractor.search_channel(
            channel_id=channel_id,
            search_text=search_text,
            search_comments=search_comments,
            search_transcripts=search_transcripts,
            search_live_chat=search_live_chat,
            max_videos=max_videos
        )

        if results:
            extractor.save_to_csv(results)
            print("\n[OK] 完了しました！")
        else:
            print("\n[!] 該当する結果が見つかりませんでした")

    except Exception as e:
        print(f"\n[!] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def main():
    """メイン関数"""
    args = sys.argv[1:]

    if not args or args[0] == '--help':
        # 対話モード
        interactive_mode()
    else:
        # コマンドライン引数モード
        command_line_mode(args)


if __name__ == "__main__":
    main()
