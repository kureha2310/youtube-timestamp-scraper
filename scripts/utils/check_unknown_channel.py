#!/usr/bin/env python3
"""不明なチャンネルIDを確認するスクリプト"""

import json
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build

load_dotenv()

unknown_id = 'UCCPc-kcJjcyVGB9N51qNsMg'

api_key = os.getenv('API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    try:
        request = youtube.channels().list(
            part='snippet',
            id=unknown_id
        )
        response = request.execute()
        
        if response.get('items'):
            channel = response['items'][0]
            print(f"チャンネルID: {unknown_id}")
            print(f"チャンネル名: {channel['snippet']['title']}")
            print(f"説明: {channel['snippet'].get('description', '')[:100]}")
        else:
            print(f"チャンネルID {unknown_id} が見つかりませんでした")
    except Exception as e:
        print(f"エラー: {e}")
else:
    print("API_KEYが設定されていません")

