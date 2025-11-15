// ===== グローバル変数 =====
let allData = [];
let filteredData = [];
let activeChannels = new Set();
const channels = {
    'UCHM_SLi7s0AJ8UBmm3pWN6Q': { name: 'ふくもつく', thumbnail: '' },
    'UCmM2LkAA9WYFZor1k_szNew': { name: '九文字ポルポ', thumbnail: '' },
    'UCMf7-2iEzioOK6t_T7mVvDQ': { name: '月儚リン', thumbnail: '' },
    'UCiVwDkYw01KbZwZl5s7b9IQ': { name: '琉華メイファン', thumbnail: '' },
    'UCgaaW1hyIQQ6rQg0cfPASsA': { name: '狛ノヰみつ', thumbnail: '' }
};

// ===== 初期化 =====
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    await loadChannelThumbnails();
    initChannelFilter();
    initEventListeners();
    applyFilters();
});

// ===== データ読み込み =====
async function loadData() {
    try {
        const response = await fetch('data/timestamps.json');
        if (!response.ok) {
            throw new Error('データファイルが見つかりません');
        }
        const data = await response.json();
        allData = data.timestamps || [];

        // 最終更新日を設定
        document.getElementById('lastUpdate').textContent =
            data.last_updated || new Date().toLocaleDateString('ja-JP');

        // 統計情報を更新
        updateStats();
    } catch (error) {
        console.error('データ読み込みエラー:', error);
        document.getElementById('loading').innerHTML =
            '<p style="color: #d32f2f;">データの読み込みに失敗しました</p>';
    }
}

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

    Object.entries(channels).forEach(([id, info]) => {
        // 各チャンネルの楽曲数を集計
        const count = allData.filter(item => item.動画ID &&
            allData.some(d => d.動画ID === item.動画ID && getChannelId(d.動画ID) === id)
        ).length;

        const card = document.createElement('div');
        card.className = 'channel-card';
        card.dataset.channelId = id;

        // サムネイルがあれば表示、なければプレースホルダー
        const thumbnailUrl = info.thumbnail || `https://ui-avatars.com/api/?name=${encodeURIComponent(info.name)}&size=96&background=4b9cfb&color=fff`;

        card.innerHTML = `
            <img class="channel-avatar" src="${thumbnailUrl}" alt="${info.name}"
                 onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(info.name)}&size=96&background=4b9cfb&color=fff'">
            <div class="channel-info">
                <div class="channel-name">${info.name}</div>
                <div class="channel-count">${count}曲</div>
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
    applyFilters();
}

// ===== イベントリスナー設定 =====
function initEventListeners() {
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    document.getElementById('genreFilter').addEventListener('change', applyFilters);
    document.getElementById('sortBy').addEventListener('change', applyFilters);
}

// ===== フィルター適用 =====
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const genreFilter = document.getElementById('genreFilter').value;

    filteredData = allData.filter(item => {
        // チャンネルフィルター
        if (activeChannels.size > 0) {
            const channelId = getChannelIdFromVideoId(item.動画ID);
            if (!activeChannels.has(channelId)) return false;
        }

        // 検索フィルター
        if (searchTerm) {
            const searchFields = [
                item.曲 || '',
                item['歌手-ユニット'] || '',
                item.動画ID || ''
            ].join(' ').toLowerCase();

            if (!searchFields.includes(searchTerm)) return false;
        }

        // ジャンルフィルター
        if (genreFilter && item.ジャンル !== genreFilter) {
            return false;
        }

        return true;
    });

    // ソート適用
    applySorting();

    // テーブル更新
    renderTable();
    updateFilteredCount();
}

// ===== ソート適用 =====
function applySorting() {
    const sortBy = document.getElementById('sortBy').value;

    filteredData.sort((a, b) => {
        switch(sortBy) {
            case 'date-desc':
                return new Date(b.配信日) - new Date(a.配信日);
            case 'date-asc':
                return new Date(a.配信日) - new Date(b.配信日);
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

    loading.style.display = 'none';

    if (filteredData.length === 0) {
        tbody.innerHTML = '';
        noResults.style.display = 'block';
        return;
    }

    noResults.style.display = 'none';

    tbody.innerHTML = filteredData.map((item, index) => {
        const genreClass = getGenreClass(item.ジャンル);
        const channelName = getChannelName(item.動画ID);
        const videoUrl = `https://www.youtube.com/watch?v=${item.動画ID}&t=${convertTimestampToSeconds(item.タイムスタンプ)}s`;

        return `
            <tr>
                <td>${index + 1}</td>
                <td><strong>${escapeHtml(item.曲 || '-')}</strong></td>
                <td>${escapeHtml(item['歌手-ユニット'] || '-')}</td>
                <td><span class="genre-tag ${genreClass}">${escapeHtml(item.ジャンル || '-')}</span></td>
                <td>${escapeHtml(item.タイムスタンプ || '-')}</td>
                <td>${escapeHtml(item.配信日 || '-')}</td>
                <td>${escapeHtml(channelName)}</td>
                <td><a href="${videoUrl}" target="_blank" class="video-link">視聴</a></td>
            </tr>
        `;
    }).join('');
}

// ===== 統計情報更新 =====
function updateStats() {
    const uniqueVideos = new Set(allData.map(item => item.動画ID)).size;

    document.getElementById('totalSongs').textContent = allData.length.toLocaleString();
    document.getElementById('totalVideos').textContent = uniqueVideos.toLocaleString();
}

function updateFilteredCount() {
    document.getElementById('filteredCount').textContent = filteredData.length.toLocaleString();
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
    // 実際のチャンネルIDマッピングが必要
    // データに含まれていない場合はダミー値を返す
    return Object.keys(channels)[0];
}

function getChannelName(videoId) {
    const channelId = getChannelIdFromVideoId(videoId);
    return channels[channelId]?.name || '不明';
}

function convertTimestampToSeconds(timestamp) {
    if (!timestamp) return 0;

    const parts = timestamp.split(':').map(Number);
    if (parts.length === 2) {
        return parts[0] * 60 + parts[1];
    } else if (parts.length === 3) {
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return 0;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
