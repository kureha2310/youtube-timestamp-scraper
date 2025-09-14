#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from enhanced_extractor import Config, EnhancedTimestampExtractor

# テスト用のサンプルデータ
sample_texts = [
    # 元の問題があったHTMLタグ混入データ
    '<a href="...">6:53</a> 1.サイハテ/小林オニキス feat. 初音ミク',
    '<a> napori <a href="UCY85ViSyTU5Wy_bwsUVjkdA/pOG1Z7jMBYy__9EP2cTfoAk"></a><a href="https://www.youtube.com/watch?v=utbk0nDUlLU&t=705">11:45</a> 東京フラッシュ',
    '<a> 丸の内サディスティック <a href="UCY85ViSyTU5Wy_bwsUVjkdA/C3wkZ8XmMKCn_9EPjZHyiQQ"></a><a href="https://www.youtube.com/watch?v=utbk0nDUlLU&t=4077">1:07:57</a> 絶え間なく藍色',
    
    # 正常なテキスト
    '5:00 夏夜のマジック / Indigo la End',
    '27:30 君がくれた夏 / 家入レオ',
    
    # 複雑なHTMLアンカーパターン
    '<a href="https://www.youtube.com/watch?v=d2pz8tMZJ08&t=300">5:00</a> 夏夜のマジック / Indigo la End <a href="https://www.youtube.com/watch?v=d2pz8tMZJ08&t=1650">27:30</a> 君がくれた夏 / 家入レオ',
    
    # 無効なパターン（おぱんちゅうさぎなど）
    '47:43 おぱんちゅうさぎのポシェットの話 面白かった',
]

def test_html_cleaning():
    print("HTMLクリーニングテスト")
    print("=" * 60)
    
    config = Config()
    extractor = EnhancedTimestampExtractor(config)
    
    for i, text in enumerate(sample_texts, 1):
        print(f"\n{i}. 入力テキスト:")
        print(f"   {text}")
        
        # HTMLとプレーンテキストの両方で抽出
        html_results = extractor.extract_html_timestamps(text)
        plain_results = extractor.extract_plain_timestamps(text)
        
        # 全体での抽出
        all_results = extractor.extract_all_timestamps(text)
        
        print(f"   HTMLアンカー抽出: {len(html_results)}件")
        for ts, content in html_results:
            print(f"     {ts} - {content}")
        
        print(f"   プレーンテキスト抽出: {len(plain_results)}件")
        for ts, content in plain_results:
            print(f"     {ts} - {content}")
        
        print(f"   全体抽出: {len(all_results)}件")
        for ts, content in all_results:
            print(f"     {ts} - {content}")

if __name__ == "__main__":
    test_html_cleaning()