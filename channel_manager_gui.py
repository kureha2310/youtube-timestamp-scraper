#!/usr/bin/env python3
"""
チャンネル管理GUI
新しいチャンネルの追加とスクレイピング実行をGUIで操作できます
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import subprocess
import os
import re
import threading
import requests
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

class ChannelManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTubeチャンネル管理")
        self.root.geometry("800x600")

        # メインフレーム
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # タイトル
        title_label = ttk.Label(main_frame, text="YouTubeチャンネル管理", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 既存チャンネルリスト
        ttk.Label(main_frame, text="登録済みチャンネル:", font=('Arial', 12, 'bold')).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        self.channel_listbox = tk.Listbox(main_frame, height=8, width=60)
        self.channel_listbox.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.channel_listbox.yview)
        scrollbar.grid(row=2, column=2, sticky=(tk.N, tk.S), pady=(0, 20))
        self.channel_listbox.configure(yscrollcommand=scrollbar.set)

        # 新しいチャンネル追加セクション
        ttk.Label(main_frame, text="新しいチャンネルを追加:", font=('Arial', 12, 'bold')).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))

        ttk.Label(main_frame, text="チャンネルURL または チャンネルID:").grid(row=4, column=0, sticky=tk.W, pady=(5, 0))
        self.url_entry = ttk.Entry(main_frame, width=50)
        self.url_entry.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 2))

        hint_label = ttk.Label(main_frame, text="例: https://www.youtube.com/@NanyoRyuka", font=('Arial', 8), foreground='gray')
        hint_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)

        ttk.Label(main_frame, text="チャンネル名 (任意):").grid(row=7, column=0, sticky=tk.W, pady=(5, 0))
        self.name_entry = ttk.Entry(main_frame, width=50)
        self.name_entry.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=9, column=0, columnspan=2, pady=(10, 10))

        self.add_button = ttk.Button(button_frame, text="チャンネル追加", command=self.add_channel)
        self.add_button.grid(row=0, column=0, padx=5)

        self.scrape_button = ttk.Button(button_frame, text="スクレイピング実行", command=self.run_scraping)
        self.scrape_button.grid(row=0, column=1, padx=5)

        self.delete_button = ttk.Button(button_frame, text="選択したチャンネル削除", command=self.delete_channel)
        self.delete_button.grid(row=0, column=2, padx=5)

        # ログ出力エリア
        ttk.Label(main_frame, text="ログ:", font=('Arial', 10, 'bold')).grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        self.log_text = scrolledtext.ScrolledText(main_frame, height=10, width=60, state='disabled')
        self.log_text.grid(row=11, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # グリッドの重み設定
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(11, weight=1)

        # 初期データ読み込み
        self.load_channels()
        self.log("準備完了！")

    def log(self, message):
        """ログメッセージを表示"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def load_channels(self):
        """user_ids.jsonからチャンネルリストを読み込む"""
        try:
            with open('user_ids.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.channel_listbox.delete(0, tk.END)
            channels = data.get('channels', [])

            for ch in channels:
                display_text = f"{ch['name']} ({ch['channel_id']}) {'✓' if ch.get('enabled', True) else '✗'}"
                self.channel_listbox.insert(tk.END, display_text)

            self.log(f"チャンネルリストを読み込みました ({len(channels)}件)")
        except FileNotFoundError:
            self.log("⚠ user_ids.json が見つかりません")
            messagebox.showerror("エラー", "user_ids.json が見つかりません")
        except Exception as e:
            self.log(f"⚠ エラー: {e}")
            messagebox.showerror("エラー", str(e))

    def extract_channel_id(self, url):
        """YouTubeチャンネルURLからチャンネルIDを抽出"""
        # パターン1: youtube.com/channel/UCxxxxxx
        match = re.search(r'youtube\.com/channel/(UC[\w-]+)', url)
        if match:
            return match.group(1)

        # パターン2: youtube.com/@username
        match = re.search(r'youtube\.com/@([\w-]+)', url)
        if match:
            username = match.group(1)
            self.log(f"@{username} からチャンネルIDを取得中...")
            return self.resolve_username_to_channel_id(username)

        # パターン3: 直接チャンネルIDを入力
        if url.startswith('UC') and len(url) == 24:
            return url

        return None

    def resolve_username_to_channel_id(self, username):
        """@ユーザー名からチャンネルIDを取得（YouTube Data API v3使用）"""
        api_key = os.getenv('API_KEY')
        if not api_key:
            self.log("⚠ API_KEYが見つかりません（.envファイルを確認してください）")
            return None

        try:
            # YouTube Data API v3でチャンネル情報を取得
            url = "https://www.googleapis.com/youtube/v3/channels"
            params = {
                'part': 'id',
                'forHandle': username,  # @ユーザー名の場合
                'key': api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'items' in data and len(data['items']) > 0:
                channel_id = data['items'][0]['id']
                self.log(f"✓ チャンネルIDを取得: {channel_id}")
                return channel_id
            else:
                # forHandleで見つからない場合、forUsernameを試す
                params['forUsername'] = username
                del params['forHandle']

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if 'items' in data and len(data['items']) > 0:
                    channel_id = data['items'][0]['id']
                    self.log(f"✓ チャンネルIDを取得: {channel_id}")
                    return channel_id
                else:
                    self.log(f"⚠ @{username} のチャンネルが見つかりませんでした")
                    return None

        except requests.exceptions.RequestException as e:
            self.log(f"⚠ API リクエストエラー: {e}")
            return None
        except Exception as e:
            self.log(f"⚠ エラー: {e}")
            return None

    def add_channel(self):
        """新しいチャンネルを追加"""
        channel_url = self.url_entry.get().strip()
        channel_name = self.name_entry.get().strip()

        if not channel_url:
            messagebox.showwarning("入力エラー", "チャンネルURLまたはIDを入力してください")
            return

        # チャンネルIDを抽出
        channel_id = self.extract_channel_id(channel_url)

        if not channel_id:
            messagebox.showerror("エラー", "有効なチャンネルURLまたはIDを入力してください\n\n対応形式:\n• https://www.youtube.com/@ユーザー名\n• https://www.youtube.com/channel/UCxxxxxx\n• UCxxxxxx（チャンネルIDを直接入力）")
            return

        if not channel_name:
            channel_name = f'チャンネル_{channel_id[:8]}'

        try:
            # user_ids.jsonを読み込み
            with open('user_ids.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 既存チャンネルチェック
            existing = [ch for ch in data.get('channels', []) if ch['channel_id'] == channel_id]
            if existing:
                messagebox.showwarning("重複エラー", "このチャンネルは既に追加されています")
                return

            # 新しいチャンネルを追加
            new_channel = {
                'name': channel_name,
                'channel_id': channel_id,
                'enabled': True
            }

            data.setdefault('channels', []).append(new_channel)

            # 保存
            with open('user_ids.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.log(f"✓ チャンネルを追加しました: {channel_name} ({channel_id})")
            self.load_channels()
            self.url_entry.delete(0, tk.END)
            self.name_entry.delete(0, tk.END)

            messagebox.showinfo("成功", f"チャンネル「{channel_name}」を追加しました！\n\n「スクレイピング実行」ボタンでデータを取得してください。")

        except Exception as e:
            self.log(f"⚠ エラー: {e}")
            messagebox.showerror("エラー", f"チャンネル追加に失敗しました:\n{e}")

    def delete_channel(self):
        """選択したチャンネルを削除"""
        selection = self.channel_listbox.curselection()
        if not selection:
            messagebox.showwarning("選択エラー", "削除するチャンネルを選択してください")
            return

        index = selection[0]

        try:
            with open('user_ids.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            channels = data.get('channels', [])
            if index < len(channels):
                channel_name = channels[index]['name']

                if messagebox.askyesno("確認", f"チャンネル「{channel_name}」を削除しますか？"):
                    del channels[index]
                    data['channels'] = channels

                    with open('user_ids.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    self.log(f"✓ チャンネルを削除しました: {channel_name}")
                    self.load_channels()

        except Exception as e:
            self.log(f"⚠ エラー: {e}")
            messagebox.showerror("エラー", f"チャンネル削除に失敗しました:\n{e}")

    def run_scraping(self):
        """スクレイピングを実行"""
        if messagebox.askyesno("確認", "スクレイピングを実行しますか？\n（数分かかる場合があります）"):
            self.log("=" * 50)
            self.log("スクレイピングを開始します...")
            self.scrape_button.config(state='disabled')

            # 別スレッドで実行
            threading.Thread(target=self._run_scraping_thread, daemon=True).start()

    def _run_scraping_thread(self):
        """スクレイピングを別スレッドで実行"""
        try:
            # update_vercel.pyを実行
            process = subprocess.Popen(
                ['python', 'update_vercel.py', '--auto'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # 出力をリアルタイムで表示
            for line in process.stdout:
                self.log(line.rstrip())

            process.wait()

            if process.returncode == 0:
                self.log("=" * 50)
                self.log("✓ スクレイピング完了！")
                self.root.after(0, lambda: messagebox.showinfo("完了", "スクレイピングが完了しました！"))
            else:
                self.log("=" * 50)
                self.log(f"⚠ エラーが発生しました (終了コード: {process.returncode})")
                self.root.after(0, lambda: messagebox.showerror("エラー", "スクレイピングに失敗しました"))

        except Exception as e:
            self.log(f"⚠ エラー: {e}")
            self.root.after(0, lambda: messagebox.showerror("エラー", f"実行エラー:\n{e}"))

        finally:
            self.root.after(0, lambda: self.scrape_button.config(state='normal'))

def main():
    root = tk.Tk()
    app = ChannelManagerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
