# IR Homework 2: 查詢處理與搜尋系統 (Query Processing and Searching)
---

## 1. 環境需求

- **Python 3.10 以上** (於 Python 3.13 測試通過)。
- **套件**：`pip install -r requirements.txt` (只需 nltk，提供 Porter 詞幹還原，與 HW1 的 Solr PorterStemFilter 一致)。
- **索引檔**：把 HW1 產出的倒排索引 `HW1.txt` 放在 `hw2/` 根目錄 (檔名可在 `config.py` 的 `INDEX_FILE_NAME` 修改)。
- 純 Python 實作，不需要 Java 或 Solr 伺服器。

## 2. 設定 (`SourceCode/config.py`)

| 參數 | 說明 | 預設 |
|---|---|---|
| `INDEX_FILE_NAME` | 索引檔名 | `HW1.txt` |
| `TOTAL_DOCS` | 文件總數 N (IDF 用)，須與 HW1 索引的文件數一致 | `35011` |
| `TOP_K` | 預設顯示/輸出前幾名 | `10` |
| `DEFAULT_WEIGHTING` | 預設權重方案 | `tfidf` |
| `BM25_K1`、`BM25_B` | BM25 參數 | `1.2`、`0.75` |
| `WILDCARD_MAX_TERMS` | 萬用字元最多展開幾個詞 | `50` |
| `OUTPUT_FILE_NAME` | 批次模式的輸出檔 | `HW2.txt` |

## 3. 執行

```bash
python SourceCode/Search.py                      # 互動模式，出現 cmd> 後輸入查詢，exit 離開
python SourceCode/Search.py --top 20             # 顯示前 20 名
python SourceCode/Search.py --weighting bm25     # 換權重方案
python SourceCode/Search.py --queries queries.txt --output HW2.txt --top 100   # 批次模式
```

| 參數 | 說明 |
|---|---|
| `--top N` | 顯示/輸出前 N 名 |
| `--weighting` | `tfidf` (預設)、`tfidf-raw`、`bm25`，見第 5 節 |
| `--champion R` | 啟用 champion list 近似檢索，見第 6 節 |
| `--queries FILE` | 批次模式：查詢檔，每行一個查詢 |
| `--output FILE` | 批次模式的輸出檔 |

## 4. 支援的查詢

| 類型 | 範例 | 說明 |
|---|---|---|
| 單一關鍵字 | `airplanes` | |
| 自由文本 | `United States government` | |
| 布林查詢 | `hong AND kong`、`hong OR kong`、`(arc OR zip) AND stop`、`hong AND NOT kong` | `AND`、`OR`、`NOT`、括號；`NOT` 優先於 `AND`，`AND` 優先於 `OR` |
| 片語 | `"hong kong"` | 詞依序緊鄰出現 |
| 鄰近 | `"hong kong"~5` | 所有詞在 5 個位置內，不限順序 |
| 萬用字元 | `govern*`、`*ment`、`micro*soft` | `*` 代表任意長度字元 |
| 拼字校正 | `goverment` | 有可疑的詞時列出最多 3 個建議，輸入 `y` 套用第一個 |

以上可以組合，例如 `"open source" AND linux`、`govern* AND NOT policy`。

**查詢前處理**：與 HW1 索引相同的分析鏈 (`SourceCode/analyzer.py`)：切詞 → 小寫 → 停用詞 → Porter 詞幹，所以 `governments` 會對應到索引裡的 `govern`。

**注意事項**
- 索引存的是**詞幹**，拼字建議也是詞幹形式 (如 `govern`)；萬用字元比對的也是詞幹 (`air*ne` 找不到，因為 `airplane` 在索引裡是 `airplan`，可改用 `airpl*`)。
- `NOT` 必須大寫 (小寫的 not 是停用詞)，且至少要搭配一個正向詞。
- 查詢含布林運算子、括號、引號或 `*` 時，沒寫運算子的相鄰詞視為 `AND`。
- 萬用字元樣式至少要有 2 個非 `*` 的字元；展開結果只保留 df 最高的 `WILDCARD_MAX_TERMS` 個詞，被截斷時會顯示說明。
- 片語查詢只讀候選文件的位置資訊，不佔額外記憶體；停用詞留下的位置空位會保留，所以 `"united states of america"` 的 `of` 位置可由任何停用詞佔據。
- 拼字檢查只處理至少 4 個字母的英文詞；詞不在索引中，或 df 很低 (<50) 且有 df 高 20 倍以上的相近詞時才會建議。

## 5. 排序與輸出

**排序**：向量空間模型，輸出格式 `<doc#> <similarity score>` (例如 `clueweb09-en0000-02-12984    0.176598`)。

| `--weighting` | 文件詞權重 | 排序 |
|---|---|---|
| `tfidf` (預設，作業指定) | `(1 + log tf) × log(N/df)` | cosine similarity (0~1) |
| `tfidf-raw` | `tf × log(N/df)` | cosine similarity |
| `bm25` | Okapi BM25，文件長度為索引中的詞數 | 直接加總，分數可大於 1 |

**批次輸出檔**：每個查詢一段，以 `Query:` 開頭，接著每行 `<doc#>` 與分數 (以 Tab 分隔)；第一行 `# weighting: ...` 註明方案，其他 `#` 開頭的行是註解 (錯誤訊息、拼字建議、萬用字元展開說明)。批次模式不會詢問拼字替換，只把建議寫成註解。

## 6. 近似 top-k：champion list (`--champion R`)

```bash
python SourceCode/Search.py --champion 200               # 互動模式
python SourceCode/Search.py --champion 200 --weighting bm25
python SourceCode/Benchmark.py                           # 速度與排名差異比較
```

啟動時為每個 df > R 的詞建立 champion list：只保留「對該詞貢獻最大」的 R 篇文件 (貢獻依所選權重方案計算，含文件長度正規化)。查詢時只掃 champion list，不掃完整 postings。
- champion list 是針對 `--weighting` 建立的，查詢用的方案必須一致 (CLI 保證一致)。
- 結果少於 `--top` 篇時，自動退回掃完整 postings (精確計分)。
- 布林/片語/萬用字元的「文件篩選」仍是精確的，只有計分是近似。
- 因為只計 champion 內的文件，畫面或輸出檔顯示的命中篇數會比精確模式少，前幾名則大致相同。

`Benchmark.py` 實測結果 (35,011 篇文件、12 個查詢，只量計分與排序；前 10 名重疊率 = 與精確計分前 10 名相同的比例)：

| 權重方案 | R | 平均耗時 | 加速 | 前 10 名重疊 |
|---|---|---|---|---|
| tfidf | 精確 | 10.01 ms | 1x | 100% |
| tfidf | 50 | 0.05 ms | 186x | 66% |
| tfidf | 200 | 0.22 ms | 45x | 92% |
| tfidf | 1000 | 1.10 ms | 9x | 98% |
| bm25 | 精確 | 9.77 ms | 1x | 100% |
| bm25 | 200 | 0.23 ms | 43x | 70% |
| bm25 | 1000 | 1.38 ms | 7x | 93% |

R 越小越快、越不準；`tfidf` 用 R=200 是不錯的折衷。(耗時會隨機器而異。)
