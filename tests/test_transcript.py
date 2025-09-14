"""
字幕抽出機能のテスト
"""
from transcript_only_scraper import TranscriptOnlyScraper
from enhanced_extractor import Config

def test_single_video():
    """特定の動画IDで字幕抽出をテスト"""
    config = Config()
    scraper = TranscriptOnlyScraper(config)
    
    # テスト用の動画ID（歌枠動画）
    test_video_id = "lxZPgnmdkok"  # ユーザーの動画から1つ選択
    
    print(f"Testing video ID: {test_video_id}")
    
    # 字幕を取得
    transcript = scraper.get_transcript(test_video_id)
    
    if transcript:
        print(f"Found transcript with {len(transcript)} entries")
        
        # 最初の10件を表示
        print("\nFirst 10 transcript entries:")
        for i, entry in enumerate(transcript[:10]):
            start_time = entry.start if hasattr(entry, 'start') else 0
            text = entry.text if hasattr(entry, 'text') else str(entry)
            timestamp = scraper._seconds_to_timestamp(start_time)
            print(f"[{timestamp}] {text}")
        
        # 楽曲情報を抽出
        songs = scraper.extract_songs_from_transcript(transcript, test_video_id)
        
        if songs:
            print(f"\n=== Found {len(songs)} songs ===")
            for song in songs:
                print(f"[{song['timestamp']}] {song['title']} / {song['artist']}")
                print(f"  Genre: {song['genre']}, Confidence: {song['confidence']:.2f}")
        else:
            print("\nNo songs found in transcript")
    else:
        print("No transcript available")

if __name__ == "__main__":
    test_single_video()