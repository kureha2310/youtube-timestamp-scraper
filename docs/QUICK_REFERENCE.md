# クイックリファレンス - 開発者用

## 🎯 システムの核心（最重要）

### 主目的
**YouTubeのタイムスタンプを正確に取得してCSVにする**

### 品質の指標
1. **アーティスト名の抽出率** - 80%以上が理想
2. **確度スコア** - 0.8以上が信頼できる歌配信
3. **ジャンル分類の精度**

---

## 📂 最重要ファイル

```
src/extractors/youtube_song_scraper.py  ← メインロジック
output/csv/song_timestamps_complete.csv ← 最終成果物
config/genre_keywords.json              ← ジャンル分類設定
```

---

## 🔧 よく修正する箇所

### 1. タイムスタンプ抽出パターン
📍 `src/utils/infoclass.py` - `TimeStamp.from_videoinfo()`

```python
# 対応すべきパターン
"01:23 曲名 / アーティスト"    ← 理想形
"01:23 - 曲名 / アーティスト"
"01:23）曲名 / アーティスト"
"01:23：曲名 / アーティスト"
```

### 2. ジャンル分類
📍 `config/genre_keywords.json`

```json
{
  "artist_to_genre": {
    "新しいアーティスト": "J-POP"  ← ここに追加
  }
}
```

### 3. 確度スコア調整
📍 `src/extractors/youtube_song_scraper.py` - `calculate_confidence_score()`

```python
# 重みを調整する場合
if re.search(r'[歌うたウタ]', title):
    singing_score += 5  ← この数値を調整
```

---

## 📊 デバッグ方法

### 確度スコアの分布を確認
```python
import pandas as pd
df = pd.read_csv('output/csv/song_timestamps_complete.csv', encoding='utf-8-sig')
print(df['確度スコア'].value_counts().sort_index())
print(f"平均: {df['確度スコア'].mean():.2f}")
```

### アーティスト名の抽出率を確認
```python
df = pd.read_csv('output/csv/song_timestamps_complete.csv', encoding='utf-8-sig')
has_artist = df['歌手-ユニット'].notna() & (df['歌手-ユニット'] != '')
print(f"アーティスト名抽出率: {has_artist.sum() / len(df) * 100:.1f}%")
```

### ジャンル分布を確認
```python
df = pd.read_csv('output/csv/song_timestamps_complete.csv', encoding='utf-8-sig')
print(df['ジャンル'].value_counts())
```

---

## ⚠️ よくある間違い

### ❌ やってはいけないこと
1. タイムスタンプ抽出以外を優先する（主目的を忘れない）
2. 確度スコアの計算ロジックを複雑にしすぎる
3. ジャンル分類に時間をかけすぎる（副目的）

### ✅ やるべきこと
1. まずタイムスタンプの抽出精度を上げる
2. アーティスト名の抽出率を確認する
3. 統計を見て改善効果を測定する

---

## 🚀 開発フロー

### 1. 変更前にテストデータで確認
```bash
# 既存データをバックアップ
cp output/csv/song_timestamps_complete.csv output/csv/backup_$(date +%Y%m%d).csv

# 小規模テスト（1チャンネルのみ）
# user_ids.jsonで1チャンネルだけenabledにする
```

### 2. 変更後の品質確認
```bash
# 統計を確認
python -c "
import pandas as pd
df = pd.read_csv('output/csv/song_timestamps_complete.csv', encoding='utf-8-sig')
print(f'総曲数: {len(df)}')
print(f'アーティスト抽出率: {(df[\"歌手-ユニット\"]!=\"\").sum()/len(df)*100:.1f}%')
print(f'平均確度: {df[\"確度スコア\"].mean():.2f}')
print(df['ジャンル'].value_counts())
"
```

### 3. before/afterを比較
```python
# 改善前後でアーティスト抽出率を比較
df_before = pd.read_csv('output/csv/backup_20251103.csv', encoding='utf-8-sig')
df_after = pd.read_csv('output/csv/song_timestamps_complete.csv', encoding='utf-8-sig')

print(f"Before: {(df_before['歌手-ユニット']!='').sum() / len(df_before) * 100:.1f}%")
print(f"After:  {(df_after['歌手-ユニット']!='').sum() / len(df_after) * 100:.1f}%")
```

---

## 📋 コーディング時のチェックリスト

### 新機能追加時
- [ ] タイムスタンプ抽出の精度は下がっていないか？
- [ ] アーティスト名の抽出率は向上したか？
- [ ] 確度スコアの分布は改善したか？
- [ ] 既存のテストデータで動作確認したか？

### バグ修正時
- [ ] 他の部分に影響を与えていないか？
- [ ] before/afterで統計を比較したか？
- [ ] エッジケースをテストしたか？

---

## 🎨 改善の優先順位

### 今すぐやるべきこと
1. タイムスタンプ抽出パターンの追加
2. アーティスト名の分離ロジックの改善
3. 無効なエントリの除外ロジックの改善

### 後でやること
4. ジャンル分類の精度向上
5. 確度スコアの細かい調整
6. UI/UXの改善

### 慎重に検討すること
- 機械学習の導入（オーバーエンジニアリングに注意）
- 複雑な自然言語処理（シンプルさを保つ）

---

## 💡 困ったときは

### アーティスト名が取れない
→ `src/extractors/youtube_song_scraper.py` - `parse_song_title_artist()` を確認
→ 「/」以外の区切り文字に対応する必要があるかも

### 確度スコアが低すぎる/高すぎる
→ `calculate_confidence_score()` の重みを調整
→ 統計を見て適切な閾値を決める

### ジャンルが正しく分類されない
→ `config/genre_keywords.json` にアーティスト/キーワードを追加
→ `artist_to_genre` の完全一致を優先的に使う

---

**このファイルを見れば、今何をすべきか迷わない！**
