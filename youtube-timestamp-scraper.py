import json
import os
import re
from dataclasses import asdict

from googleapiclient import discovery
from dotenv import load_dotenv

from infoclass import VideoInfo, CommentInfo
from utils import aligned_json_dump

load_dotenv()
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise RuntimeError("`.env` に API_KEY がありません。YouTube Data API v3 のAPIキーを設定してください。")

youtube = discovery.build('youtube', 'v3', developerKey=API_KEY)

# 入力チャンネルID読み込み
try:
    users = json.load(open('user_ids.json', encoding='utf-8'))
except FileNotFoundError:
    print("user_ids.json が見つかりません。サンプルを作成します。")
    users = ["UCxxxxxxxxxxxxxxxxxxxxxx"]
    with open('user_ids.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def is_singing_stream(title: str, description: str) -> bool:
    combined_text = f"{title} {description}".lower()
    singing_keywords = [
        "歌", "うた", "歌枠", "うたわく", "歌配信", "singing", "sing",
        "カラオケ", "からおけ", "karaoke",
        "音楽", "music", "楽曲", "ソング", "song",
        "メドレー", "medley", "弾き語り",
        "ライブ", "live", "演奏", "performance",
        "アカペラ", "acappella", "コーラス", "chorus",
        "歌ってみた", "うたってみた", "歌リレー", "歌回",
        "リクエスト歌", "歌練習", "新曲", "cover",
        "ボカロ", "vocaloid", "アニソン", "anime song", "anisong",
        "セトリ", "setlist", "リハ", "リハーサル", "rehearsal"
    ]
    exclude_keywords = [
        "ゲーム", "game", "gaming", "プレイ", "play",
        "雑談", "zatsudan", "talk", "おしゃべり", "chat",
        "料理", "cooking", "クッキング", "食べる", "eating",
        "お絵描き", "絵", "drawing", "art", "イラスト",
        "工作", "craft", "作業", "work", "study", "勉強"
    ]
    singing_score = 0
    for keyword in singing_keywords:
        if keyword in combined_text:
            singing_score += 1
    exclude_score = 0
    for keyword in exclude_keywords:
        if keyword in combined_text:
            exclude_score += 1
    if re.search(r'[歌うたウタ]', title):
        singing_score += 3
    if re.search(r'[♪♫♬🎵🎶🎤🎼]', combined_text):
        singing_score += 2
    timestamp_count = len(re.findall(r'\d{1,2}:\d{2}', description))
    if timestamp_count >= 3:
        singing_score += 2
    if singing_score >= 2 and exclude_score <= singing_score:
        return True
    elif singing_score >= 4:
        return True
    else:
        return False


def get_uploads_playlist_id(channel_id: str) -> str | None:
    if not channel_id or not channel_id.startswith("UC"):
        return None
    try:
        resp = youtube.channels().list(
            part="contentDetails",
            id=channel_id,
            fields="items/contentDetails/relatedPlaylists/uploads"
        ).execute()
        items = resp.get("items", [])
        if not items:
            return None
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        print(f"チャンネル {channel_id} の uploads プレイリスト取得でエラー: {e}")
        return None


def get_video_info_in_playlist(playlist_id: str) -> list[VideoInfo]:
    video_info_list: list[VideoInfo] = []
    try:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            fields="nextPageToken,items/snippet(publishedAt,title,description,resourceId/videoId)"
        )
        while request:
            response = request.execute()
            items = response.get("items", [])
            for i in items:
                vi = VideoInfo.from_response_snippet(i["snippet"])
                vid = vi.id

                # --- 動画詳細を追加で取得 ---
                try:
                    details = youtube.videos().list(
                        part="liveStreamingDetails,snippet",
                        id=vid,
                        fields="items(snippet/publishedAt,liveStreamingDetails/actualStartTime)"
                    ).execute()

                    if details.get("items"):
                        item = details["items"][0]
                        vi.stream_start = item.get("liveStreamingDetails", {}).get("actualStartTime")
                        if not vi.stream_start:
                            vi.stream_start = item["snippet"]["publishedAt"]

                except Exception as e:
                    print(f"動画 {vid} の詳細取得でエラー: {e}")

                video_info_list.append(vi)

            request = youtube.playlistItems().list_next(request, response)
    except Exception as e:
        print(f"プレイリスト {playlist_id} の取得でエラー: {e}")
    return video_info_list


def get_comments(video_id: str) -> list[CommentInfo]:
    comment_list: list[CommentInfo] = []
    comment_field = "snippet(videoId,textDisplay,textOriginal)"
    top_comment_f = f"items/snippet/topLevelComment/{comment_field}"
    replies_f = f"items/replies/comments/{comment_field}"

    try:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            maxResults=100,
            videoId=video_id,
            fields=f"nextPageToken,{top_comment_f},{replies_f}"
        )
        while request:
            response = request.execute()
            for item in response.get("items", []):
                comment_list.extend(CommentInfo.response_item_to_comments(item))
            request = youtube.commentThreads().list_next(request, response)
    except Exception as e:
        print(f"動画 {video_id} のコメント取得でエラー: {e}")

    return comment_list


# 実行本体
uploads_ids: list[str] = []
for uc in users:
    up = get_uploads_playlist_id(uc)
    if up:
        uploads_ids.append(up)
    else:
        print(f"取得失敗: {uc}")

video_info_list: list[VideoInfo] = []
for upid in uploads_ids:
    video_info_list += get_video_info_in_playlist(upid)

filtered_video_list = []
for vi in video_info_list:
    if is_singing_stream(vi.title, vi.description):
        filtered_video_list.append(vi)

print(f"全動画数: {len(video_info_list)}, 歌枠動画数: {len(filtered_video_list)}")

print("\n=== 歌枠として検出された動画 ===")
for i, vi in enumerate(filtered_video_list[:10]):
    print(f"{i+1}. {vi.title}")
if len(filtered_video_list) > 10:
    print(f"... 他 {len(filtered_video_list) - 10} 件")

print("\nコメントを取得中...")
for i, video_info in enumerate(filtered_video_list):
    print(f"{i+1}/{len(filtered_video_list)}: {video_info.title}")
    video_info.comments = get_comments(video_info.id)

vi_dict = [asdict(vi) for vi in filtered_video_list]
aligned_json_dump(vi_dict, "comment_info.json")
print("完了！comment_info.json を作成しました。")
