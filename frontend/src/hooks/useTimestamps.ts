import { useState, useEffect } from 'react';
import type { TimestampData, Channel, Mode } from '../types';

export function useTimestamps(mode: Mode) {
  const [data, setData] = useState<TimestampData | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        // データファイルのパス
        const dataFile = mode === 'singing'
          ? '/data/timestamps_singing.json'
          : '/data/timestamps_other.json';

        // タイムスタンプデータを取得
        const timestampsRes = await fetch(dataFile);
        if (!timestampsRes.ok) {
          throw new Error(`データの読み込みに失敗しました: ${timestampsRes.statusText}`);
        }
        const timestampsData = await timestampsRes.json();
        setData(timestampsData);

        // チャンネル情報を取得
        try {
          const channelsRes = await fetch('/data/channels.json');
          if (channelsRes.ok) {
            const channelsData = await channelsRes.json();
            setChannels(channelsData);
          }
        } catch (err) {
          console.warn('チャンネル情報の読み込みをスキップ:', err);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'データの読み込みに失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [mode]);

  return { data, channels, loading, error };
}
