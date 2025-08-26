# extract-timestamp-list.py
# -*- coding: utf-8 -*-

import csv
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- ジャンル判定用キーワード --------------------------------------

VOCALOID_KEYWORDS = [
    "初音ミク","鏡音リン","鏡音レン","巡音ルカ","MEIKO","KAITO",
    "GUMI","IA","重音テト","ジミーサムP","wowaka","ryo","supercell",
    "みきとP","かいりきベア","DECO*27","Neru","40mP","バルーン","n-buna",
    "ピノキオピー","Chinozo","Orangestar","じん","すりぃ","八王子P","蝶々P"
]
ANIME_KEYWORDS = [
    "涼宮ハルヒ","千石撫子","MAHO堂","どうぶつビスケッツ","平野綾",
    "茅原実里","後藤邑子","ZONE","KANA-BOON","UNISON SQUARE GARDEN",
    "AKINO","井上あずみ","中島義実","さユり","大黒摩季","松任谷由実"
]
ANIME_TITLES = [
    "God knows","恋愛サーキュレーション","シルエット","ブルーバード",
    "ハレ晴れユカイ","君の知らない物語","創世のアクエリオン",
    "ようこそジャパリパークへ","おジャ魔女カーニバル",
    "シュガーソングとビターステップ","Zzz","夢をかなえてドラえもん",
    "ラヴァーズ","オレンジ","花の塔","ミカヅキ"
]

# --- 判定ロジック --------------------------------------------------

def detect_genre(title: str, artist: str) -> str:
    text = f"{title} {artist}"
    if any(k.lower() in text.lower() for k in VOCALOID_KEYWORDS):
        return "Vocaloid"
    if any(k.lower() in text.lower() for k in ANIME_KEYWORDS):
        return "アニメ"
    if any(k.lower() in title.lower() for k in ANIME_TITLES):
        return "アニメ"
    return "その他"

def clean_title(text: str) -> str:
    # 先頭ナンバリング（01. / 1) / [1] / 1- / 1：など）を削除
    text = re.sub(
        r"^\s*(?:\(?\s*\d+\s*\)?[\.\)：:：\-]*\s*|\[\s*\d+\]\s*)",
        "",
        text
    )
    # <br> を除去（大文字・閉じタグも対応）
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    return text.strip()

# --- メイン処理 ----------------------------------------------------

def format_timestamps(input_file: str, output_file: str):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    seen = {}
    idx = 1

    for entry in data:
        video_id = entry.get("video_id")
        raw_title = entry.get("text", "")
        timestamp = entry.get("timestamp", "")
        published_at = entry.get("stream_start") or entry.get("published_at")

        title = clean_title(raw_title)

        # 「曲 / 歌手」形式で分割
        parts = re.split(r"\s*/\s*", title, maxsplit=1)
        if len(parts) == 2:
            song_title, artist = parts[0].strip(), parts[1].strip()
        else:
            song_title, artist = title.strip(), ""

        # 歌手なしは除外
        if not artist:
            continue

        # 重複判定（clean後のキーで）
        key = (song_title.lower(), artist.lower(), video_id, timestamp)
        if key in seen:
            # 先頭にナンバリングがある方はスキップ
            if re.match(r"^\s*\d+", raw_title):
                continue
        seen[key] = True

        genre = detect_genre(song_title, artist)

        # 日付をJSTへ
        try:
            dt = datetime.fromisoformat((published_at or "").replace("Z", "+00:00"))
            date_str = dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y/%m/%d")
        except Exception:
            date_str = ""

        rows.append([
            idx,
            song_title,
            artist,
            "",  # 検索用
            genre,
            timestamp,
            date_str,
            video_id
        ])
        idx += 1

    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["No","曲","歌手-ユニット","検索用","ジャンル","タイムスタンプ","配信日","動画ID"])
        writer.writerows(rows)

    print(f"✅ CSV を出力しました: {output_file}")

if __name__ == "__main__":
    format_timestamps("timestamps.json", "timestamps_list.csv")
