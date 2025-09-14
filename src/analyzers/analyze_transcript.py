"""
字幕内容の詳細分析
"""
from transcript_only_scraper import TranscriptOnlyScraper
from enhanced_extractor import Config
import re

def analyze_transcript_patterns():
    """字幕の中に楽曲らしいパターンがないかを分析"""
    config = Config()
    scraper = TranscriptOnlyScraper(config)
    
    test_video_id = "lxZPgnmdkok"
    transcript = scraper.get_transcript(test_video_id)
    
    if not transcript:
        print("No transcript available")
        return
    
    print(f"Analyzing {len(transcript)} transcript entries...\n")
    
    # 楽曲らしいキーワードを含むエントリを探す
    music_keywords = [
        '歌', 'うた', '曲', '歌います', '歌わせて', '歌枠',
        'カラオケ', 'からおけ', 'リクエスト', 'next', '次',
        'song', 'sing', 'cover', 'original', 'オリジナル',
        'ボカロ', 'vocaloid', 'アニソン', 'アニメ',
        '「', '」', '『', '』'  # 括弧で囲まれた楽曲名
    ]
    
    potential_songs = []
    
    for i, entry in enumerate(transcript):
        text = entry.text if hasattr(entry, 'text') else str(entry)
        start_time = entry.start if hasattr(entry, 'start') else 0
        timestamp = scraper._seconds_to_timestamp(start_time)
        
        # 楽曲関連キーワードをチェック
        for keyword in music_keywords:
            if keyword in text.lower():
                potential_songs.append({
                    'timestamp': timestamp,
                    'text': text,
                    'keyword': keyword
                })
                break
    
    print(f"Found {len(potential_songs)} entries with music-related keywords:")
    print("=" * 80)
    
    # 結果を表示（最初の20件）
    for item in potential_songs[:20]:
        try:
            print(f"[{item['timestamp']}] ({item['keyword']}) {item['text']}")
        except UnicodeEncodeError:
            print(f"[{item['timestamp']}] ({item['keyword']}) [Text contains special characters]")
        print()
    
    # より具体的なパターン分析
    print("\n" + "=" * 80)
    print("DETAILED PATTERN ANALYSIS")
    print("=" * 80)
    
    # 括弧で囲まれたテキストを探す
    bracket_patterns = []
    for entry in transcript:
        text = entry.text if hasattr(entry, 'text') else str(entry)
        start_time = entry.start if hasattr(entry, 'start') else 0
        timestamp = scraper._seconds_to_timestamp(start_time)
        
        # 日本語括弧
        matches = re.findall(r'「([^」]+)」', text)
        for match in matches:
            if len(match) > 2 and len(match) < 30:  # 適度な長さ
                bracket_patterns.append((timestamp, match, '「」'))
        
        matches = re.findall(r'『([^』]+)』', text)
        for match in matches:
            if len(match) > 2 and len(match) < 30:
                bracket_patterns.append((timestamp, match, '『』'))
    
    print(f"\nFound {len(bracket_patterns)} items in brackets:")
    for timestamp, text, bracket_type in bracket_patterns[:10]:
        try:
            print(f"[{timestamp}] {bracket_type}: {text}")
        except UnicodeEncodeError:
            print(f"[{timestamp}] {bracket_type}: [Text contains special characters]")
    
    # "次" "歌" などの組み合わせパターン
    print(f"\nLooking for song transition patterns...")
    transition_patterns = []
    
    for i, entry in enumerate(transcript):
        text = entry.text if hasattr(entry, 'text') else str(entry)
        start_time = entry.start if hasattr(entry, 'start') else 0
        timestamp = scraper._seconds_to_timestamp(start_time)
        
        # 楽曲紹介らしいパターン
        if any(pattern in text for pattern in ['次は', '次の曲', '歌います', '歌わせて', '続いて']):
            # 前後の文脈も取得
            context_before = ""
            context_after = ""
            
            if i > 0:
                prev_entry = transcript[i-1]
                context_before = prev_entry.text if hasattr(prev_entry, 'text') else str(prev_entry)
            
            if i < len(transcript) - 1:
                next_entry = transcript[i+1]
                context_after = next_entry.text if hasattr(next_entry, 'text') else str(next_entry)
            
            transition_patterns.append({
                'timestamp': timestamp,
                'main': text,
                'before': context_before,
                'after': context_after
            })
    
    print(f"Found {len(transition_patterns)} transition patterns:")
    for pattern in transition_patterns[:5]:
        try:
            print(f"[{pattern['timestamp']}]")
            print(f"  Before: {pattern['before'][:50]}...")
            print(f"  Main: {pattern['main']}")
            print(f"  After: {pattern['after'][:50]}...")
            print()
        except UnicodeEncodeError:
            print(f"[{pattern['timestamp']}] [Contains special characters]")
            print()

if __name__ == "__main__":
    analyze_transcript_patterns()