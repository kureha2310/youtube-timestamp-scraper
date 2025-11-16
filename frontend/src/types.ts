export interface Timestamp {
  No: string;
  曲: string;
  '歌手-ユニット': string;
  検索用: string;
  ジャンル: string;
  タイムスタンプ: string;
  配信日: string;
  動画ID: string;
  確度スコア: string;
  チャンネルID?: string;
}

export interface TimestampData {
  last_updated: string;
  total_count: number;
  timestamps: Timestamp[];
}

export interface Channel {
  id: string;
  name: string;
  thumbnail: string;
}

export type Mode = 'singing' | 'all';
export type Genre = '' | 'Vocaloid' | 'アニメ' | 'ゲーム音楽' | 'J-POP' | 'ロック' | 'オルタナティブ' | 'バラード' | 'R&B/ソウル' | 'エレクトロニック' | 'シティポップ' | 'フォーク' | 'パンク' | 'その他';
export type SortBy = 'date-desc' | 'date-asc' | 'song-asc' | 'artist-asc';
