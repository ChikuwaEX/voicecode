# 🔮 VOICECODE プレミアムレポート — 確定設計仕様書
> **ステータス: LOCKED（確定版）** | 最終更新: 2026-06-15
> ユーザーにより承認済み。このフォーマットを基準として維持すること。

---

## 📋 概要

| 項目 | 値 |
|---|---|
| **レポートエンジン** | Playwright (Chromium headless) + Jinja2 |
| **出力形式** | Web表示（HTML）＋ PDFダウンロード の両立 |
| **PDFサイズ（目安）** | 約2.0 MB |
| **ページ数** | A4 12ページ以上 |
| **セクション数** | 12セクション（目次含む） |
| **グラフ数** | 6種類（Chart.js v4.4.0） |
| **フォント** | Cinzel（英字見出し）/ Shippori Mincho（日本語）/ Noto Sans JP（本文） |
| **カラースキーム** | ダークモード（#08080F背景）+ ゴールド（#D4AF37）+ アーキタイプ別アクセントカラー |

---

## 🗂️ 12セクション構成（確定）

| # | セクション | 英語タイトル | 内容 |
|---|---|---|---|
| 表紙 | カバーページ | Soul Blueprint | アーキタイプ絵文字・名前・タグライン・声紋コードID・発行日 |
| 目次 | コンテンツ一覧 | Contents | 12セクション一覧 |
| 01 | エグゼクティブ・サマリー | Executive Summary | 4枠サマリーカード＋総合所見文 |
| **02** | **声紋周波数詳細データ** | **Frequency Analysis** | **★6種のChart.jsグラフ（後述）** |
| 03 | 5元素エネルギーマトリクス | Element Matrix | 5元素カード（主元素バッジ付き）＋解釈テキスト |
| 04 | 隠れた才能の覚醒 | Hidden Talent | 才能説明＋3つの具体的発現シーン |
| 05 | ソウルミッション | Soul Mission | 使命説明＋過去の出来事の霊的解釈 |
| 06 | 人間関係・共鳴マップ | Resonance Map | 高共鳴タイプ＋摩擦タイプ＋チャクラ活性化 |
| 07 | シャドウの統合 | Shadow Integration | シャドウ説明＋ユング的統合実践法2枠 |
| 08 | チャクラ別エネルギー診断 | Chakra Diagnosis | 7チャクラ（HIGH/MID/LOWレベル）全診断 |
| 09 | 2026年 宇宙のメッセージ | Universe Message 2026 | 宇宙バイオリズムと個人的指針 |
| 10 | 才能の開花を加速する3つの鍵 | Activation Keys | 3段カード形式の具体的アクション処方箋 |
| 11 | 30日間魂のアクティベーションプラン | 30-Day Plan | 週別4フェーズ（観察→解放→表現→統合） |
| 12 | ヒーリングリソース処方箋 | Healing Resources | 6枠グリッド（クリスタル・音・自然・書籍・瞑想・日課） |
| 裏表紙 | クロージング | — | 締めの言葉・セッションIDと発行情報 |

---

## 📊 6種グラフ仕様（確定・Section 02内）

### Row 1: パーソナリティ分析
| グラフ | Chart.js種別 | ID | データソース | 科学的根拠 |
|---|---|---|---|---|
| Big5レーダーチャート | `radar` | `radarChart` | `score_json`（Big5の5軸） | Mairesse et al.(2007) |
| 声帯品質スコア | `bar`（水平・indexAxis:y） | `voiceQualityChart` | `acoustic_json`（HNR/Jitter/Shimmer/RMS/話速） | Praat準拠アルゴリズム |

### Row 2: 周波数・元素分析
| グラフ | Chart.js種別 | ID | データソース | 科学的根拠 |
|---|---|---|---|---|
| F0ピッチ分布 | `bar`（縦） | `pitchChart` | `acoustic_json`（f0_min/mean/max/range） | YIN算法 |
| 5元素エネルギードーナツ | `doughnut` | `elementDonutChart` | `score_json`（Big5→5元素変換） | 元素スピリチュアルモデル |

### Row 3: 深層音響指紋
| グラフ | Chart.js種別 | ID | データソース | 科学的根拠 |
|---|---|---|---|---|
| MFCC係数 | `bar`（縦・正負） | `mfccChart` | `acoustic_json.mfcc`（係数1-6） | librosa Python |
| 音響特徴量vs平均比較 | `bar`（水平・2系列） | `featureBarChart` | `score_json`（Big5スコア vs 平均50%） | 相対的ポジション可視化 |

---

## 🗃️ 主要ファイル一覧

| 役割 | パス |
|---|---|
| **HTMLテンプレート（確定版）** | `src/report/templates/premium_report.html` |
| **PDFジェネレーター** | `src/report/generator.py` |
| **診断モデル（音響データ付き）** | `src/diagnosis/models.py` |
| **診断エンジン** | `src/diagnosis/engine.py` |
| **アーキタイプYAML** | `src/diagnosis/worldview/themes/elements_v1.yaml` |
| **APIエンドポイント（View/DL）** | `src/api/report.py` |
| **音声アップロードAPI** | `src/api/audio.py` |

---

## 🔧 テンプレートコンテキスト変数（確定）

```python
# generator.py _build_template_context() が返す辞書のキー一覧
{
    "session_id": str,
    "user_name": str,
    "voice_code_id": str,      # 例: "#A7-440Hz"
    "diagnosed_at": str,       # 例: "2026.06.15"
    "score_data": {            # Big5スコア（0-100の整数）
        "openness": int,
        "conscientiousness": int,
        "extraversion": int,
        "agreeableness": int,
        "neuroticism": int,
    },
    "score_json": str,         # score_data のJSON文字列（JS用）
    "element_color": str,      # 主元素のHEXカラーコード
    "archetype": {
        "name": str,           # 例: "天空のモデレーター"
        "emoji": str,          # 例: "🌌"
        "tagline": str,
        "rarity": str,
        "dominant_elements": list[str],  # 例: ["空", "地"]
        "hidden_talent": {"title": str, "description": str, "examples": list},
        "mission": {"title": str, "description": str, "past_interpretation": str},
        "shadow": {"title": str, "description": str},
        "resonance": {"compatible_types": list, "compatible_description": str,
                      "challenging_types": list, "chakra_activation": str},
        "universe_message_2026": {"title": str, "description": str},
        "keys_to_bloom": list[{"title": str, "description": str}],
        "element_crystal": str,   # 例: "クンツァイト・モルガナイト"
        "element_note": str,      # 例: "639Hz（F音）- 愛と接続"
        "element_chakra": str,    # 例: "第4チャクラ（ハート）無条件の愛の拡張瞑想"
    },
    "acoustic_json": str,      # 音響生データのJSON文字列（6グラフ用）
    # acoustic_jsonの内部キー:
    # f0_mean, f0_std, f0_max, f0_min, jitter_pct, shimmer_pct,
    # hnr_score, jitter_score, shimmer_score, rms_energy_pct,
    # speech_rate_pct, pause_ratio_pct, spectral_centroid, f1, f2, mfcc(list)
}
```

---

## 🎨 デザイントークン（確定）

```css
--bg: #08080F;              /* メイン背景 */
--bg2: #0D0D1A;
--text: #E8E0FF;            /* メインテキスト */
--text-muted: #7A7A9A;
--accent: {element_color};  /* アーキタイプ別アクセント */
--gold: #D4AF37;            /* ゴールド */
--gold2: #F0D060;           /* ライトゴールド */
--border: rgba(255,255,255,0.08);
--border-accent: rgba(212,175,55,0.25);
--serif: 'Shippori Mincho', serif;
--sans: 'Noto Sans JP', sans-serif;
--display: 'Cinzel', serif;
```

---

## ⚙️ アーキタイプ別アクセントカラー

| アーキタイプコード | 主元素 | アクセントカラー |
|---|---|---|
| FIRE系（SOLAR_HERALD, STORM_SHAMAN） | 火 | `#D4AF37`（ゴールド） |
| WATER系（MOON_SAGE, FOG_ORACLE, TIDE_WANDERER） | 水 | `#2C3E50`（ネイビー） |
| WIND系（COMET_SEEKER, WIND_PIONEER） | 風 | `#BDC3C7`（シルバー） |
| EARTH系（EARTH_GUARDIAN） | 地 | `#5D4037`（アースブラウン） |
| SKY系（SKY_HARMONIST, STAR_ARCHITECT） | 空 | `#8E44AD`（ロイヤルパープル） |

---

## 🚀 起動コマンド

```bash
# サーバー起動
.\venv\Scripts\python.exe -m src.main

# テスト実行
.\venv\Scripts\python.exe test_api.py

# WebレポートURL
http://localhost:8000/api/v1/report/{session_id}/view

# PDFダウンロードURL
http://localhost:8000/api/v1/report/{session_id}/download
```

---

## 📌 変更禁止事項（ユーザー承認済み仕様）

1. **12セクションの構成順序** — 変更しない
2. **6グラフのレイアウト（3行×2列）** — 変更しない
3. **ダークモード＋ゴールドのカラースキーム** — 変更しない
4. **Playwright（Chromium）PDFエンジン** — 他のエンジンへの変更禁止
5. **「Scientific Basis」セクション** — 科学的根拠の明記を省略しない
