# ジャンル分類システム - 使い方ガイド

## 📝 概要

キーワードベースのジャンル分類システムを統合JSONで管理するように改善しました。

### 改善点

✅ **統一管理**: 分散していたキーワード定義を1つのJSONファイルに集約
✅ **保守性向上**: キーワード追加・修正が1箇所で完結
✅ **誤分類修正**: Official髭男dism、King Gnu等の誤分類を修正
✅ **拡張性**: 新しいカテゴリやアーティストを簡単に追加可能

---

## 📂 ファイル構成

```
youtube-timestamp-scraper/
├── config/
│   ├── genre_keywords.json      # 統合キーワード設定（★メイン）
│   ├── tag_reference.json       # 旧形式（後方互換性用）
│   └── tag_reference.py         # 旧形式（後方互換性用）
├── src/
│   └── utils/
│       └── genre_classifier.py  # ジャンル分類クラス
└── build_tag_reference.py       # CSV→JSON変換ツール
```

---

## 🚀 使い方

### 1. 基本的な使い方

```python
from src.utils.genre_classifier import GenreClassifier

# 初期化
classifier = GenreClassifier()

# ジャンル判定
genre = classifier.classify("DECO*27", "ヴァンパイア")
print(genre)  # => "Vocaloid"

genre = classifier.classify("米津玄師", "Lemon")
print(genre)  # => "J-POP"

genre = classifier.classify("高橋洋子", "残酷な天使のテーゼ")
print(genre)  # => "アニメ"
```

### 2. アーティストマッピングを学習する

```python
from src.utils.genre_classifier import GenreClassifier

classifier = GenreClassifier()

# 新しいアーティストを学習
classifier.update_artist_mapping("新人アーティスト", "J-POP")

# 保存
classifier.save_config()
```

### 3. CSVからアーティストマッピングを構築

既存のCSVファイル（`song_timestamps_enhanced.csv`）からアーティスト→ジャンルのマッピングを自動構築します。

```bash
python build_tag_reference.py
```

実行すると：
- `config/genre_keywords.json` のアーティストマッピングが自動更新されます
- 統計情報が表示されます

---

## 📊 ジャンル分類のロジック

優先順位：

1. **アーティスト名の完全一致** (`artist_to_genre`)
   - 例: "DECO*27" → "Vocaloid"

2. **キーワードマッチング** (`categories`)
   - アーティスト名や曲名に特定キーワードが含まれるか
   - 例: "feat. 初音ミク" を含む → "Vocaloid"

3. **デフォルト**
   - 上記に該当しない場合 → "その他"

---

## 🔧 genre_keywords.json の構造

```json
{
  "version": "1.0",
  "categories": {
    "Vocaloid": {
      "vocaloid_characters": ["初音ミク", "鏡音リン", ...],
      "producers": ["DECO*27", "ハチ", ...],
      "keywords": ["ボカロ", "vocaloid", ...],
      "songs": ["みくみくにしてあげる", ...]
    },
    "アニメ": {
      "artists": ["高橋洋子", "LiSA", ...],
      "keywords": ["OP", "ED", "アニメ", ...],
      "songs": ["God knows", "残酷な天使のテーゼ", ...]
    },
    "J-POP": {
      "artists": ["YOASOBI", "あいみょん", ...],
      "keywords": ["jpop", "j-pop", ...]
    }
  },
  "artist_to_genre": {
    "DECO*27": "Vocaloid",
    "米津玄師": "J-POP",
    "Official髭男dism": "J-POP",
    "King Gnu": "J-POP",
    ...
  }
}
```

---

## ✏️ カスタマイズ方法

### キーワードを追加

`config/genre_keywords.json` を直接編集：

```json
{
  "categories": {
    "Vocaloid": {
      "producers": [
        "DECO*27",
        "新しいボカロP"  // ← 追加
      ]
    }
  }
}
```

### アーティストマッピングを追加

方法1: JSONを直接編集

```json
{
  "artist_to_genre": {
    "新人アーティスト": "J-POP"  // ← 追加
  }
}
```

方法2: Pythonで追加

```python
classifier = GenreClassifier()
classifier.update_artist_mapping("新人アーティスト", "J-POP")
classifier.save_config()
```

---

## 📈 統計情報の確認

```python
from src.utils.genre_classifier import GenreClassifier

classifier = GenreClassifier()
stats = classifier.get_stats()

print(f"バージョン: {stats['version']}")
print(f"登録アーティスト数: {stats['artist_mappings']}")

for category, keyword_count in stats['categories'].items():
    print(f"{category}: {keyword_count}キーワード")
```

出力例:
```
バージョン: 1.0
登録アーティスト数: 43
Vocaloid: 65キーワード
アニメ: 43キーワード
J-POP: 16キーワード
その他: 0キーワード
```

---

## 🔍 トラブルシューティング

### Q1. 誤分類されている

**A.** `config/genre_keywords.json` の `artist_to_genre` を修正してください。

```json
{
  "artist_to_genre": {
    "Official髭男dism": "J-POP"  // Vocaloid → J-POP に修正
  }
}
```

### Q2. 新しいアーティストが「その他」になる

**A.** 以下のいずれかを実行：
1. `artist_to_genre` に追加
2. アーティスト名に含まれるキーワードを `categories` に追加

### Q3. キーワードが効いていない

**A.** キーワードマッチングは**小文字変換後**に行われます。
   - OK: "ボカロ" → "ぼかろ"
   - OK: "Vocaloid" → "vocaloid"

---

## 🎯 まとめ

- **メイン設定**: `config/genre_keywords.json`
- **分類クラス**: `src/utils/genre_classifier.py`
- **自動学習**: `build_tag_reference.py`

キーワードやアーティストマッピングは全て `genre_keywords.json` で一元管理されています。
