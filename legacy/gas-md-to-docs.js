/**
 * MDファイルをGoogleドキュメントに変換するGAS
 *
 * 使い方:
 * 1. Google Driveにmdファイルをアップロード
 * 2. 新しいGoogleドキュメントを作成
 * 3. 「拡張機能」→「Apps Script」でエディタを開く
 * 4. このスクリプトを貼り付け
 * 5. convertMarkdownToGoogleDocs() を実行
 * 6. mdファイルのファイルIDを入力
 */

/**
 * マークダウンファイルをGoogleドキュメントに変換
 */
function convertMarkdownToGoogleDocs() {
  const ui = DocumentApp.getUi();
  const response = ui.prompt(
    'マークダウンファイルのID',
    'Google DriveにアップロードしたmdファイルのファイルIDを入力してください:',
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  const fileId = response.getResponseText();

  try {
    const file = DriveApp.getFileById(fileId);
    const content = file.getBlob().getDataAsString();
    const fileName = file.getName();

    // 新しいドキュメントを作成
    const doc = DocumentApp.create(fileName.replace('.md', ''));
    const body = doc.getBody();

    // 既存のコンテンツをクリア
    body.clear();

    // マークダウンをパース
    parseMarkdownToDoc(body, content);

    ui.alert(
      '変換完了！',
      '新しいドキュメントが作成されました:\n' + doc.getUrl(),
      ui.ButtonSet.OK
    );

  } catch (e) {
    ui.alert('エラー: ' + e.message);
  }
}

/**
 * 複数のマークダウンファイルを一度に変換
 */
function convertMultipleMarkdownFiles() {
  const ui = DocumentApp.getUi();

  // フォルダIDを取得
  const response = ui.prompt(
    'フォルダID',
    'mdファイルが入っているGoogle DriveフォルダのIDを入力してください:',
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  const folderId = response.getResponseText();

  try {
    const folder = DriveApp.getFolderById(folderId);
    const files = folder.getFilesByType(MimeType.PLAIN_TEXT);

    const createdDocs = [];

    while (files.hasNext()) {
      const file = files.next();
      const fileName = file.getName();

      // .mdファイルのみ処理
      if (!fileName.endsWith('.md')) continue;

      const content = file.getBlob().getDataAsString();

      // 新しいドキュメントを作成
      const doc = DocumentApp.create(fileName.replace('.md', ''));
      const body = doc.getBody();
      body.clear();

      // マークダウンをパース
      parseMarkdownToDoc(body, content);

      // 作成したドキュメントを同じフォルダに移動
      const docFile = DriveApp.getFileById(doc.getId());
      folder.addFile(docFile);
      DriveApp.getRootFolder().removeFile(docFile);

      createdDocs.push(fileName + ' → ' + doc.getUrl());
    }

    ui.alert(
      '変換完了！',
      createdDocs.length + '個のドキュメントを作成しました:\n\n' + createdDocs.join('\n'),
      ui.ButtonSet.OK
    );

  } catch (e) {
    ui.alert('エラー: ' + e.message);
  }
}

/**
 * マークダウンをGoogleドキュメント形式にパース
 */
function parseMarkdownToDoc(body, markdown) {
  const lines = markdown.split('\n');
  let inCodeBlock = false;
  let codeBlockContent = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // コードブロックの開始/終了
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        // コードブロック終了 - 内容を追加
        const codeText = codeBlockContent.join('\n');
        const para = body.appendParagraph(codeText);
        para.setFontFamily('Courier New');
        para.setFontSize(9);
        para.setBackgroundColor('#f8f9fa');
        para.setSpacingBefore(6);
        para.setSpacingAfter(6);
        codeBlockContent = [];
        inCodeBlock = false;
      } else {
        // コードブロック開始
        inCodeBlock = true;
      }
      continue;
    }

    // コードブロック内
    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    // 空行
    if (line.trim() === '') {
      body.appendParagraph('');
      continue;
    }

    // 見出し1 (# )
    if (line.startsWith('# ')) {
      const text = line.substring(2);
      const heading = body.appendParagraph(text);
      heading.setHeading(DocumentApp.ParagraphHeading.HEADING1);
      heading.setForegroundColor('#1a73e8');
      continue;
    }

    // 見出し2 (## )
    if (line.startsWith('## ')) {
      const text = line.substring(3);
      const heading = body.appendParagraph(text);
      heading.setHeading(DocumentApp.ParagraphHeading.HEADING2);
      continue;
    }

    // 見出し3 (### )
    if (line.startsWith('### ')) {
      const text = line.substring(4);
      const heading = body.appendParagraph(text);
      heading.setHeading(DocumentApp.ParagraphHeading.HEADING3);
      continue;
    }

    // 見出し4 (#### )
    if (line.startsWith('#### ')) {
      const text = line.substring(5);
      const heading = body.appendParagraph(text);
      heading.setHeading(DocumentApp.ParagraphHeading.HEADING4);
      continue;
    }

    // 見出し5 (##### )
    if (line.startsWith('##### ')) {
      const text = line.substring(6);
      const heading = body.appendParagraph(text);
      heading.setHeading(DocumentApp.ParagraphHeading.HEADING5);
      continue;
    }

    // リスト項目 (- または * )
    if (line.match(/^[\-\*]\s/)) {
      const text = line.substring(2);
      const item = body.appendListItem(text);
      item.setGlyphType(DocumentApp.GlyphType.BULLET);
      continue;
    }

    // 番号付きリスト
    if (line.match(/^\d+\.\s/)) {
      const text = line.replace(/^\d+\.\s/, '');
      const item = body.appendListItem(text);
      item.setGlyphType(DocumentApp.GlyphType.NUMBER);
      continue;
    }

    // 引用 (> )
    if (line.startsWith('> ')) {
      const text = line.substring(2);
      const para = body.appendParagraph(text);
      para.setIndentStart(36);
      para.setBackgroundColor('#f1f3f4');
      para.setBorderLeft(true);
      para.setBorderColor('#e8eaed');
      continue;
    }

    // 水平線 (--- または ***)
    if (line.trim() === '---' || line.trim() === '***') {
      body.appendHorizontalRule();
      continue;
    }

    // 通常のテキスト
    const para = body.appendParagraph(line);

    // インラインフォーマットを適用
    applyInlineFormatting(para, line);
  }
}

/**
 * インラインのマークダウン記法を適用
 */
function applyInlineFormatting(paragraph, text) {
  const textElement = paragraph.editAsText();

  // 太字 (**text** または __text__)
  let boldRegex = /\*\*([^\*]+)\*\*/g;
  let match;
  while ((match = boldRegex.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    textElement.setBold(start, end - 1, true);
  }

  // イタリック (*text* または _text_)
  let italicRegex = /(?<!\*)\*([^\*]+)\*(?!\*)/g;
  while ((match = italicRegex.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    textElement.setItalic(start, end - 1, true);
  }

  // インラインコード (`code`)
  let codeRegex = /`([^`]+)`/g;
  while ((match = codeRegex.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    textElement.setFontFamily(start, end - 1, 'Courier New');
    textElement.setBackgroundColor(start, end - 1, '#f8f9fa');
  }

  // リンク ([text](url))
  let linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  while ((match = linkRegex.exec(text)) !== null) {
    const linkText = match[1];
    const url = match[2];
    const start = match.index;
    const end = start + match[0].length;

    // リンクテキストを設定
    textElement.deleteText(start, end - 1);
    textElement.insertText(start, linkText);
    textElement.setLinkUrl(start, start + linkText.length - 1, url);
    textElement.setForegroundColor(start, start + linkText.length - 1, '#1a73e8');
    textElement.setUnderline(start, start + linkText.length - 1, true);
  }
}

/**
 * 現在のドキュメントにマークダウンテキストを挿入
 * （手動でコピペした場合に使用）
 */
function formatCurrentDocAsMarkdown() {
  const doc = DocumentApp.getActiveDocument();
  const body = doc.getBody();
  const text = body.getText();

  // 現在のコンテンツをクリア
  body.clear();

  // マークダウンとしてパース
  parseMarkdownToDoc(body, text);

  DocumentApp.getUi().alert('フォーマット完了！');
}
