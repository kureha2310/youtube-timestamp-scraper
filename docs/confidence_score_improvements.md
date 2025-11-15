# 確度スコア改善案

## 現在の問題
- 正規化の分母が固定（15.0）で、実際のスコアが想定を超える
- タイムスタンプの質（形式、数、密度）を評価していない
- 動画の長さや抽出されたタイムスタンプの詳細を考慮していない

## 改善案

### 1. タイムスタンプの質を評価（最優先）
```python
# 実際に抽出されたタイムスタンプを評価
extracted_timestamps = TimeStamp.from_videoinfo(video_info)
timestamp_quality_score = 0

# アーティスト名がある割合（最も信頼できる指標）
artist_ratio = sum(1 for ts in extracted_timestamps if '/' in ts.text) / max(1, len(extracted_timestamps))
if artist_ratio > 0.8:
    timestamp_quality_score += 5  # 80%以上にアーティスト名
elif artist_ratio > 0.5:
    timestamp_quality_score += 3
elif artist_ratio > 0.2:
    timestamp_quality_score += 1

# タイムスタンプの数
if len(extracted_timestamps) >= 20:
    timestamp_quality_score += 3
elif len(extracted_timestamps) >= 10:
    timestamp_quality_score += 2
elif len(extracted_timestamps) >= 5:
    timestamp_quality_score += 1

# タイムスタンプの密度（規則的に並んでいるか）
# 3-6分間隔なら歌枠の可能性が高い
```

### 2. 動的な正規化
```python
# 実際に獲得したスコアの最大値を記録
max_possible_score = singing_score + timestamp_quality_score
normalized_score = raw_score / max(max_possible_score, 1)
```

### 3. 動画メタデータを活用
```python
# 動画の長さ（30分以上の配信は歌枠の可能性が高い）
if video_duration > 1800:  # 30分
    singing_score += 2

# 視聴回数とコメント数の比率
if comment_count / max(view_count, 1) > 0.01:  # エンゲージメントが高い
    singing_score += 1
```

### 4. コメント分析の改善
```python
# コメントの内容分析
song_title_mentions = 0  # 曲名への言及
artist_mentions = 0      # アーティストへの言及
timestamp_quality = 0    # タイムスタンプの形式の質

for comment in comments:
    # 「曲名 / アーティスト」形式のタイムスタンプ（最も信頼できる）
    if re.search(r'\d{1,2}:\d{2}.*?/.*?[^\d]', comment):
        timestamp_quality += 2

    # セットリスト関連のコメント
    if any(kw in comment.lower() for kw in ['セトリ', 'setlist', 'セットリスト']):
        singing_score += 1
```

### 5. 重み付けの見直し
**信頼度の高い順:**
1. タイムスタンプに「曲名 / アーティスト」形式が多い → +6
2. コメントに複数のタイムスタンプ+歌手名 → +4
3. タイトルに「歌」「歌枠」 → +3
4. 概要欄にタイムスタンプ多数 → +2
5. 音楽関連キーワード → +1

### 6. マイナス要因の強化
```python
# 明らかに歌ではない動画
if any(kw in title.lower() for kw in ['ゲーム実況', 'gameplay', 'プレイ動画']):
    exclude_score += 5  # 現在は1点ずつだが、強いシグナルには重みを
```

## 推奨実装順序
1. **タイムスタンプの質評価** - 最も効果が高い
2. **動的な正規化** - スコアの範囲を適切に
3. **重み付けの見直し** - 信頼できるシグナルに高い重み
4. **マイナス要因の強化** - ノイズを減らす
5. **動画メタデータの活用** - さらなる精度向上
