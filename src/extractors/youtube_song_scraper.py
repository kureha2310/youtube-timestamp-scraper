import json
import os
import re
import csv
from datetime import datetime, timezone, timedelta
from dataclasses import asdict
from typing import List, Optional

from googleapiclient import discovery
from dotenv import load_dotenv
import pandas as pd

# MeCabのインポート（オプション）
try:
    import MeCab
    mecab_reading = MeCab.Tagger('-Oyomi')
    print("MeCab loaded successfully")
except (ImportError, RuntimeError) as e:
    print(f"MeCab not available: {type(e).__name__}. Using simple hiragana conversion.")
    mecab_reading = None

from infoclass import VideoInfo, CommentInfo, TimeStamp
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

class EnhancedAnalyzer:
    def __init__(self):
        # ジャンル判定用キーワード
        self.vocaloid_keywords = [
            "初音ミク","鏡音リン","鏡音レン","巡音ルカ","MEIKO","KAITO",
            "GUMI","IA","重音テト","ジミーサムP","wowaka","ryo","supercell",
            "みきとP","かいりきベア","DECO*27","Neru","40mP","バルーン","n-buna",
            "ピノキオピー","Chinozo","Orangestar","じん","すりぃ","八王子P","蝶々P"
        ]
        self.anime_keywords = [
            "涼宮ハルヒ","千石撫子","MAHO堂","どうぶつビスケッツ","平野綾",
            "茅原実里","後藤邑子","ZONE","KANA-BOON","UNISON SQUARE GARDEN",
            "AKINO","井上あずみ","中島義実","さユり","大黒摩季","松任谷由実"
        ]
        self.anime_titles = [
            "God knows","恋愛サーキュレーション","シルエット","ブルーバード",
            "ハレ晴れユカイ","君の知らない物語","創世のアクエリオン",
            "ようこそジャパリパークへ","おジャ魔女カーニバル",
            "シュガーソングとビターステップ","Zzz","夢をかなえてドラえもん",
            "ラヴァーズ","オレンジ","花の塔","ミカヅキ"
        ]

    def to_hiragana(self, text: str) -> str:
        """テキストをひらがなに変換"""
        if mecab_reading:
            try:
                reading = mecab_reading.parse(text).strip()
                hiragana = ''
                for char in reading:
                    if 'ァ' <= char <= 'ヶ':
                        hiragana += chr(ord(char) - ord('ァ') + ord('ぁ'))
                    elif char == 'ヵ':
                        hiragana += 'か'
                    elif char == 'ヶ':
                        hiragana += 'け'
                    else:
                        hiragana += char.lower()
                return hiragana
            except:
                pass
        
        # MeCabが使えない場合の簡易変換
        return self._simple_katakana_to_hiragana(text.lower())
    
    def _simple_katakana_to_hiragana(self, text: str) -> str:
        """簡易カタカナ→ひらがな変換（英数字・記号も処理）"""
        result = ''
        for char in text:
            if 'ァ' <= char <= 'ヶ':
                result += chr(ord(char) - ord('ァ') + ord('ぁ'))
            elif char == 'ヵ':
                result += 'か'
            elif char == 'ヶ':
                result += 'け'
            elif 'A' <= char <= 'Z':
                result += char.lower()
            elif char in '０１２３４５６７８９':
                # 全角数字を半角に
                result += str(ord(char) - ord('０'))
            elif char in '（）［］｛｝':
                # 全角括弧を除去
                continue
            else:
                result += char
        return result

    def detect_genre(self, title: str, artist: str) -> str:
        """ジャンルを自動判定"""
        text = f"{title} {artist}"
        if any(k.lower() in text.lower() for k in self.vocaloid_keywords):
            return "Vocaloid"
        if any(k.lower() in text.lower() for k in self.anime_keywords):
            return "アニメ"
        if any(k.lower() in title.lower() for k in self.anime_titles):
            return "アニメ"
        return "その他"

    def calculate_confidence_score(self, video_info: VideoInfo) -> float:
        """歌動画の確度スコアを計算（既存のロジックを活用）"""
        title = video_info.title
        description = video_info.description
        
        # 既存のis_singing_stream関数と同じロジック
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
        
        # 正規化してスコアを0-1の範囲に
        total_possible = len(singing_keywords) + 5 + 2  # キーワード数 + ボーナススコア
        raw_score = max(0, singing_score - exclude_score)
        return min(1.0, raw_score / 10.0)  # 10点満点で正規化

    def clean_title(self, text: str) -> str:
        """先頭ナンバリングを除去"""
        text = re.sub(
            r"^\s*(?:\(?\s*\d+\s*\)?[\.\)：:：\-]*\s*|\[\s*\d+\]\s*)",
            "",
            text
        )
        text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
        return text.strip()

    def parse_song_title_artist(self, title: str) -> tuple[str, str]:
        """曲名とアーティストを分離"""
        title = self.clean_title(title)
        
        # 「曲 / 歌手」形式で分割
        parts = re.split(r"\s*/\s*", title, maxsplit=1)
        if len(parts) == 2:
            song_title, artist = parts[0].strip(), parts[1].strip()
            return song_title, artist
        else:
            return title.strip(), ""

def is_singing_stream(title: str, description: str) -> bool:
    """既存の歌動画判定ロジック（そのまま使用）"""
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
    """既存関数をそのまま使用"""
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
    """既存関数をそのまま使用"""
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
    """既存関数をそのまま使用"""
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

def main():
    print("🎵 YouTube歌動画タイムスタンプ抽出ツール（統合版）")
    print("=" * 60)
    
    analyzer = EnhancedAnalyzer()
    
    # 1. 動画情報取得（既存ロジック）
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

    # 2. 歌動画フィルタリング
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

    # 3. コメント取得
    print("\nコメントを取得中...")
    for i, video_info in enumerate(filtered_video_list):
        print(f"{i+1}/{len(filtered_video_list)}: {video_info.title}")
        video_info.comments = get_comments(video_info.id)

    # 4. タイムスタンプ抽出
    print("\nタイムスタンプを抽出中...")
    all_timestamps = []
    for v in filtered_video_list:
        ts_list = TimeStamp.from_videoinfo(v)
        all_timestamps.extend(ts_list)
    
    print(f"抽出されたタイムスタンプ数: {len(all_timestamps)}")

    # 5. CSV形式に変換
    print("\nCSV形式に変換中...")
    rows = []
    seen = {}
    idx = 1

    for entry in all_timestamps:
        video_id = entry.video_id
        raw_title = entry.text
        timestamp = entry.timestamp
        published_at = getattr(entry, 'stream_start', None) or entry.published_at
        
        # 確度スコア計算（該当する動画を見つけて計算）
        confidence = 0.0
        for vi in filtered_video_list:
            if vi.id == video_id:
                confidence = analyzer.calculate_confidence_score(vi)
                break

        song_title, artist = analyzer.parse_song_title_artist(raw_title)

        # 歌手なしは除外
        if not artist:
            continue

        # 重複判定
        key = (song_title.lower(), artist.lower(), video_id, timestamp)
        if key in seen:
            if re.match(r"^\s*\d+", raw_title):
                continue
        seen[key] = True

        # ジャンル判定
        genre = analyzer.detect_genre(song_title, artist)
        
        # ひらがな変換
        search_text = analyzer.to_hiragana(song_title)

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
            search_text,  # ひらがな検索用
            genre,
            timestamp,
            date_str,
            video_id,
            f"{confidence:.2f}"  # 確度スコア
        ])
        idx += 1

    # 6. CSV出力
    output_file = "song_timestamps_complete.csv"
    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["No","曲","歌手-ユニット","検索用","ジャンル","タイムスタンプ","配信日","動画ID","確度スコア"])
        writer.writerows(rows)

    print(f"\n✅ 完了！CSVを出力しました: {output_file}")
    print(f"📊 統計:")
    print(f"   - 処理した動画数: {len(filtered_video_list)}")
    print(f"   - 抽出したタイムスタンプ数: {len(all_timestamps)}")
    print(f"   - 最終出力行数: {len(rows)}")
    
    # 確度スコア統計
    if rows:
        scores = [float(row[8]) for row in rows]
        high_conf = len([s for s in scores if s > 0.7])
        med_conf = len([s for s in scores if 0.4 <= s <= 0.7])
        low_conf = len([s for s in scores if s < 0.4])
        
        print(f"   - 高確度 (>0.7): {high_conf}件")
        print(f"   - 中確度 (0.4-0.7): {med_conf}件")  
        print(f"   - 低確度 (<0.4): {low_conf}件")

    # JSONファイルも保存（バックアップ用）
    vi_dict = [asdict(vi) for vi in filtered_video_list]
    aligned_json_dump(vi_dict, "comment_info.json")
    print(f"📄 バックアップJSONも作成: comment_info.json")

if __name__ == "__main__":
    main()