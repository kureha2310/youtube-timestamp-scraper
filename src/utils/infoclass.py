# infoclass.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class CommentInfo:
    text_display: str
    text_original: str

    @classmethod
    def from_response_comment(cls, response_comment: Dict[str, Any]) -> "CommentInfo":
        comment_snippet = response_comment["snippet"]
        return cls(
            text_display=comment_snippet["textDisplay"],
            text_original=comment_snippet["textOriginal"],
        )

    @classmethod
    def response_item_to_comment_dict(cls, response_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        comment_list: List[Dict[str, Any]] = []
        comment_list.append(response_item["snippet"]["topLevelComment"])
        replies = response_item.get("replies", [])
        if replies:
            replies = replies["comments"]
        comment_list += replies
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


@dataclass
class VideoInfo:
    id: str
    title: str
    description: str
    published_at: str
    comments: List[CommentInfo]
    stream_start: str = None  # stream_start属性を追加

    @classmethod
    def from_response_snippet(cls, response_snippet: Dict[str, Any]) -> "VideoInfo":
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
            stream_start=json_dict.get("stream_start", None)
        )


@dataclass
class TimeStamp:
    video_id: str
    video_title: str
    published_at: str
    link: str
    timestamp: str
    text: str
    stream_start: str = None  # stream_start属性を追加

    def normalize(self) -> None:
        self.link = self.link.replace("&amp;", "&")
        self.text = self.text.strip()

        # 先頭ナンバリングを削除
        numbering_pattern = r"""
            ^\s*
            (?:
                [\(\[\uFF08]?\s*\d+\s*[\)\]\uFF09]?
                [\.\uFF0E\u3002:\uFF1A\)\]-]*
                |
                \d+[\.\uFF0E\u3002:\uFF1A\)\]-]*
            )
            \s*
        """
        self.text = re.sub(numbering_pattern, "", self.text, flags=re.VERBOSE)
        self.text = self.text.strip()

    @classmethod
    def _from_html_anchors(cls, video_id: str, video_title: str, published_at: str, text: str, stream_start: str = None) -> List["TimeStamp"]:
        # HTMLリンク形式のタイムスタンプを抽出
        # <a href="...&t=413">6:53</a> 1.サイハテ/小林オニキス feat. 初音ミク
        pattern = r'<a href="[^"]*">(\d{1,2}:\d{2}(?::\d{2})?)</a>\s*(.+?)(?=<br>|<a href=|$)'
        
        timestamp_list: List[TimeStamp] = []
        
        # 全体をマッチング（<br>で分割しない）
        matches = re.finditer(pattern, text)
        for match in matches:
            timestamp = match.group(1)
            content = match.group(2).strip()
            
            # HTMLエスケープを元に戻す
            content = content.replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"')
            
            # ナンバリングを除去（1. や (1) など）
            content = re.sub(r'^\s*\d+[\.\)]\s*', '', content)
            
            if content and cls._is_valid_song_timestamp(timestamp, content):
                timestamp_list.append(
                    cls(
                        video_id=video_id,
                        video_title=video_title,
                        published_at=published_at,
                        link=f"https://www.youtube.com/watch?v={video_id}&t={timestamp}",
                        timestamp=timestamp,
                        text=content,
                        stream_start=stream_start
                    )
                )
        return timestamp_list

    @classmethod
    def _from_plain_lines(cls, video_id: str, video_title: str, published_at: str, text: str, stream_start: str = None) -> List["TimeStamp"]:
        results: List[TimeStamp] = []
        
        # \r\nを\nに統一、\rも処理
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = [ln.strip() for ln in text.split('\n')]
        
        for line in lines:
            if not line:
                continue
            
            # タイムスタンプパターン: 行頭から開始（より柔軟に）
            # 6:53 1.サイハテ/小林オニキス feat. 初音ミク
            # 1:07:50 9.炉心融解/iroha(sasaki) feat. 鏡音リン
            match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)', line)
            
            if match:
                timestamp = match.group(1)
                content = match.group(2).strip()
                
                # ナンバリングを除去
                content = re.sub(r'^\s*\d+[\.\)]\s*', '', content)
                
                if cls._is_valid_song_timestamp(timestamp, content):
                    results.append(
                        cls(
                            video_id=video_id,
                            video_title=video_title,
                            published_at=published_at,
                            link=f"https://www.youtube.com/watch?v={video_id}&t={timestamp}",
                            timestamp=timestamp,
                            text=content,
                            stream_start=stream_start
                        )
                    )
        
        return results
    
    @classmethod
    def _is_valid_song_timestamp(cls, timestamp: str, content: str) -> bool:
        # 明らかに無効なパターンを除外（緩和版）
        invalid_patterns = [
            r'^https?://',                    # URLで始まる
            r'^www\.',                        # www.で始まる
            r'^[\d\s\-\.]+$',                 # 数字と記号のみ
            r'^～|^〜',                       # 装飾文字で始まる
        ]
        
        # 特定のキーワードは除外（ただし「声入り」「告知」などは許可）
        exclude_keywords = [
            'セトリ', 'タイムスタンプ', '配信開始', 'くしゃみ', '伸び', '背伸び'
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        # 除外キーワードをチェック（完全一致のみ）
        content_lower = content.lower()
        for keyword in exclude_keywords:
            if keyword.lower() == content_lower or f'{keyword}＆タイムスタンプ' in content or f'セトリ＆{keyword}' in content:
                return False
        
        # 有効な楽曲かチェック
        # 「声入り」「告知」などは許可するが、曲名っぽいものを優先
        # スラッシュがあれば「曲名/アーティスト」形式の可能性が高い
        if '/' in content or 'feat.' in content or 'feat ' in content or 'CV.' in content or 'CV:' in content:
            return True
        
        # 文字（日本語、英語）が含まれている
        if re.search(r'[a-zA-Z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', content):
            # 声入り、告知などの単純なものも一旦許可
            return True
        
        return False
    
    @classmethod
    def _is_clock_time(cls, timestamp: str) -> bool:
        parts = timestamp.split(':')
        
        if len(parts) == 2:
            minutes, seconds = parts
            try:
                if int(minutes) >= 23 and int(seconds) >= 55:
                    return True
            except ValueError:
                return False
        
        return False

    @classmethod
    def from_text(cls, video_id: str, video_title: str, published_at: str, text: str, stream_start: str = None) -> List["TimeStamp"]:
        out: List[TimeStamp] = []
        out.extend(cls._from_html_anchors(video_id, video_title, published_at, text, stream_start))
        out.extend(cls._from_plain_lines(video_id, video_title, published_at, text, stream_start))
        for ts in out:
            ts.normalize()
        return out

    @classmethod
    def from_videoinfo(cls, video_info: "VideoInfo") -> List["TimeStamp"]:
        timestamp_list: List[TimeStamp] = []
        
        # stream_startを取得
        stream_start = getattr(video_info, 'stream_start', None)
        
        # 概要欄
        timestamp_list.extend(
            cls.from_text(
                video_info.id,
                video_info.title,
                video_info.published_at,
                video_info.description,
                stream_start
            )
        )
        
        # コメント欄
        for comment in video_info.comments:
            timestamp_list.extend(
                cls.from_text(
                    video_info.id,
                    video_info.title,
                    video_info.published_at,
                    comment.text_display,
                    stream_start
                )
            )
        return timestamp_list


__all__ = ["CommentInfo", "VideoInfo", "TimeStamp"]