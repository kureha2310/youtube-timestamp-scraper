// ===== グローバル変数 =====
let allData = [];
let filteredData = [];
let activeChannels = new Set();
let filterTimeout = null;
let currentMode = 'all'; // 'singing' or 'all'
const channels = {
    'UCHM_SLi7s0AJ8UBmm3pWN6Q': { name: 'ふくもつく', thumbnail: '' },
    'UCmM2LkAA9WYFZor1k_szNew': { name: '九文字ポルポ', thumbnail: '' },
    'UCMf7-2iEzioOK6t_T7mVvDQ': { name: '月儚リン', thumbnail: '' },
    'UCiVwDkYw01KbZwZl5s7b9IQ': { name: '琉華メイファン', thumbnail: '' },
    'UCgaaW1hyIQQ6rQg0cfPASsA': { name: '狛ノヰみつ', thumbnail: '' }
};

// ===== 初期化 =====
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    await loadChannelThumbnails();
    await loadData();
    initEventListeners();
    applyFilters();
});

// ===== テーマ管理 =====
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');
        if (icon) {
            icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    showToast(`テーマを${newTheme === 'dark' ? 'ダーク' : 'ライト'}モードに切り替えました`);
}

// ===== トースト通知 =====
function showToast(message, duration = 3000) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.innerHTML = `<i class="fas fa-info-circle"></i><span>${message}</span>`;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// ===== データ読み込み =====
async function loadData() {
    try {
        // 現在のモードに応じてJSONファイルを読み込み
        const jsonFile = currentMode === 'singing' 
            ? 'data/timestamps_singing.json' 
            : 'data/timestamps_all.json';
        
        let response = await fetch(jsonFile);
        let data;
        
        if (!response.ok) {
            // フォールバック: 旧ファイル名を試す
            response = await fetch('data/timestamps.json');
            if (!response.ok) {
                throw new Error('データファイルが見つかりません');
            }
        }
        
        data = await response.json();
        allData = data.timestamps || [];

        console.log(`データ読み込み成功 (${currentMode === 'singing' ? '歌枠モード' : '総合モード'}): ${allData.length}件`);

        // 最終更新日を設定
        const lastUpdateEl = document.getElementById('lastUpdate');
        if (lastUpdateEl) {
            lastUpdateEl.textContent = data.last_updated || new Date().toLocaleDateString('ja-JP');
        }

        // 統計情報を更新
        updateStats();
        initChannelFilter();
        applyFilters();
        showToast(`${allData.length.toLocaleString()}件のデータを読み込みました (${currentMode === 'singing' ? '歌枠モード' : '総合モード'})`);
    } catch (error) {
        console.error('データ読み込みエラー:', error);
        const loading = document.getElementById('loading');
        if (loading) {
            loading.innerHTML = `<p style="color: #ef4444;">データの読み込みに失敗しました: ${error.message}</p>`;
        }
        showToast('データの読み込みに失敗しました', 5000);
    }
}

// ===== モード切り替え =====
function switchMode(mode) {
    if (currentMode === mode) return;
    
    // 現在のチャンネル選択状態を保存
    const currentActiveChannels = new Set(activeChannels);
    
    currentMode = mode;
    const modeButtons = document.querySelectorAll('.mode-btn');
    modeButtons.forEach(btn => {
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // チャンネル選択状態をクリア
    activeChannels.clear();
    
    // データを再読み込み（loadData内でinitChannelFilterが呼ばれる）
    loadData().then(() => {
        // データ読み込み後にチャンネル選択状態を復元
        currentActiveChannels.forEach(channelId => {
            if (channels[channelId]) {
                activeChannels.add(channelId);
                const card = document.querySelector(`.channel-card[data-channel-id="${channelId}"]`);
                if (card) {
                    card.classList.add('active');
                }
            }
        });
        // フィルターを再適用
        applyFilters();
    });
}

// グローバルスコープに公開
window.switchMode = switchMode;

// ===== チャンネルサムネイル読み込み =====
async function loadChannelThumbnails() {
    try {
        const response = await fetch('data/channels.json');
        if (response.ok) {
            const channelsData = await response.json();
            channelsData.forEach(ch => {
                if (channels[ch.id]) {
                    channels[ch.id].thumbnail = ch.thumbnail;
                }
            });
        }
    } catch (error) {
        console.log('チャンネル情報の読み込みをスキップ');
    }
}

// ===== チャンネルフィルター初期化 =====
function initChannelFilter() {
    const container = document.getElementById('channelFilter');
    if (!container) return;

    // 既存の要素をクリア
    container.innerHTML = '';

    // チャンネルごとの楽曲数を集計
    const channelCounts = {};
    allData.forEach(item => {
        if (item.動画ID && item.チャンネルID) {
            const channelId = item.チャンネルID;
            if (channels[channelId]) {
                channelCounts[channelId] = (channelCounts[channelId] || 0) + 1;
            }
        }
    });

    Object.entries(channels).forEach(([id, info]) => {
        const count = channelCounts[id] || 0;

        const card = document.createElement('div');
        card.className = 'channel-card';
        card.dataset.channelId = id;
        
        // 以前に選択されていたチャンネルを復元
        if (activeChannels.has(id)) {
            card.classList.add('active');
        }

        // サムネイルがあれば表示、なければプレースホルダー
        const thumbnailUrl = info.thumbnail || 
            `https://ui-avatars.com/api/?name=${encodeURIComponent(info.name)}&size=112&background=6366f1&color=fff&bold=true`;

        card.innerHTML = `
            <img class="channel-avatar" src="${thumbnailUrl}" alt="${info.name}"
                 loading="lazy"
                 onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(info.name)}&size=112&background=6366f1&color=fff&bold=true'">
            <div class="channel-info">
                <div class="channel-name">${escapeHtml(info.name)}</div>
                <div class="channel-count">${count.toLocaleString()}曲</div>
            </div>
        `;

        card.addEventListener('click', () => toggleChannel(id, card));
        container.appendChild(card);
    });
}

// ===== チャンネルフィルター切り替え =====
function toggleChannel(channelId, card) {
    if (activeChannels.has(channelId)) {
        activeChannels.delete(channelId);
        card.classList.remove('active');
    } else {
        activeChannels.add(channelId);
        card.classList.add('active');
    }
    updateClearFiltersButton();
    applyFilters();
}

// ===== イベントリスナー設定 =====
function initEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const searchClear = document.getElementById('searchClear');
    const genreFilter = document.getElementById('genreFilter');
    const sortBy = document.getElementById('sortBy');
    const clearFilters = document.getElementById('clearFilters');

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            // 検索クリアボタンの表示/非表示
            if (searchClear) {
                searchClear.style.display = e.target.value ? 'flex' : 'none';
            }
            // デバウンス処理
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(() => {
                applyFilters();
            }, 300);
        });
    }

    if (searchClear) {
        searchClear.addEventListener('click', () => {
            if (searchInput) {
                searchInput.value = '';
                searchClear.style.display = 'none';
                applyFilters();
            }
        });
    }

    if (genreFilter) {
        genreFilter.addEventListener('change', applyFilters);
    }

    if (sortBy) {
        sortBy.addEventListener('change', applyFilters);
    }

    if (clearFilters) {
        clearFilters.addEventListener('click', clearAllFilters);
    }

    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', clearAllFilters);
    }
}

// ===== フィルタークリア =====
function clearAllFilters() {
    const searchInput = document.getElementById('searchInput');
    const searchClear = document.getElementById('searchClear');
    const genreFilter = document.getElementById('genreFilter');
    const sortBy = document.getElementById('sortBy');

    if (searchInput) searchInput.value = '';
    if (searchClear) searchClear.style.display = 'none';
    if (genreFilter) genreFilter.value = '';
    if (sortBy) sortBy.value = 'date-desc';

    activeChannels.clear();
    document.querySelectorAll('.channel-card.active').forEach(card => {
        card.classList.remove('active');
    });

    updateClearFiltersButton();
    applyFilters();
    showToast('すべてのフィルターをクリアしました');
}

// ===== クリアフィルターボタンの表示/非表示 =====
function updateClearFiltersButton() {
    const clearFilters = document.getElementById('clearFilters');
    if (!clearFilters) return;

    const searchInput = document.getElementById('searchInput');
    const genreFilter = document.getElementById('genreFilter');
    const hasSearch = searchInput && searchInput.value.trim() !== '';
    const hasGenre = genreFilter && genreFilter.value !== '';
    const hasChannels = activeChannels.size > 0;

    clearFilters.style.display = (hasSearch || hasGenre || hasChannels) ? 'flex' : 'none';
}

// ===== フィルター適用 =====
function applyFilters() {
    const searchInput = document.getElementById('searchInput');
    const genreFilter = document.getElementById('genreFilter');

    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const genreFilterValue = genreFilter ? genreFilter.value : '';

    filteredData = allData.filter(item => {
        // チャンネルフィルター
        if (activeChannels.size > 0) {
            const channelId = item.チャンネルID || getChannelIdFromVideoId(item.動画ID);
            if (!channelId || !activeChannels.has(channelId)) return false;
        }

        // 検索フィルター
        if (searchTerm) {
            const searchFields = [
                item.曲 || '',
                item['歌手-ユニット'] || '',
                item.動画ID || '',
                item.検索用 || ''
            ].join(' ').toLowerCase();

            if (!searchFields.includes(searchTerm)) return false;
        }

        // ジャンルフィルター
        if (genreFilterValue && item.ジャンル !== genreFilterValue) {
            return false;
        }

        return true;
    });

    // ソート適用
    applySorting();

    // テーブル更新
    renderTable();
    updateFilteredCount();
    updateClearFiltersButton();
}

// ===== ソート適用 =====
function applySorting() {
    const sortBy = document.getElementById('sortBy');
    if (!sortBy) return;

    const sortValue = sortBy.value;

    filteredData.sort((a, b) => {
        switch(sortValue) {
            case 'date-desc':
                return new Date(b.配信日 || 0) - new Date(a.配信日 || 0);
            case 'date-asc':
                return new Date(a.配信日 || 0) - new Date(b.配信日 || 0);
            case 'song-asc':
                return (a.曲 || '').localeCompare(b.曲 || '', 'ja');
            case 'artist-asc':
                return (a['歌手-ユニット'] || '').localeCompare(b['歌手-ユニット'] || '', 'ja');
            default:
                return 0;
        }
    });
}

// ===== テーブル描画 =====
function renderTable() {
    const tbody = document.getElementById('tableBody');
    const loading = document.getElementById('loading');
    const noResults = document.getElementById('noResults');

    if (loading) loading.style.display = 'none';

    if (!tbody) return;

    if (filteredData.length === 0) {
        tbody.innerHTML = '';
        if (noResults) noResults.style.display = 'block';
        return;
    }

    if (noResults) noResults.style.display = 'none';

    // パフォーマンス最適化: バッチ処理
    const fragment = document.createDocumentFragment();
    
    filteredData.forEach((item, index) => {
        const genreClass = getGenreClass(item.ジャンル);
        const channelName = getChannelName(item.動画ID);
        const videoUrl = `https://www.youtube.com/watch?v=${item.動画ID}&t=${convertTimestampToSeconds(item.タイムスタンプ)}s`;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td><strong>${escapeHtml(item.曲 || '-')}</strong></td>
            <td>${escapeHtml(item['歌手-ユニット'] || '-')}</td>
            <td><span class="genre-tag ${genreClass}">${escapeHtml(item.ジャンル || '-')}</span></td>
            <td><code style="background: var(--color-bg-light); padding: 0.25rem 0.5rem; border-radius: 4px; font-family: 'Courier New', monospace;">${escapeHtml(item.タイムスタンプ || '-')}</code></td>
            <td>${escapeHtml(item.配信日 || '-')}</td>
            <td>${escapeHtml(channelName)}</td>
            <td><a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="video-link"><i class="fas fa-play"></i> 視聴</a></td>
        `;
        fragment.appendChild(tr);
    });

    tbody.innerHTML = '';
    tbody.appendChild(fragment);
}

// ===== 統計情報更新 =====
function updateStats() {
    const uniqueVideos = new Set(allData.map(item => item.動画ID).filter(Boolean)).size;

    const totalSongs = document.getElementById('totalSongs');
    const totalVideos = document.getElementById('totalVideos');

    if (totalSongs) {
        totalSongs.textContent = allData.length.toLocaleString();
    }
    if (totalVideos) {
        totalVideos.textContent = uniqueVideos.toLocaleString();
    }
}

function updateFilteredCount() {
    const filteredCount = document.getElementById('filteredCount');
    if (filteredCount) {
        filteredCount.textContent = filteredData.length.toLocaleString();
    }
}

// ===== ユーティリティ関数 =====
function getGenreClass(genre) {
    const map = {
        'Vocaloid': 'vocaloid',
        'J-POP': 'jpop',
        'アニメ': 'anime'
    };
    return map[genre] || 'other';
}

function getChannelIdFromVideoId(videoId) {
    if (!videoId) return null;
    
    // データからチャンネルIDを取得
    const item = allData.find(d => d.動画ID === videoId);
    if (item && item.チャンネルID) {
        return item.チャンネルID;
    }
    
    // フォールバック: 動画IDが一致する最初のアイテムを探す
    if (item) {
        // 同じ動画IDを持つ他のアイテムからチャンネルIDを取得
        const sameVideoItem = allData.find(d => d.動画ID === videoId && d.チャンネルID);
        if (sameVideoItem && sameVideoItem.チャンネルID) {
            return sameVideoItem.チャンネルID;
        }
    }
    
    // それでも見つからない場合はnullを返す
    return null;
}

function getChannelName(videoId) {
    const channelId = getChannelIdFromVideoId(videoId);
    return channels[channelId]?.name || '不明';
}

function convertTimestampToSeconds(timestamp) {
    if (!timestamp) return 0;

    const parts = timestamp.split(':').map(Number).filter(n => !isNaN(n));
    if (parts.length === 2) {
        return parts[0] * 60 + parts[1];
    } else if (parts.length === 3) {
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return 0;
}

function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// ===== パフォーマンス最適化: デバウンス =====
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===== エクスポート（グローバルスコープで使用） =====
window.applyFilters = applyFilters;
