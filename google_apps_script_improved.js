// Google Apps Script - 改善版
// 曲名のみで重複判定（アーティスト名は統合時に優先）

function outputAllGenresToSheets() {
  const genres = ['Vocaloid', 'アニメ', 'その他'];
  for (const genre of genres) {
    outputSongsByGenreWithTemplate(genre);
  }
}

function outputSongsByGenreWithTemplate(targetGenre) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName('リスト(一覧)');
  const allData = sourceSheet.getRange('A2:H').getDisplayValues().filter(r => r[1]);

  const filtered = allData.filter(row => row[4] && row[4].includes(targetGenre));

  const grouped = {};
  for (const row of filtered) {
    const title = (row[1] || '').toString().trim();
    const artist = (row[2] || '').toString().trim();
    const timestamp = row[5];
    const date = row[6];
    const videoId = row[7];

    if (!timestamp || !videoId) continue;

    const normalize = str => str.replace(/\s/g, '').replace(/　/g, '').toLowerCase();
    const normTitle = normalize(title);
    const normArtist = normalize(artist);

    // 曲名だけで判定（アーティスト名は統合時に優先順位で選択）
    const key = normTitle;

    if (!grouped[key]) {
      grouped[key] = {
        title,
        artist,
        logs: [],
        hasArtist: !!artist  // アーティスト名があるか
      };
    } else {
      // 既存エントリにアーティスト名がなく、新しいエントリにある場合は更新
      if (!grouped[key].hasArtist && artist) {
        grouped[key].artist = artist;
        grouped[key].hasArtist = true;
      }
      // 両方アーティスト名がある場合、より長い方（詳細な方）を採用
      else if (grouped[key].hasArtist && artist && artist.length > grouped[key].artist.length) {
        grouped[key].artist = artist;
      }
    }

    const seconds = hmsToSeconds(timestamp);
    const tsStr = secondsToHMS(seconds);
    const url = `https://www.youtube.com/watch?v=${videoId}&t=${seconds}s`;
    const linkFormula = `=HYPERLINK("${url}", "${tsStr}")`;

    grouped[key].logs.push([date, linkFormula]);
  }

  let maxLogs = 1;
  const output = [];
  for (const key in grouped) {
    const { title, artist, logs } = grouped[key];
    if (logs.length > maxLogs) maxLogs = logs.length;
    const flatLogs = logs.flat();
    const count = logs.length;
    output.push([count, title, artist, ...flatLogs]);
  }

  const headers = ['回数', '曲名', 'アーティスト'];
  for (let i = 1; i <= maxLogs; i++) {
    headers.push(`配信日${i}`, `TS${i}`);
  }

  const sheetName = `🐙リスト(${targetGenre})`;
  const existing = ss.getSheetByName(sheetName);
  if (existing) ss.deleteSheet(existing);

  const template = ss.getSheetByName('🐙出力(テンプレート)');
  const newSheet = template.copyTo(ss);
  newSheet.setName(sheetName);

  newSheet.clearContents();
  newSheet.appendRow(headers);

  if (output.length > 0) {
    const normalized = output.map(row => {
      while (row.length < headers.length) row.push('');
      return row;
    });
    newSheet.getRange(2, 1, normalized.length, headers.length).setValues(normalized);
  } else {
    newSheet.getRange("A2").setValue("該当データはありませんでした");
  }
}

function hmsToSeconds(hms) {
  if (!hms) return 0;
  const str = hms.toString().trim();
  const parts = str.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 1) return parts[0];
  return 0;
}

function secondsToHMS(seconds) {
  const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
  const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
  const s = String(seconds % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
}
