"""
78枠の歌枠動画から一括で楽曲情報を抽出
"""
import csv
import json
from transcript_only_scraper import TranscriptOnlyScraper
from enhanced_extractor import Config
from datetime import datetime
import time

def get_video_ids_from_channel():
    """チャンネルから歌枠動画IDのリストを取得（手動入力版）"""
    print("歌枠動画のIDまたはURLを入力してください（1行に1つ、空行で終了）:")
    print("例: lxZPgnmdkok または https://youtu.be/lxZPgnmdkok")
    
    video_ids = []
    while True:
        line = input().strip()
        if not line:
            break
            
        # URLから動画IDを抽出
        if 'youtu' in line:
            import re
            match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', line)
            if match:
                video_ids.append(match.group(1))
            else:
                print(f"無効なURL: {line}")
        else:
            # 直接IDとして扱う
            video_ids.append(line)
    
    return video_ids

def scrape_all_singing_videos():
    """全ての歌枠動画から楽曲情報を抽出"""
    config = Config()
    scraper = TranscriptOnlyScraper(config)
    
    # 動画IDを取得（手動入力またはファイルから）
    print("=== 歌枠動画一括抽出 ===")
    print("1. 手動で動画IDを入力")
    print("2. video_list.txtファイルから読み込み")
    choice = input("選択してください (1 or 2): ").strip()
    
    video_ids = []
    if choice == '1':
        video_ids = get_video_ids_from_channel()
    else:
        # ファイルから読み込み
        try:
            with open('video_list.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        video_ids.append(line)
        except FileNotFoundError:
            print("video_list.txtが見つかりません。手動入力に切り替えます。")
            video_ids = get_video_ids_from_channel()
    
    if not video_ids:
        print("動画IDが入力されませんでした。")
        return
    
    print(f"\n{len(video_ids)}個の動画を処理します...")
    
    all_songs = []
    processed_count = 0
    failed_count = 0
    
    for i, video_id in enumerate(video_ids, 1):
        print(f"\n[{i}/{len(video_ids)}] 処理中: {video_id}")
        
        try:
            # 楽曲情報を抽出
            songs = scraper.scrape_single_video(f"https://youtu.be/{video_id}")
            
            if songs:
                all_songs.extend(songs)
                processed_count += 1
                print(f"  ✓ {len(songs)}件の楽曲を抽出")
            else:
                print("  ✗ 楽曲が見つかりませんでした")
                failed_count += 1
            
            # API制限回避のため少し待機
            time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ エラー: {e}")
            failed_count += 1
    
    # 結果をCSVに保存
    if all_songs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"bulk_songs_{timestamp}.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['No', '動画ID', 'タイムスタンプ', '曲名', 'アーティスト', '検索用', 'ジャンル', '信頼度', '元テキスト']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for i, song in enumerate(all_songs, 1):
                try:
                    writer.writerow({
                        'No': i,
                        '動画ID': song['video_id'],
                        'タイムスタンプ': song['timestamp'],
                        '曲名': song['title'],
                        'アーティスト': song['artist'],
                        '検索用': song['search_term'],
                        'ジャンル': song['genre'],
                        '信頼度': song['confidence'],
                        '元テキスト': song['original_text'][:50] + '...' if len(song['original_text']) > 50 else song['original_text']
                    })
                except UnicodeEncodeError:
                    # エンコードエラーの場合は簡略化
                    writer.writerow({
                        'No': i,
                        '動画ID': song['video_id'],
                        'タイムスタンプ': song['timestamp'],
                        '曲名': '[エンコードエラー]',
                        'アーティスト': '[エンコードエラー]',
                        '検索用': '[エンコードエラー]',
                        'ジャンル': song['genre'],
                        '信頼度': song['confidence'],
                        '元テキスト': '[エンコードエラー]'
                    })
        
        print(f"\n=== 処理完了 ===")
        print(f"処理成功: {processed_count}動画")
        print(f"処理失敗: {failed_count}動画") 
        print(f"抽出楽曲: {len(all_songs)}件")
        print(f"保存先: {output_file}")
        
        # 統計情報
        print(f"\n=== 統計情報 ===")
        genres = {}
        confidence_levels = {'高': 0, '中': 0, '低': 0}
        
        for song in all_songs:
            # ジャンル統計
            genre = song.get('genre', 'その他')
            genres[genre] = genres.get(genre, 0) + 1
            
            # 信頼度統計
            conf = song.get('confidence', 0.5)
            if conf >= 0.7:
                confidence_levels['高'] += 1
            elif conf >= 0.5:
                confidence_levels['中'] += 1
            else:
                confidence_levels['低'] += 1
        
        print("ジャンル別:")
        for genre, count in sorted(genres.items(), key=lambda x: x[1], reverse=True):
            print(f"  {genre}: {count}件")
        
        print("信頼度別:")
        for level, count in confidence_levels.items():
            print(f"  {level}: {count}件")
    
    else:
        print("\n楽曲が1件も抽出されませんでした。")

def create_sample_video_list():
    """サンプルの動画リストファイルを作成"""
    sample_content = """# 歌枠動画IDリスト
# 1行に1つの動画IDまたはURLを記載
# #で始まる行はコメント
lxZPgnmdkok
nQu5zkoTMLU
utbk0nDUlLU
# 他の動画IDをここに追加
"""
    
    with open('video_list.txt', 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    print("サンプルのvideo_list.txtを作成しました。")
    print("このファイルを編集して動画IDを追加してください。")

if __name__ == "__main__":
    print("=== 歌枠動画一括楽曲抽出ツール ===")
    print("1. 一括抽出を実行")
    print("2. サンプル動画リストファイルを作成")
    
    choice = input("選択してください (1 or 2): ").strip()
    
    if choice == '2':
        create_sample_video_list()
    else:
        scrape_all_singing_videos()