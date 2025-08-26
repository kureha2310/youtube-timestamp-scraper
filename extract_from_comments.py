# extract_from_comments.py
# -*- coding: utf-8 -*-

import json
from infoclass import VideoInfo, TimeStamp

INPUT_FILE = "comment_info.json"
OUTPUT_FILE = "timestamps.json"


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        videos_json = json.load(f)

    # JSON → VideoInfo
    videos = [VideoInfo.from_json(v) for v in videos_json]

    # すべての動画から TimeStamp を抽出
    all_timestamps = []
    for v in videos:
        ts_list = TimeStamp.from_videoinfo(v)
        for ts in ts_list:
            all_timestamps.append({
                "video_id": ts.video_id,
                "video_title": ts.video_title,
                "published_at": ts.published_at,
                "stream_start": getattr(ts, "stream_start", None),  # あれば拾う
                "link": ts.link,
                "timestamp": ts.timestamp,
                "text": ts.text,
            })

    # JSON 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_timestamps, f, ensure_ascii=False, indent=2)

    print(f"✅ 抽出完了: {len(all_timestamps)} 件")
    print(f"  JSON: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
