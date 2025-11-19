#!/usr/bin/env python3
"""
Vercelサイト更新スクリプト
最新動画を取得 → CSV生成 → JSON変換 → フロントエンドビルド → docs更新 → Git push
"""

import json
import sys
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main(auto_yes=False):
    print("=" * 70)
    print("【Vercelサイト更新】")
    print("=" * 70)
    print()
    print("実行内容:")
    print("  1. 最新動画のタイムスタンプを取得（差分更新）")
    print("  2. CSVファイルを生成")
    print("  3. Web表示用JSONファイルを生成")
    print("  4. フロントエンドをビルド")
    print("  5. docsディレクトリに出力")
    print("  6. Gitコミット & プッシュ（Vercelが自動デプロイ）")
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
    if not auto_yes:
        confirm = input("更新を開始しますか？ (y/N): ").strip().lower()
        if confirm != 'y':
            print("キャンセルしました")
            return 0
    else:
        print("自動実行モード: 更新を開始します")

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
        import traceback
        traceback.print_exc()
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
    print("ステップ3: フロントエンドをビルド中...")
    print("=" * 70)

    # フロントエンドのビルド
    try:
        # npm installを実行（初回またはpackage.json変更時）
        print("\n[*] npm install を実行中...")
        subprocess.run(
            ['npm', 'install'],
            cwd='frontend',
            check=True,
            capture_output=False,
            text=True
        )

        # npm run buildを実行
        print("\n[*] npm run build を実行中...")
        subprocess.run(
            ['npm', 'run', 'build'],
            cwd='frontend',
            check=True,
            capture_output=False,
            text=True
        )

        print("\n[OK] ビルド完了")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] ビルドでエラーが発生しました: {e}")
        return 1
    except FileNotFoundError:
        print("\n[!] npmが見つかりません。Node.jsがインストールされているか確認してください")
        return 1

    print()
    print("=" * 70)
    print("ステップ4: Gitにコミット & プッシュ中...")
    print("=" * 70)

    # Gitコミット
    try:
        # git add
        subprocess.run(['git', 'add', 'docs/', 'output/', 'last_scrape.json'], check=True)

        # git status
        result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, check=True)

        if not result.stdout.strip():
            print("\n[i] 変更がないため、コミットをスキップします")
        else:
            # git commit
            from datetime import datetime
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            commit_msg = f"🤖 Auto-update timestamps [{now}]"

            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)

            # git push
            subprocess.run(['git', 'push'], check=True)

            print("\n[OK] GitHubにプッシュしました")
            print("[OK] Vercelが自動的にデプロイを開始します（数分かかります）")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Gitコミットでエラーが発生しました: {e}")
        print("    手動でコミット・プッシュしてください")
        return 1

    print()
    print("=" * 70)
    print("【完了】Vercelサイトの更新を開始しました！")
    print("=" * 70)
    print()
    print("次のステップ:")
    print("  1. Vercelが自動的にデプロイします（3-5分ほど待機）")
    print("  2. https://youtube-timestamp-scraper.vercel.app/ で確認")
    print()
    print("Vercelのデプロイ状況を確認:")
    print("  https://vercel.com/dashboard")
    print()

    return 0

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Vercelサイト更新')
    parser.add_argument('--auto', action='store_true', help='確認なしで自動実行')
    args = parser.parse_args()

    sys.exit(main(auto_yes=args.auto))
