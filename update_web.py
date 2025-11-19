#!/usr/bin/env python3
"""
ワンクリックWeb更新スクリプト
最新動画を取得 → CSV生成 → JSON変換 → Web更新
"""

import json
import sys
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("=" * 70)
    print("【ワンクリックWeb更新】")
    print("=" * 70)
    print()
    print("実行内容:")
    print("  1. 最新動画のタイムスタンプを取得（差分更新）")
    print("  2. CSVファイルを生成")
    print("  3. Web表示用JSONファイルを生成")
    print()

    # user_ids.jsonからチャンネル情報を確認
    try:
        with open('user_ids.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        channels = data.get('channels', [])
        enabled_channels = [ch for ch in channels if ch.get('enabled', True)]

        if not enabled_channels:
            print("[!] 有効なチャンネルが見つかりません")
            return 1

        print(f"対象チャンネル: {len(enabled_channels)}件")
        for ch in enabled_channels:
            print(f"  - {ch['name']}")
        print()
    except FileNotFoundError:
        print("[!] user_ids.json が見つかりません")
        return 1

    # 確認
    confirm = input("更新を開始しますか？ (y/N): ").strip().lower()
    if confirm != 'y':
        print("キャンセルしました")
        return 0

    print()
    print("=" * 70)
    print("ステップ1: 最新動画のタイムスタンプを取得中...")
    print("=" * 70)

    # scrape_latest.py を直接実行（差分更新）
    from extractors.youtube_song_scraper import scrape_channels

    channel_ids = [ch['channel_id'] for ch in enabled_channels]

    try:
        scrape_channels(channel_ids, incremental=True)
    except Exception as e:
        print(f"\n[!] エラーが発生しました: {e}")
        return 1

    print()
    print("=" * 70)
    print("ステップ2: Web表示用JSONを生成中...")
    print("=" * 70)

    # export_to_web.py を実行
    try:
        result = subprocess.run(
            [sys.executable, 'export_to_web.py'],
            check=True,
            capture_output=False,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"\n[!] JSON生成でエラーが発生しました: {e}")
        return 1

    print()
    print("=" * 70)
    print("【完了】Webサイトが更新されました！")
    print("=" * 70)
    print()
    print("次のステップ:")
    print("  1. docs/index.html をブラウザで開いて確認")
    print("  2. GitHubにプッシュしてGitHub Pagesに反映")
    print()
    print("コマンド例:")
    print("  git add .")
    print('  git commit -m "Update timestamps"')
    print("  git push")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
