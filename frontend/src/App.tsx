import { useState, useMemo } from 'react';
import { useTimestamps } from './hooks/useTimestamps';
import type { Mode, Genre, SortBy } from './types';

function App() {
  const [mode, setMode] = useState<Mode>('singing');
  const [searchTerm, setSearchTerm] = useState('');
  const [genreFilter, setGenreFilter] = useState<Genre>('');
  const [sortBy, setSortBy] = useState<SortBy>('date-desc');
  const [activeChannels, setActiveChannels] = useState<Set<string>>(new Set());

  const { data, channels, loading, error } = useTimestamps(mode);

  // フィルター & ソート
  const filteredData = useMemo(() => {
    if (!data) return [];

    let filtered = data.timestamps.filter((item) => {
      // チャンネルフィルター
      if (activeChannels.size > 0 && item.チャンネルID) {
        if (!activeChannels.has(item.チャンネルID)) return false;
      }

      // 検索フィルター
      if (searchTerm) {
        const searchFields = [
          item.曲,
          item['歌手-ユニット'],
          item.動画ID,
          item.検索用,
        ].join(' ').toLowerCase();

        if (!searchFields.includes(searchTerm.toLowerCase())) return false;
      }

      // ジャンルフィルター
      if (genreFilter && item.ジャンル !== genreFilter) {
        return false;
      }

      return true;
    });

    // ソート
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date-desc':
          return new Date(b.配信日 || 0).getTime() - new Date(a.配信日 || 0).getTime();
        case 'date-asc':
          return new Date(a.配信日 || 0).getTime() - new Date(b.配信日 || 0).getTime();
        case 'song-asc':
          return (a.曲 || '').localeCompare(b.曲 || '', 'ja');
        case 'artist-asc':
          return (a['歌手-ユニット'] || '').localeCompare(b['歌手-ユニット'] || '', 'ja');
        default:
          return 0;
      }
    });

    return filtered;
  }, [data, searchTerm, genreFilter, sortBy, activeChannels]);

  // チャンネル切り替え
  const toggleChannel = (channelId: string) => {
    const newChannels = new Set(activeChannels);
    if (newChannels.has(channelId)) {
      newChannels.delete(channelId);
    } else {
      newChannels.add(channelId);
    }
    setActiveChannels(newChannels);
  };

  // チャンネルごとの楽曲数を集計
  const channelCounts = useMemo(() => {
    if (!data) return {};
    const counts: Record<string, number> = {};
    data.timestamps.forEach((item) => {
      if (item.チャンネルID) {
        counts[item.チャンネルID] = (counts[item.チャンネルID] || 0) + 1;
      }
    });
    return counts;
  }, [data]);

  const getGenreClass = (genre: string) => {
    const map: Record<string, string> = {
      Vocaloid: 'bg-indigo-100 text-indigo-700 border-indigo-300',
      'J-POP': 'bg-pink-100 text-pink-700 border-pink-300',
      アニメ: 'bg-purple-100 text-purple-700 border-purple-300',
    };
    return map[genre] || 'bg-gray-100 text-gray-700 border-gray-300';
  };

  const convertTimestampToSeconds = (timestamp: string) => {
    const parts = timestamp.split(':').map(Number).filter((n) => !isNaN(n));
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return 0;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">データを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="text-center text-red-600">
          <p className="text-xl font-semibold mb-2">エラーが発生しました</p>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* ヘッダー */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-indigo-600 to-pink-600 bg-clip-text text-transparent">
                🎵 歌枠タイムスタンプ一覧
              </h1>
              <p className="text-xs text-gray-600 mt-0.5">
                5人の配信者の歌ってみた楽曲データベース
              </p>
            </div>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              <button
                onClick={() => setMode('singing')}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
                  mode === 'singing'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-gray-700 hover:bg-gray-200'
                }`}
              >
                🎤 歌枠
              </button>
              <button
                onClick={() => setMode('all')}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-all ${
                  mode === 'all'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-gray-700 hover:bg-gray-200'
                }`}
              >
                📊 総合
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-4 space-y-4">
        {/* チャンネルフィルター */}
        <section className="bg-white rounded-lg p-3 shadow-sm border border-gray-200">
          <h2 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <span className="text-indigo-600">👤</span>
            配信者で絞り込み
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {channels.map((channel) => (
              <button
                key={channel.id}
                onClick={() => toggleChannel(channel.id)}
                className={`flex items-center gap-2 p-2 rounded border transition-all ${
                  activeChannels.has(channel.id)
                    ? 'border-indigo-500 bg-indigo-50 shadow-sm'
                    : 'border-gray-200 hover:border-indigo-300'
                }`}
              >
                <img
                  src={channel.thumbnail}
                  alt={channel.name}
                  className="w-8 h-8 rounded-full object-cover flex-shrink-0"
                />
                <div className="flex-1 text-left min-w-0">
                  <div className="font-medium text-xs truncate">{channel.name}</div>
                  <div className="text-xs text-gray-500">
                    {channelCounts[channel.id] || 0}曲
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* 検索・フィルター */}
        <section className="bg-white rounded-lg p-3 shadow-sm border border-gray-200">
          <div className="space-y-2">
            <input
              type="text"
              placeholder="🔍 曲名、アーティスト、動画IDで検索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded focus:border-indigo-500 focus:outline-none transition-colors"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <select
                value={genreFilter}
                onChange={(e) => setGenreFilter(e.target.value as Genre)}
                className="px-3 py-2 text-sm border border-gray-200 rounded focus:border-indigo-500 focus:outline-none transition-colors bg-white"
              >
                <option value="">すべてのジャンル</option>
                <option value="Vocaloid">Vocaloid</option>
                <option value="J-POP">J-POP</option>
                <option value="アニメ">アニメ</option>
                <option value="その他">その他</option>
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="px-3 py-2 text-sm border border-gray-200 rounded focus:border-indigo-500 focus:outline-none transition-colors bg-white"
              >
                <option value="date-desc">配信日（新しい順）</option>
                <option value="date-asc">配信日（古い順）</option>
                <option value="song-asc">曲名（昇順）</option>
                <option value="artist-asc">アーティスト（昇順）</option>
              </select>
            </div>
          </div>
        </section>

        {/* 統計 */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg p-3 text-white shadow-sm">
            <div className="text-xl font-bold">{data?.total_count.toLocaleString()}</div>
            <div className="text-indigo-100 text-xs">総楽曲数</div>
          </div>
          <div className="bg-gradient-to-br from-pink-500 to-pink-600 rounded-lg p-3 text-white shadow-sm">
            <div className="text-xl font-bold">
              {new Set(data?.timestamps.map((t) => t.動画ID)).size.toLocaleString()}
            </div>
            <div className="text-pink-100 text-xs">配信数</div>
          </div>
          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg p-3 text-white shadow-sm">
            <div className="text-xl font-bold">{filteredData.length.toLocaleString()}</div>
            <div className="text-purple-100 text-xs">表示中</div>
          </div>
        </div>

        {/* テーブル */}
        <section className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase">No</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase">曲名</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase hidden md:table-cell">アーティスト</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase">ジャンル</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase hidden lg:table-cell">TS</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase hidden lg:table-cell">配信日</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-gray-600 uppercase">動画</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredData.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-gray-500">
                      検索条件に一致する楽曲が見つかりませんでした
                    </td>
                  </tr>
                ) : (
                  filteredData.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50 transition-colors">
                      <td className="px-2 py-2 text-xs text-gray-900">{index + 1}</td>
                      <td className="px-2 py-2">
                        <div className="text-sm font-medium text-gray-900">{item.曲}</div>
                        <div className="text-xs text-gray-500 md:hidden">{item['歌手-ユニット'] || '-'}</div>
                      </td>
                      <td className="px-2 py-2 text-sm text-gray-600 hidden md:table-cell">{item['歌手-ユニット'] || '-'}</td>
                      <td className="px-2 py-2">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${getGenreClass(item.ジャンル)}`}>
                          {item.ジャンル}
                        </span>
                      </td>
                      <td className="px-2 py-2 text-xs font-mono text-gray-900 hidden lg:table-cell">{item.タイムスタンプ}</td>
                      <td className="px-2 py-2 text-xs text-gray-600 hidden lg:table-cell">{item.配信日}</td>
                      <td className="px-2 py-2">
                        <a
                          href={`https://www.youtube.com/watch?v=${item.動画ID}&t=${convertTimestampToSeconds(item.タイムスタンプ)}s`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-2 py-1 bg-gradient-to-r from-indigo-500 to-indigo-600 text-white text-xs rounded hover:from-indigo-600 hover:to-indigo-700 transition-all whitespace-nowrap"
                        >
                          ▶
                        </a>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {/* フッター */}
      <footer className="mt-12 py-6 text-center text-xs md:text-sm text-gray-500 border-t border-gray-200">
        <p>© 2025 歌枠タイムスタンプ一覧 | Data powered by YouTube Data API v3</p>
        <p className="mt-1">最終更新: {data?.last_updated}</p>
      </footer>
    </div>
  );
}

export default App;
