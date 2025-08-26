# infoclass.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any


# --- YouTubeコメントの最小情報を保持するクラス -------------------------------

@dataclass
class CommentInfo:
    text_display: str
    text_original: str

    @classmethod
    def from_response_comment(cls, response_comment: Dict[str, Any]) -> "CommentInfo":
        """
        YouTube Data API (commentThreads / comments) の item から生成。
        """
        comment_snippet = response_comment["snippet"]
        return cls(
            text_display=comment_snippet["textDisplay"],
            text_original=comment_snippet["textOriginal"],
        )

    @classmethod
    def response_item_to_comment_dict(cls, response_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        commentThreads の items[*] を、topLevel + replies を単純な list[comment] に平坦化。
        """
        comment_list: List[Dict[str, Any]] = []
        comment_list.append(response_item["snippet"]["topLevelComment"])
        replies = response_item.get("replies", [])
        if replies:
            replies = replies["comments"]
        comment_list += replies  # type: ignore[assignment]
        return comment_list

    @classmethod
    def response_item_to_comments(cls, response_item: Dict[str, Any]) -> List["CommentInfo"]:
        c_dict = cls.response_item_to_comment_dict(response_item)
        return list(map(cls.from_response_comment, c_dict))

    @classmethod
    def from_json(cls, json_dict: Dict[str, Any]) -> "CommentInfo":
        return cls(
            text_display=json_dict["text_display"],
            text_original=json_dict["text_original"],
        )


# --- 動画情報（プレイリストitems などの snippet から） -----------------------

@dataclass
class VideoInfo:
    id: str
    title: str
    description: str
    published_at: str  # ISO8601文字列
    comments: List[CommentInfo]

    @classmethod
    def from_response_snippet(cls, response_snippet: Dict[str, Any]) -> "VideoInfo":
        """
        playlistItems.items[*].snippet もしくは videos.items[*].snippet に対応。
        """
        s = response_snippet.get("snippet", response_snippet)
        return cls(
            id=s["resourceId"]["videoId"],
            title=s["title"],
            description=s.get("description", ""),
            published_at=s.get("publishedAt", ""),
            comments=[],
        )

    @classmethod
    def from_json(cls, json_dict: Dict[str, Any]) -> "VideoInfo":
        return cls(
            id=json_dict["id"],
            title=json_dict["title"],
            description=json_dict["description"],
            published_at=json_dict.get("published_at", ""),
            comments=[CommentInfo.from_json(c) for c in json_dict["comments"]],
        )


# --- タイムスタンプ行（抽出結果） -------------------------------------------

@dataclass
class TimeStamp:
    video_id: str
    video_title: str
    published_at: str
    link: str
    timestamp: str
    text: str

    def normalize(self) -> None:
        # HTMLエスケープの &amp; を実体化
        self.link = self.link.replace("&amp;", "&")
        # 前後の空白を除去
        self.text = self.text.strip()

        # --- 先頭ナンバリングを削除 ---
        # 対応例:
        #   "01. 曲名", "02.曲名"
        #   "1) 曲名", "[1] 曲名", "(1) 曲名", "（1）曲名"
        #   "1- 曲名", "1: 曲名", "1：曲名"
        numbering_pattern = r"""
            ^\s*                                   # 先頭空白
            (?:
                [\(\[\uFF08]?\s*\d+\s*[\)\]\uFF09]?  # (1) / [1] / （1）など
                [\.\uFF0E\u3002:\uFF1A\)\]-]*       # 区切り記号
                |                                   # または
                \d+[\.\uFF0E\u3002:\uFF1A\)\]-]*    # 数字から始まる
            )
            \s*                                    # 後続空白
        """
        self.text = re.sub(numbering_pattern, "", self.text, flags=re.VERBOSE)

        # 最終トリム
        self.text = self.text.strip()

    # --- aタグの中にあるタイムスタンプを抽出 ---------------------------------
    @classmethod
    def _from_html_anchors(cls, video_id: str, video_title: str, published_at: str, text: str) -> List["TimeStamp"]:
        """
        <a href=\"https://www.youtube.com/watch?v=...&t=...\">1:23</a> や
        <a href=\"https://youtu.be/...?...&t=...\">1:23</a> に対応。
        """
        pattern = (
            r"<a href=\\\"("
            r"https://(?:www\.)?(?:youtube\.com/watch\?v=[^\"&]+(?:&amp;|&)t=[^\"<>]+|"
            r"youtu\.be/[^\"?<>]+(?:\?|&amp;|&)t=[^\"<>]+)"
            r")\\\"[^>]*>([\d:]+)</a>"
        )
        timestamp_pattern = re.compile(pattern)
        timestamp_list: List[TimeStamp] = []
        line_list = text.split("<br>")
        for line in line_list:
            m = timestamp_pattern.search(line)
            if not m:
                continue
            comment = timestamp_pattern.sub("", line)
            timestamp_list.append(
                cls(
                    video_id=video_id,
                    video_title=video_title,
                    published_at=published_at,
                    link=m[1],
                    timestamp=m[2],
                    text=comment,
                )
            )
        return timestamp_list

    # --- プレーンテキストからの抽出 ------------------------------------------
    @classmethod
    def _from_plain_lines(cls, video_id: str, video_title: str, published_at: str, text: str) -> List["TimeStamp"]:
        """
        素のテキスト例：
            0:33 声入り
            1:10 開始
            1:12
            青と夏 / Mrs. GREEN APPLE
            7:22
            八月の夜 / SILENT SIREN
        行頭の時刻（mm:ss or h:mm:ss）を検出して曲名（注釈）をペアにする。
        """
        ts_re = re.compile(
            r"(?P<ts>(?:\d{1,2}:)?\d{1,2}:\d{2})\s*(?:[-–~]|[ \t　]+)?(?P<rest>.*)"
        )
        results: List[TimeStamp] = []
        pending_ts: str | None = None

        # 改行で割って処理（CRLF→LFに統一）
        lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
        for ln in lines:
            if not ln:
                continue
            m = ts_re.match(ln)
            if m:
                ts = m.group("ts")
                rest = (m.group("rest") or "").strip()
                if rest:
                    results.append(
                        cls(
                            video_id=video_id,
                            video_title=video_title,
                            published_at=published_at,
                            link=f"https://www.youtube.com/watch?v={video_id}&t={ts}",
                            timestamp=ts,
                            text=rest,
                        )
                    )
                    pending_ts = None
                else:
                    pending_ts = ts
            else:
                if pending_ts:
                    results.append(
                        cls(
                            video_id=video_id,
                            video_title=video_title,
                            published_at=published_at,
                            link=f"https://www.youtube.com/watch?v={video_id}&t={pending_ts}",
                            timestamp=pending_ts,
                            text=ln,
                        )
                    )
                    pending_ts = None
                else:
                    # ただの行。スキップ。
                    pass

        return results

    # --- テキスト全体から抽出（HTMLアンカー + プレーンの両対応） -----------
    @classmethod
    def from_text(cls, video_id: str, video_title: str, published_at: str, text: str) -> List["TimeStamp"]:
        out: List[TimeStamp] = []
        out.extend(cls._from_html_anchors(video_id, video_title, published_at, text))
        out.extend(cls._from_plain_lines(video_id, video_title, published_at, text))
        for ts in out:
            ts.normalize()
        return out

    # --- 動画情報（概要欄 + コメント）から一括抽出 --------------------------
    @classmethod
    def from_videoinfo(cls, video_info: "VideoInfo") -> List["TimeStamp"]:
        timestamp_list: List[TimeStamp] = []
        # 概要欄
        timestamp_list.extend(
            cls.from_text(
                video_info.id,
                video_info.title,
                video_info.published_at,
                video_info.description,
            )
        )
        # コメント欄（表示用テキスト）
        for comment in video_info.comments:
            timestamp_list.extend(
                cls.from_text(
                    video_info.id,
                    video_info.title,
                    video_info.published_at,
                    comment.text_display,
                )
            )
        return timestamp_list


__all__ = ["CommentInfo", "VideoInfo", "TimeStamp"]
