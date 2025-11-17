import { useState, useMemo, useEffect } from 'react';
import { useTimestamps } from './hooks/useTimestamps';
import type { Mode, Genre, SortBy } from './types';

function App() {
  const [mode, setMode] = useState<Mode>('singing');
  const [searchTerm, setSearchTerm] = useState('');
  const [genreFilter, setGenreFilter] = useState<Genre>('');
  const [sortBy, setSortBy] = useState<SortBy>('date-desc');
  const [activeChannels, setActiveChannels] = useState<Set<string>>(new Set());
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const { data, channels, loading, error } = useTimestamps(mode);

  // フィルター & ソート
  const filteredData = useMemo(() => {
    if (!data) return [];

    let filtered = data.timestamps.filter((item) => {
      if (activeChannels.size > 0 && item.チャンネルID) {
        if (!activeChannels.has(item.チャンネルID)) return false;
      }

      if (searchTerm) {
        const searchFields = [
          item.曲,
          item['歌手-ユニット'],
          item.動画ID,
          item.検索用,
        ].join(' ').toLowerCase();

        if (!searchFields.includes(searchTerm.toLowerCase())) return false;
      }

      if (genreFilter && item.ジャンル !== genreFilter) {
        return false;
      }

      return true;
    });

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

  const toggleChannel = (channelId: string) => {
    const newChannels = new Set(activeChannels);
    if (newChannels.has(channelId)) {
      newChannels.delete(channelId);
    } else {
      newChannels.add(channelId);
    }
    setActiveChannels(newChannels);
  };

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
      'Vocaloid': 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300',
      'アニメ': 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300',
      'ゲーム音楽': 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
      'J-POP': 'bg-pink-100 dark:bg-pink-900/40 text-pink-700 dark:text-pink-300',
      'ロック': 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
      'オルタナティブ': 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300',
      'バラード': 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
      'R&B/ソウル': 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',
      'エレクトロニック': 'bg-cyan-100 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300',
      'シティポップ': 'bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300',
      'フォーク': 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300',
      'パンク': 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300',
    };
    return map[genre] || 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300';
  };

  const convertTimestampToSeconds = (timestamp: string) => {
    const parts = timestamp.split(':').map(Number).filter((n) => !isNaN(n));
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return 0;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50/30 to-purple-50/20">
        <div className="text-center">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-pink-600 rounded-full blur-2xl opacity-50 animate-pulse"></div>
            <div className="relative w-20 h-20 border-4 border-indigo-600/30 border-t-indigo-600 rounded-full animate-spin mx-auto mb-6"></div>
          </div>
          <p className="text-slate-700 dark:text-slate-300 text-lg font-bold">データを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50/30 to-purple-50/20">
        <div className="elegant-card elegant-card-dark p-12 text-center max-w-md mx-4">
          <div className="relative mb-6">
            <div className="absolute inset-0 bg-red-600/20 rounded-full blur-2xl"></div>
            <i className="fas fa-exclamation-triangle text-7xl text-red-600 relative"></i>
          </div>
          <p className="text-2xl font-black text-slate-900 dark:text-white mb-3">エラーが発生しました</p>
          <p className="text-base text-slate-600 dark:text-slate-400 font-medium">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* ヘッダー */}
      <header className="sticky top-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm shadow-sm border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-[1800px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-2 rounded-lg">
                <i className="fas fa-clock text-white text-lg"></i>
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-white">タイムスタンプ一覧</h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">5人の配信者 • {data?.total_count.toLocaleString() || 0}件</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* ダークモードトグル */}
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                aria-label="ダークモード切替"
              >
                {darkMode ? (
                  <i className="fas fa-sun text-lg"></i>
                ) : (
                  <i className="fas fa-moon text-lg"></i>
                )}
              </button>

              <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                <button
                  onClick={() => setMode('singing')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${
                    mode === 'singing'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  <i className="fas fa-music text-xs"></i>
                  歌枠のみ
                </button>
                <button
                  onClick={() => setMode('all')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${
                    mode === 'all'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  <i className="fas fa-list text-xs"></i>
                  総合
                </button>
              </div>
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <i className={`fas ${darkMode ? 'fa-sun' : 'fa-moon'} text-slate-700 dark:text-slate-300`}></i>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1800px] mx-auto px-4 py-4 space-y-4">
        {/* フィルターバー */}
        <div className="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-3">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
            {/* 検索 */}
            <div className="lg:col-span-4">
              <div className="relative">
                <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
                <input
                  type="text"
                  placeholder="曲名、アーティスト、動画IDで検索..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-8 py-2 text-sm border border-slate-200 dark:border-slate-700 rounded-lg focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all outline-none bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                />
                {searchTerm && (
                  <button
                    onClick={() => setSearchTerm('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                  >
                    <i className="fas fa-times text-xs"></i>
                  </button>
                )}
              </div>
            </div>

            {/* ジャンル */}
            <div className="lg:col-span-2">
              <select
                value={genreFilter}
                onChange={(e) => setGenreFilter(e.target.value as Genre)}
                className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-700 rounded-lg focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all outline-none bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              >
                <option value="">すべてのジャンル</option>
                <optgroup label="主要ジャンル">
                  <option value="Vocaloid">🎤 Vocaloid</option>
                  <option value="アニメ">🎬 アニメ</option>
                  <option value="ゲーム音楽">🎮 ゲーム音楽</option>
                  <option value="J-POP">🎵 J-POP</option>
                </optgroup>
                <optgroup label="サブジャンル">
                  <option value="ロック">🎸 ロック</option>
                  <option value="オルタナティブ">🎧 オルタナティブ</option>
                  <option value="パンク">⚡ パンク</option>
                  <option value="バラード">🎹 バラード</option>
                  <option value="R&B/ソウル">🎺 R&B/ソウル</option>
                  <option value="エレクトロニック">🎛️ エレクトロニック</option>
                  <option value="シティポップ">🌆 シティポップ</option>
                  <option value="フォーク">🍃 フォーク</option>
                </optgroup>
                <option value="その他">📀 その他</option>
              </select>
            </div>

            {/* ソート */}
            <div className="lg:col-span-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-700 rounded-lg focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all outline-none bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              >
                <option value="date-desc">配信日（新しい順）</option>
                <option value="date-asc">配信日（古い順）</option>
                <option value="song-asc">曲名（昇順）</option>
                <option value="artist-asc">アーティスト（昇順）</option>
              </select>
            </div>

            {/* 配信者フィルター */}
            <div className="lg:col-span-4 flex items-center gap-2 flex-wrap">
              {channels.map((channel) => (
                <button
                  key={channel.id}
                  onClick={() => toggleChannel(channel.id)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    activeChannels.has(channel.id)
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-indigo-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                  title={channel.name}
                >
                  <img
                    src={channel.thumbnail || `https://ui-avatars.com/api/?name=${encodeURIComponent(channel.name)}&size=32&background=6366f1&color=fff&bold=true`}
                    alt={channel.name}
                    className="w-5 h-5 rounded-full object-cover"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(channel.name)}&size=32&background=6366f1&color=fff&bold=true`;
                    }}
                  />
                  <span className="max-w-[80px] truncate">{channel.name}</span>
                  <span className="text-[10px] opacity-70">({channelCounts[channel.id] || 0})</span>
                </button>
              ))}
              {activeChannels.size > 0 && (
                <button
                  onClick={() => setActiveChannels(new Set())}
                  className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
                >
                  <i className="fas fa-times text-[10px]"></i>
                  クリア
                </button>
              )}
            </div>
          </div>

          {/* 結果数 */}
          <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
            <span className="font-medium text-slate-900 dark:text-white">{filteredData.length.toLocaleString()}</span>件 表示中
            {data && <span className="ml-2">/ 全{data.total_count.toLocaleString()}件</span>}
            {data && <span className="ml-2">• {new Set(data.timestamps.map((t) => t.動画ID)).size.toLocaleString()}配信</span>}
          </div>
        </div>

        {/* テーブル */}
        <section className="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-400">No</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-400">曲名</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 hidden md:table-cell">アーティスト</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-400">ジャンル</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 hidden lg:table-cell">TS</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 hidden lg:table-cell">配信日</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 dark:text-slate-400">動画</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredData.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center gap-3">
                        <i className="fas fa-search text-4xl text-slate-300 dark:text-slate-600"></i>
                        <div>
                          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">検索条件に一致するタイムスタンプが見つかりませんでした</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">別の条件で検索してみてください</p>
                        </div>
                        <button
                          onClick={() => {
                            setSearchTerm('');
                            setGenreFilter('');
                            setActiveChannels(new Set());
                          }}
                          className="mt-2 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-1.5"
                        >
                          <i className="fas fa-redo text-[10px]"></i>
                          フィルターをリセット
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredData.map((item, index) => (
                    <tr key={`${item.動画ID}-${item.タイムスタンプ}-${index}`} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                      <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{index + 1}</td>
                      <td className="px-3 py-2.5">
                        <div className="font-semibold text-slate-900 dark:text-white">{item.曲 || '-'}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 md:hidden mt-0.5">{item['歌手-ユニット'] || '-'}</div>
                      </td>
                      <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300 hidden md:table-cell">{item['歌手-ユニット'] || '-'}</td>
                      <td className="px-3 py-2.5">
                        <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${getGenreClass(item.ジャンル)}`}>
                          {item.ジャンル || 'その他'}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 font-mono text-xs text-slate-700 dark:text-slate-300 hidden lg:table-cell">{item.タイムスタンプ || '-'}</td>
                      <td className="px-3 py-2.5 text-xs text-slate-600 dark:text-slate-400 hidden lg:table-cell">{item.配信日 || '-'}</td>
                      <td className="px-3 py-2.5">
                        <a
                          href={`https://www.youtube.com/watch?v=${item.動画ID}&t=${convertTimestampToSeconds(item.タイムスタンプ)}s`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                        >
                          <i className="fas fa-play text-[10px]"></i>
                          視聴
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
      <footer className="mt-8 py-6 text-center">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          © 2025 タイムスタンプ一覧 | Data powered by YouTube Data API v3 | 最終更新: {data?.last_updated}
        </p>
      </footer>
    </div>
  );
}

export default App;
