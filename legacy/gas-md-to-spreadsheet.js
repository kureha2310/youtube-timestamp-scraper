/**
 * 🏭 YouTube歌配信タイムスタンプ工場 - ドキュメント管理システム
 *
 * このスクリプトは、工場見学ガイドなどのREADMEファイルを
 * Googleスプレッドシートに変換して見やすく表示します。
 *
 * 使い方:
 * 1. 新しいGoogleスプレッドシートを作成
 * 2. 「拡張機能」→「Apps Script」でエディタを開く
 * 3. このスクリプトを貼り付け
 * 4. createSheetsFromMarkdown() を実行
 * 5. 各README_○○.mdファイルの内容をコピペして貼り付け
 *
 * 💡 おすすめ: まずは「初心者向け解説（工場見学ガイド）」から！
 */

function createSheetsFromMarkdown() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // 目次シートを先に作成（存在しない場合）
  let tocSheet = ss.getSheetByName('目次');
  if (!tocSheet) {
    tocSheet = ss.insertSheet('目次', 0);
  } else {
    tocSheet.clear();
  }

  // 既存のシートを削除（目次以外）
  const sheets = ss.getSheets();
  for (const sheet of sheets) {
    if (sheet.getName() !== '目次') {
      ss.deleteSheet(sheet);
    }
  }

  // mdファイルの定義
  const mdFiles = [
    { name: 'システム解説', title: 'システム解説（技術者向け）' },
    { name: '初心者向け解説', title: '初心者向け解説（工場見学ガイド）' },
    { name: '仕組み解説', title: '仕組み解説' }
  ];

  // 目次を作成
  tocSheet.getRange('A1').setValue('🏭 YouTube歌配信タイムスタンプ工場');
  tocSheet.getRange('A1').setFontSize(18).setFontWeight('bold').setFontColor('#1a73e8');

  tocSheet.getRange('A2').setValue('YouTubeの動画を原材料に、整理された曲リストを製造する工場システム');
  tocSheet.getRange('A2').setFontSize(11).setFontColor('#5f6368');

  let row = 4;

  // 使い方ガイドセクション
  tocSheet.getRange(row, 1).setValue('📘 このドキュメントの使い方');
  tocSheet.getRange(row, 1).setFontSize(14).setFontWeight('bold');
  tocSheet.getRange(row, 1).setBackground('#e8f0fe');
  row++;

  const howToUse = [
    '',
    '【まず何から読む？】',
    '→ まずは「初心者向け解説」（工場見学ガイド）がおすすめ！',
    '→ システムがどう動いてるか知りたいだけなら、工場を見学する感覚で読めます',
    '',
    '【各ドキュメントの対象読者】',
    '・システム解説 → 開発者・技術者向け（Python、GASのコードを理解したい人）',
    '・初心者向け解説 → まじ無知な人向け（工場見学のノリでシステムの動きを理解）',
    '・仕組み解説 → プログラミング未経験者（でも仕組みには興味がある人）',
    '',
    '【初心者向け解説の特徴】',
    '・6つのセクションで工場を見学',
    '・作業員の様子を見ながらデータの流れを追跡',
    '・YouTube動画115本 → 210個のタイムスタンプ に加工される過程が分かる',
    '',
    '【全部読む必要ある？】',
    '→ NO！自分に合ったもの1つだけでOK',
    '→ 「システムがどう動くか」だけ知りたい → 初心者向け解説',
    '→ 「コードを理解したい」 → システム解説',
    '',
    '【注意】',
    '※このドキュメントはスプレッドシート版です',
    '※図やコードのインデントが崩れている場合は、元のmdファイルを参照してください',
    ''
  ];

  for (const text of howToUse) {
    const cell = tocSheet.getRange(row, 1);
    cell.setValue(text);
    cell.setFontSize(10);

    if (text.startsWith('【')) {
      cell.setFontWeight('bold');
      cell.setFontSize(11);
    } else if (text.startsWith('→')) {
      cell.setFontColor('#1a73e8');
    } else if (text.startsWith('※')) {
      cell.setFontColor('#d93025');
    }
    row++;
  }

  // ドキュメント一覧
  row += 1;
  tocSheet.getRange(row, 1).setValue('📖 ドキュメント一覧');
  tocSheet.getRange(row, 1).setFontSize(14).setFontWeight('bold');
  tocSheet.getRange(row, 1).setBackground('#e8f0fe');
  row++;
  row++;

  for (const file of mdFiles) {
    const formula = `=HYPERLINK("#gid=${getOrCreateSheet(ss, file.name).getSheetId()}", "→ ${file.title}")`;
    tocSheet.getRange(row, 1).setFormula(formula);
    tocSheet.getRange(row, 1).setFontSize(12);
    tocSheet.getRange(row, 1).setFontColor('#1a73e8');
    row++;
  }

  // 概要セクション
  row += 1;
  tocSheet.getRange(row, 1).setValue('📝 システム概要');
  tocSheet.getRange(row, 1).setFontSize(14).setFontWeight('bold');
  tocSheet.getRange(row, 1).setBackground('#e8f0fe');
  row++;

  const descriptions = [
    '',
    'このシステムは「タイムスタンプ工場」です。',
    'YouTubeの動画（原材料）が入ってきて、整理されたリスト（完成品）が出ていきます。',
    '',
    '【工場の6つのセクション】',
    '1️⃣ 採掘場 → YouTubeから動画とコメントを掘り出す',
    '2️⃣ 選別所 → 歌配信だけを選ぶ（115本→74本）',
    '3️⃣ 洗浄所 → コメントからゴミを除去',
    '4️⃣ 統合所 → 重複を削除（369個→210個）',
    '5️⃣ CSV工場 → 表の形に整形',
    '6️⃣ 仕分け所 → ジャンル別に分類（Vocaloid、アニメ、その他）',
    '',
    '【最終製品】',
    '✓ ジャンル別に整理された曲リスト',
    '✓ クリックすると動画が開くリンク付き',
    '✓ 推しが何回同じ曲歌ってるか一目瞭然',
    '',
    '詳しい工場見学は、上記のドキュメント一覧から「初心者向け解説」をご覧ください。'
  ];

  for (const desc of descriptions) {
    const cell = tocSheet.getRange(row, 1);
    cell.setValue(desc);
    cell.setFontSize(10);

    if (desc.startsWith('【')) {
      cell.setFontWeight('bold');
      cell.setFontSize(11);
    } else if (desc.startsWith('✓')) {
      cell.setFontColor('#188038');
    } else if (desc.match(/^[1-6]️⃣/)) {
      cell.setFontColor('#1967d2');
    }
    row++;
  }

  // 列幅を調整
  tocSheet.setColumnWidth(1, 600);

  SpreadsheetApp.getUi().alert(
    '🏭 工場の準備完了！\n\n' +
    '次のステップ:\n' +
    '1. 各シート（システム解説、初心者向け解説など）に移動\n' +
    '2. 対応するREADMEファイル（.md）の内容を全選択してコピー\n' +
    '3. A1セルから貼り付け\n' +
    '4. 全部貼り付けたら formatAllSheets() を実行してフォーマットを適用\n\n' +
    '💡 おすすめ: まずは「初心者向け解説」から工場見学をどうぞ！'
  );
}

function getOrCreateSheet(ss, name) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}

/**
 * 全シートにフォーマットを適用
 */
function formatAllSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();

  for (const sheet of sheets) {
    if (sheet.getName() === '目次') continue;

    formatMarkdownSheet(sheet);
  }

  SpreadsheetApp.getUi().alert('✨ フォーマット完了！工場見学の準備が整いました。');
}

/**
 * マークダウンをスプレッドシート形式にフォーマット
 */
function formatMarkdownSheet(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow === 0) return;

  const data = sheet.getRange(1, 1, lastRow, 1).getValues();

  for (let i = 0; i < data.length; i++) {
    const cell = sheet.getRange(i + 1, 1);
    const text = data[i][0].toString();

    // 空行はスキップ
    if (!text.trim()) continue;

    // 見出し1 (# )
    if (text.startsWith('# ')) {
      cell.setValue(text.substring(2));
      cell.setFontSize(18);
      cell.setFontWeight('bold');
      cell.setBackground('#4285f4');
      cell.setFontColor('#ffffff');
    }
    // 見出し2 (## )
    else if (text.startsWith('## ')) {
      cell.setValue(text.substring(3));
      cell.setFontSize(14);
      cell.setFontWeight('bold');
      cell.setBackground('#e8f0fe');
    }
    // 見出し3 (### )
    else if (text.startsWith('### ')) {
      cell.setValue(text.substring(4));
      cell.setFontSize(12);
      cell.setFontWeight('bold');
      cell.setBackground('#f1f3f4');
    }
    // 見出し4 (#### )
    else if (text.startsWith('#### ')) {
      cell.setValue(text.substring(5));
      cell.setFontSize(11);
      cell.setFontWeight('bold');
    }
    // コードブロック (```)
    else if (text.startsWith('```')) {
      cell.setBackground('#f8f9fa');
      cell.setFontFamily('Courier New');
      cell.setFontSize(9);
    }
    // リスト項目 (- または * )
    else if (text.match(/^[\-\*]\s/)) {
      cell.setValue('  ' + text);
      cell.setFontSize(10);
    }
    // 番号付きリスト
    else if (text.match(/^\d+\.\s/)) {
      cell.setFontSize(10);
    }
    // 通常のテキスト
    else {
      cell.setFontSize(10);
    }

    // リンクをハイパーリンクに変換 ([テキスト](URL))
    const linkMatch = text.match(/\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch) {
      const linkText = linkMatch[1];
      const url = linkMatch[2];
      if (url.startsWith('http')) {
        const formula = `=HYPERLINK("${url}", "${linkText}")`;
        cell.setFormula(formula);
      }
    }
  }

  // 列幅を調整（工場見学ガイドは図が多いので広めに）
  sheet.setColumnWidth(1, 1000);
  sheet.setRowHeights(1, lastRow, 25);
}

/**
 * より高度なマークダウンパーサー（オプション）
 * mdファイルを直接読み込んで変換する場合に使用
 */
function importMarkdownFromDrive() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.prompt(
    'Google DriveのファイルIDを入力',
    'Google DriveにアップロードしたmdファイルのファイルIDを入力してください:',
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() === ui.Button.OK) {
    const fileId = response.getResponseText();
    try {
      const file = DriveApp.getFileById(fileId);
      const content = file.getBlob().getDataAsString();

      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const sheet = ss.getActiveSheet();

      // 行ごとに分割
      const lines = content.split('\n');

      // A列に各行を配置
      for (let i = 0; i < lines.length; i++) {
        sheet.getRange(i + 1, 1).setValue(lines[i]);
      }

      formatMarkdownSheet(sheet);

      ui.alert('インポート完了！');
    } catch (e) {
      ui.alert('エラー: ' + e.message);
    }
  }
}

/**
 * 複数のmdファイルを一括インポート（ファイルID指定）
 * これを実行すれば自動で全部のシートに内容が読み込まれます！
 */
function importMultipleMarkdownFiles() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // ファイルIDとシート名のマッピング
  const files = [
    {
      id: '1rlGc5bCKXygWjA8-rstWF4Nwu-iBPSGd',
      sheetName: 'システム解説'
    },
    {
      id: '1aY4IJWS_B9_4FVet8vlJUV5f3uRGOzBt',
      sheetName: '仕組み解説'
    },
    {
      id: '1miPEYKgYLbxBm0cmB3U3ESIwH1WJEakI',
      sheetName: '初心者向け解説'
    }
  ];

  const results = [];

  for (const fileInfo of files) {
    try {
      // ファイルを読み込み
      const file = DriveApp.getFileById(fileInfo.id);
      const content = file.getBlob().getDataAsString();

      // シートを取得または作成
      let sheet = ss.getSheetByName(fileInfo.sheetName);
      if (!sheet) {
        sheet = ss.insertSheet(fileInfo.sheetName);
      } else {
        sheet.clear();
      }

      // 行ごとに分割
      const lines = content.split('\n');

      // A列に各行を配置
      const values = lines.map(line => [line]);
      if (values.length > 0) {
        sheet.getRange(1, 1, values.length, 1).setValues(values);
      }

      // フォーマットを適用
      formatMarkdownSheet(sheet);

      results.push(`✓ ${fileInfo.sheetName}: ${lines.length}行をインポート`);

    } catch (e) {
      results.push(`✗ ${fileInfo.sheetName}: エラー - ${e.message}`);
    }
  }

  SpreadsheetApp.getUi().alert(
    '📦 製品のインポート完了！\n\n' + results.join('\n') + '\n\n' +
    '工場見学の準備が整いました！目次シートからどうぞ。'
  );
}

/**
 * ワンクリックで全て実行（超簡単版）
 * これ1つ実行すれば、シート作成→インポート→フォーマットが全部完了！
 */
function createAndImportAll() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();

  // ステップ1: 目次シートを作成
  let tocSheet = ss.getSheetByName('目次');
  if (!tocSheet) {
    tocSheet = ss.insertSheet('目次', 0);
  } else {
    tocSheet.clear();
  }

  // 既存のシートを削除（目次以外）
  const sheets = ss.getSheets();
  for (const sheet of sheets) {
    if (sheet.getName() !== '目次') {
      ss.deleteSheet(sheet);
    }
  }

  // ステップ2: 目次を作成
  createTableOfContents(tocSheet);

  // ステップ3: Google Driveからファイルをインポート
  const files = [
    {
      id: '1rlGc5bCKXygWjA8-rstWF4Nwu-iBPSGd',
      sheetName: 'システム解説'
    },
    {
      id: '1aY4IJWS_B9_4FVet8vlJUV5f3uRGOzBt',
      sheetName: '仕組み解説'
    },
    {
      id: '1miPEYKgYLbxBm0cmB3U3ESIwH1WJEakI',
      sheetName: '初心者向け解説'
    }
  ];

  const results = [];

  for (const fileInfo of files) {
    try {
      // ファイルを読み込み
      const file = DriveApp.getFileById(fileInfo.id);
      const content = file.getBlob().getDataAsString();

      // シートを取得または作成
      let sheet = ss.getSheetByName(fileInfo.sheetName);
      if (!sheet) {
        sheet = ss.insertSheet(fileInfo.sheetName);
      } else {
        sheet.clear();
      }

      // 行ごとに分割
      const lines = content.split('\n');

      // A列に各行を配置
      const values = lines.map(line => [line]);
      if (values.length > 0) {
        sheet.getRange(1, 1, values.length, 1).setValues(values);
      }

      // フォーマットを適用
      formatMarkdownSheet(sheet);

      results.push(`✓ ${fileInfo.sheetName}: ${lines.length}行をインポート`);

    } catch (e) {
      results.push(`✗ ${fileInfo.sheetName}: エラー - ${e.message}`);
    }
  }

  // 完了メッセージ
  ui.alert(
    '🏭 工場が稼働開始しました！\n\n' +
    results.join('\n') + '\n\n' +
    '目次シートから工場見学をスタートできます。\n' +
    'まずは「初心者向け解説（工場見学ガイド）」がおすすめです！'
  );
}

/**
 * 目次シートを作成（createAndImportAllから分離）
 */
function createTableOfContents(tocSheet) {
  // 目次を作成
  tocSheet.getRange('A1').setValue('🏭 YouTube歌配信タイムスタンプ工場');
  tocSheet.getRange('A1').setFontSize(18).setFontWeight('bold').setFontColor('#1a73e8');

  tocSheet.getRange('A2').setValue('YouTubeの動画を原材料に、整理された曲リストを製造する工場システム');
  tocSheet.getRange('A2').setFontSize(11).setFontColor('#5f6368');

  let row = 4;

  // 使い方ガイドセクション
  tocSheet.getRange(row, 1).setValue('📘 このドキュメントの使い方');
  tocSheet.getRange(row, 1).setFontSize(14).setFontWeight('bold');
  tocSheet.getRange(row, 1).setBackground('#e8f0fe');
  row++;

  const howToUse = [
    '',
    '【まず何から読む？】',
    '→ まずは「初心者向け解説」（工場見学ガイド）がおすすめ！',
    '→ システムがどう動いてるか知りたいだけなら、工場を見学する感覚で読めます',
    '',
    '【各ドキュメントの対象読者】',
    '・システム解説 → 開発者・技術者向け（Python、GASのコードを理解したい人）',
    '・初心者向け解説 → まじ無知な人向け（工場見学のノリでシステムの動きを理解）',
    '・仕組み解説 → プログラミング未経験者（でも仕組みには興味がある人）',
    '',
    '【初心者向け解説の特徴】',
    '・6つのセクションで工場を見学',
    '・作業員の様子を見ながらデータの流れを追跡',
    '・YouTube動画115本 → 210個のタイムスタンプ に加工される過程が分かる',
    '',
    '【全部読む必要ある？】',
    '→ NO！自分に合ったもの1つだけでOK',
    '→ 「システムがどう動くか」だけ知りたい → 初心者向け解説',
    '→ 「コードを理解したい」 → システム解説',
    '',
    '【注意】',
    '※このドキュメントはスプレッドシート版です',
    '※図やコードのインデントが崩れている場合は、元のmdファイルを参照してください',
    ''
  ];

  for (const text of howToUse) {
    const cell = tocSheet.getRange(row, 1);
    cell.setValue(text);
    cell.setFontSize(10);

    if (text.startsWith('【')) {
      cell.setFontWeight('bold');
      cell.setFontSize(11);
    } else if (text.startsWith('→')) {
      cell.setFontColor('#1a73e8');
    } else if (text.startsWith('※')) {
      cell.setFontColor('#d93025');
    }
    row++;
  }

  // ドキュメント一覧
  row += 1;
  tocSheet.getRange(row, 1).setValue('📖 ドキュメント一覧');
  tocSheet.getRange(row, 1).setFontSize(14).setFontWeight('bold');
  tocSheet.getRange(row, 1).setBackground('#e8f0fe');
  row++;
  row++;

  const mdFiles = [
    { name: 'システム解説', title: 'システム解説（技術者向け）' },
    { name: '初心者向け解説', title: '初心者向け解説（工場見学ガイド）' },
    { name: '仕組み解説', title: '仕組み解説' }
  ];

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  for (const file of mdFiles) {
    const sheet = ss.getSheetByName(file.name);
    if (sheet) {
      const formula = `=HYPERLINK("#gid=${sheet.getSheetId()}", "→ ${file.title}")`;
      tocSheet.getRange(row, 1).setFormula(formula);
      tocSheet.getRange(row, 1).setFontSize(12);
      tocSheet.getRange(row, 1).setFontColor('#1a73e8');
    } else {
      tocSheet.getRange(row, 1).setValue(`→ ${file.title} (準備中...)`);
      tocSheet.getRange(row, 1).setFontSize(12);
      tocSheet.getRange(row, 1).setFontColor('#5f6368');
    }
    row++;
  }

  // 概要セクション
  row += 1;
  tocSheet.getRange(row, 1).setValue('📝 システム概要');
  tocSheet.getRange(row, 1).setFontSize(14).setFontWeight('bold');
  tocSheet.getRange(row, 1).setBackground('#e8f0fe');
  row++;

  const descriptions = [
    '',
    'このシステムは「タイムスタンプ工場」です。',
    'YouTubeの動画（原材料）が入ってきて、整理されたリスト（完成品）が出ていきます。',
    '',
    '【工場の6つのセクション】',
    '1️⃣ 採掘場 → YouTubeから動画とコメントを掘り出す',
    '2️⃣ 選別所 → 歌配信だけを選ぶ（115本→74本）',
    '3️⃣ 洗浄所 → コメントからゴミを除去',
    '4️⃣ 統合所 → 重複を削除（369個→210個）',
    '5️⃣ CSV工場 → 表の形に整形',
    '6️⃣ 仕分け所 → ジャンル別に分類（Vocaloid、アニメ、その他）',
    '',
    '【最終製品】',
    '✓ ジャンル別に整理された曲リスト',
    '✓ クリックすると動画が開くリンク付き',
    '✓ 推しが何回同じ曲歌ってるか一目瞭然',
    '',
    '詳しい工場見学は、上記のドキュメント一覧から「初心者向け解説」をご覧ください。'
  ];

  for (const desc of descriptions) {
    const cell = tocSheet.getRange(row, 1);
    cell.setValue(desc);
    cell.setFontSize(10);

    if (desc.startsWith('【')) {
      cell.setFontWeight('bold');
      cell.setFontSize(11);
    } else if (desc.startsWith('✓')) {
      cell.setFontColor('#188038');
    } else if (desc.match(/^[1-6]️⃣/)) {
      cell.setFontColor('#1967d2');
    }
    row++;
  }

  // 列幅を調整
  tocSheet.setColumnWidth(1, 600);
}
