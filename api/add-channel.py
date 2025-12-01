from http.server import BaseHTTPRequestHandler
import json
import os
import re

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # CORSヘッダー
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        # リクエストボディを読み取り
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            channel_url = data.get('channel_url', '')
            channel_name = data.get('channel_name', '')

            # チャンネルIDを抽出
            channel_id = self.extract_channel_id(channel_url)

            if not channel_id:
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': '有効なチャンネルURLを入力してください'
                }).encode())
                return

            if not channel_name:
                channel_name = f'チャンネル_{channel_id[:8]}'

            # user_ids.jsonを読み込み
            user_ids_path = os.path.join(os.path.dirname(__file__), '..', 'user_ids.json')

            with open(user_ids_path, 'r', encoding='utf-8') as f:
                user_ids = json.load(f)

            # 既存チャンネルチェック
            existing = [ch for ch in user_ids.get('channels', []) if ch['channel_id'] == channel_id]
            if existing:
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'このチャンネルは既に追加されています'
                }).encode())
                return

            # 新しいチャンネルを追加
            new_channel = {
                'name': channel_name,
                'channel_id': channel_id,
                'enabled': True
            }

            user_ids.setdefault('channels', []).append(new_channel)

            # 保存
            with open(user_ids_path, 'w', encoding='utf-8') as f:
                json.dump(user_ids, f, ensure_ascii=False, indent=2)

            self.wfile.write(json.dumps({
                'success': True,
                'message': f'チャンネル「{channel_name}」を追加しました。update_vercel.batを実行してスクレイピングしてください。',
                'channel': new_channel
            }).encode())

        except Exception as e:
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def extract_channel_id(self, url):
        """YouTubeチャンネルURLからチャンネルIDを抽出"""
        # パターン1: youtube.com/channel/UCxxxxxx
        match = re.search(r'youtube\.com/channel/(UC[\w-]+)', url)
        if match:
            return match.group(1)

        # パターン2: youtube.com/@username
        match = re.search(r'youtube\.com/@([\w-]+)', url)
        if match:
            # @ユーザー名の場合はYouTube APIで変換が必要
            # 今回は簡易実装としてエラーを返す
            return None

        # パターン3: 直接チャンネルIDを入力
        if url.startswith('UC') and len(url) == 24:
            return url

        return None
