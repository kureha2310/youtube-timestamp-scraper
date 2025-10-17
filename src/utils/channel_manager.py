#!/usr/bin/env python3
"""
チャンネル管理モジュール
user_ids.jsonの読み書きとチャンネル管理機能を提供
"""

import json
import os
from typing import List, Dict, Optional


USER_IDS_FILE = 'user_ids.json'


def load_channels() -> List[Dict[str, any]]:
    """
    user_ids.jsonからチャンネルリストを読み込む

    Returns:
        List[Dict]: チャンネル情報のリスト
    """
    if not os.path.exists(USER_IDS_FILE):
        return []

    with open(USER_IDS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 旧形式（配列のみ）の場合は新形式に変換
    if isinstance(data, list):
        channels = [
            {
                "name": f"チャンネル{i+1}",
                "channel_id": channel_id,
                "enabled": True
            }
            for i, channel_id in enumerate(data)
        ]
        save_channels(channels)
        return channels

    return data.get('channels', [])


def save_channels(channels: List[Dict[str, any]]):
    """
    チャンネルリストをuser_ids.jsonに保存

    Args:
        channels: チャンネル情報のリスト
    """
    data = {"channels": channels}

    with open(USER_IDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_enabled_channels() -> List[Dict[str, any]]:
    """
    有効なチャンネルのみを取得

    Returns:
        List[Dict]: 有効なチャンネル情報のリスト
    """
    channels = load_channels()
    return [ch for ch in channels if ch.get('enabled', True)]


def get_channel_ids() -> List[str]:
    """
    有効なチャンネルIDのリストを取得（旧互換性用）

    Returns:
        List[str]: チャンネルIDのリスト
    """
    channels = get_enabled_channels()
    return [ch['channel_id'] for ch in channels]


def add_channel(name: str, channel_id: str, enabled: bool = True) -> bool:
    """
    新しいチャンネルを追加

    Args:
        name: チャンネル名
        channel_id: チャンネルID
        enabled: 有効/無効

    Returns:
        bool: 成功したかどうか
    """
    channels = load_channels()

    # 既に存在するか確認
    for ch in channels:
        if ch['channel_id'] == channel_id:
            print(f"[!]  チャンネルID {channel_id} は既に登録されています")
            return False

    # 新しいチャンネルを追加
    new_channel = {
        "name": name,
        "channel_id": channel_id,
        "enabled": enabled
    }
    channels.append(new_channel)

    save_channels(channels)
    print(f"[OK] チャンネル「{name}」を追加しました")
    return True


def remove_channel(channel_id: str) -> bool:
    """
    チャンネルを削除

    Args:
        channel_id: チャンネルID

    Returns:
        bool: 成功したかどうか
    """
    channels = load_channels()

    # チャンネルを検索して削除
    for i, ch in enumerate(channels):
        if ch['channel_id'] == channel_id:
            removed_name = ch['name']
            channels.pop(i)
            save_channels(channels)
            print(f"[OK] チャンネル「{removed_name}」を削除しました")
            return True

    print(f"[!]  チャンネルID {channel_id} が見つかりません")
    return False


def toggle_channel(channel_id: str) -> bool:
    """
    チャンネルの有効/無効を切り替え

    Args:
        channel_id: チャンネルID

    Returns:
        bool: 成功したかどうか
    """
    channels = load_channels()

    for ch in channels:
        if ch['channel_id'] == channel_id:
            ch['enabled'] = not ch.get('enabled', True)
            save_channels(channels)
            status = "有効" if ch['enabled'] else "無効"
            print(f"[OK] チャンネル「{ch['name']}」を{status}にしました")
            return True

    print(f"[!]  チャンネルID {channel_id} が見つかりません")
    return False


def list_channels(show_all: bool = True):
    """
    登録されているチャンネルを一覧表示

    Args:
        show_all: 無効なチャンネルも表示するか
    """
    channels = load_channels()

    if not channels:
        print("[*] 登録されているチャンネルはありません")
        return

    print("\n" + "="*70)
    print("[*] 登録チャンネル一覧")
    print("="*70)

    for i, ch in enumerate(channels, 1):
        if not show_all and not ch.get('enabled', True):
            continue

        status = "[OK]" if ch.get('enabled', True) else "[!]"
        print(f"{i}. {status} {ch['name']}")
        print(f"   ID: {ch['channel_id']}")
        print()

    print("="*70)


def select_channels() -> List[Dict[str, any]]:
    """
    対話形式でチャンネルを選択

    Returns:
        List[Dict]: 選択されたチャンネル情報のリスト
    """
    channels = get_enabled_channels()

    if not channels:
        print("[!] 有効なチャンネルが登録されていません")
        return []

    print("\n" + "="*70)
    print("[*] チャンネル選択")
    print("="*70)
    print("スクレイプするチャンネルを選択してください")
    print()

    # チャンネル一覧を表示
    for i, ch in enumerate(channels, 1):
        print(f"{i}. {ch['name']} ({ch['channel_id']})")

    print(f"{len(channels) + 1}. すべてのチャンネル")
    print("0. キャンセル")
    print("="*70)

    # 入力を受け付ける
    while True:
        try:
            choice = input("\n番号を入力してください（複数選択可、カンマ区切り）: ").strip()

            if choice == "0":
                print("[!] キャンセルしました")
                return []

            # カンマ区切りで分割
            choices = [c.strip() for c in choice.split(',')]

            # すべて選択
            if str(len(channels) + 1) in choices:
                print(f"[OK] すべてのチャンネル（{len(channels)}件）を選択しました")
                return channels

            # 個別選択
            selected = []
            for c in choices:
                idx = int(c) - 1
                if 0 <= idx < len(channels):
                    selected.append(channels[idx])
                else:
                    print(f"[!]  無効な番号: {c}")

            if selected:
                names = [ch['name'] for ch in selected]
                print(f"[OK] {len(selected)}件のチャンネルを選択しました: {', '.join(names)}")
                return selected
            else:
                print("[!] 有効なチャンネルが選択されませんでした")

        except ValueError:
            print("[!] 無効な入力です。数字を入力してください")
        except KeyboardInterrupt:
            print("\n[!] キャンセルしました")
            return []


if __name__ == "__main__":
    # テスト用
    list_channels()
