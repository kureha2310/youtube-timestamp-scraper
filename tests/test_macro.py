#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from live_transcript_extractor import LiveTranscriptExtractor

def test_macro_summary():
    """マクロサマリーのテスト"""
    video_id = "pNIpCr03_nQ"
    
    extractor = LiveTranscriptExtractor()
    
    # 字幕データを取得
    print("字幕データを取得中...")
    transcript_data = extractor.get_transcript(video_id)
    
    if not transcript_data:
        print("字幕データが取得できませんでした")
        return
    
    print(f"字幕データ取得完了: {len(transcript_data)}件")
    
    # マクロサマリーを生成
    print("マクロサマリーを生成中...")
    macro_timestamps = extractor.create_macro_summary(transcript_data, interval_minutes=10.0)
    
    print(f"マクロサマリー生成完了: {len(macro_timestamps)}件")
    
    # 結果をCSVファイルに保存
    extractor.save_macro_summary_csv(macro_timestamps, f"natural_sentence_macro_summary_{video_id}.csv")
    print(f"自然な文章形式のマクロサマリーをnatural_sentence_macro_summary_{video_id}.csvに保存しました")
    
    # 最初の10件を表示
    print("\n=== 自然な文章形式のマクロサマリー（最初の10件）===")
    for i, ts in enumerate(macro_timestamps[:10]):
        start_str = f"{int(ts.start_time//60)}:{int(ts.start_time%60):02d}"
        end_str = f"{int(ts.end_time//60)}:{int(ts.end_time%60):02d}"
        print(f"{i+1:2d}. {start_str} - {end_str}: {ts.text}")

if __name__ == "__main__":
    test_macro_summary()