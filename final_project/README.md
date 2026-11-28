# 期末專案：互動式搜尋系統

在 HW2 的搜尋系統上加入相關回饋、結果分群與語意檢索。各模組的函式介面見 [`proposal/INTERFACE.md`](../proposal/INTERFACE.md)。

以下指令都要在 `final_project/` 目錄下執行，從 repo 根目錄先切換過去：

```bash
cd final_project
```

## 1. 準備

### 1.1 安裝套件

需要 Python 3.10 以上。

```bash
pip install -r requirements.txt
```

`requirements.txt` 包含 nltk、numpy、sentence-transformers。第一次使用語意檢索時，會自動下載 `all-MiniLM-L6-v2` 模型（約 90MB）。

### 1.2 放好資料檔

以下檔案都不進 git，要自己準備：

| 檔案 | 放在哪裡 | 怎麼取得 |
|---|---|---|
| `HW1.txt`（倒排索引） | `final_project/HW1.txt` | 從 `hw2/HW1.txt` 複製過來，或用 HW1 的 `ExportIndex.py` 重新匯出 |
| `02.warc`（原始網頁） | `hw1/02.warc` | 課程提供的檔案。網頁摘要、全文和語意向量都從這個檔讀 |

### 1.3 建立語意向量（只要做一次，約 13 分鐘）

```bash
python SourceCode/semantic.py --build
```

這一步會把 35,011 篇文件全部編碼，產生 `semantic_vectors.npy`（約 54MB）和 `semantic_doc_ids.txt`：

- 每篇取「標題 + 內文前 200 個詞」編碼。
- 從 WARC 取文字約 2 分鐘，CPU 編碼約 11 分鐘。
- 只有改了編碼方式（模型或取字規則）才需要重跑。

## 2. 執行

### 網頁介面

```bash
python SourceCode/WebApp.py                 # 開啟 http://127.0.0.1:8000
python SourceCode/WebApp.py --port 8080     # 換 port
```

啟動後約 20 秒載入索引，WARC 在背景掃描。掃描完成前就能搜尋，只是還不會顯示摘要。

### 命令列

```bash
python SourceCode/Search.py                          # HW2 的互動搜尋 (tfidf / bm25 ...)
python SourceCode/semantic.py footwear --top 10      # 語意檢索
```

## 3. 功能

| 功能 | 模組 | 狀態 | 怎麼用 |
|---|---|---|---|
| 布林、片語、萬用字元、拼字校正、tfidf／bm25 | HW2 | 完成 | 查詢語法見 [`hw2/README.md`](../hw2/README.md) |
| 相關回饋（Rocchio） | A | 已接上網頁 | 見下方說明 |
| 查詢擴展詞建議 | A | 函式完成，網頁未接 | |
| 結果分群、2D 散佈圖 | B | 開發中 | |
| 語意檢索 | C | 函式完成，網頁未接 | `semantic.py` 命令列 |
| 混合排序（BM25 + 語意） | C | 第 3 週 | |
| 評估（P@10、MAP、nDCG）、語言模型 | D | 開發中 | |

### 相關回饋怎麼用

1. 搜尋後，在每筆結果的 doc ID 旁勾選 👍（相關）或 👎（不相關）。
2. 按「依回饋重新搜尋」，系統會用 Rocchio 修正查詢向量，再以 tfidf cosine 重新排序。
3. 結果頁上方會列出 Rocchio 新加入的詞，按「清除回饋」回到原始結果。
4. 勾選會保留在網址上，可以繼續勾、再重查，多輪累積。

範例：查 `jaguar`，把汽車相關的結果勾 👍、樂團的勾 👎，重查後前 10 名幾乎都是汽車。

## 4. 設定（`SourceCode/config.py`）

除了 HW2 原有的參數，另外有：

| 參數 | 模組 | 說明 | 預設 |
|---|---|---|---|
| `ROCCHIO_ALPHA`、`ROCCHIO_BETA`、`ROCCHIO_GAMMA` | A | Rocchio 的原查詢／相關／不相關權重 | `1.0`、`0.75`、`0.15` |
| `EXPAND_TERMS_M` | A | 擴展詞數量 | `5` |
| `SEMANTIC_MODEL` | C | sentence-transformers 模型 | `all-MiniLM-L6-v2` |
| `SEMANTIC_BODY_WORDS` | C | 每篇取內文前幾個詞編碼 | `200` |
| `SEMANTIC_VECTORS_PATH`、`SEMANTIC_IDS_PATH` | C | 語意向量與 doc ID 順序檔 | `final_project/` 下 |

## 5. 程式結構（`SourceCode/`）

| 檔案 | 負責 | 內容 |
|---|---|---|
| `Search.py` | 共用 | 索引載入、各種查詢與排序（HW2）；新增 `get_doc_vector`（A）、`query_vector`、`rank_by_vector`（C） |
| `analyzer.py` | 共用 | 查詢斷詞，與 HW1 索引相同：小寫、停用詞、Porter 詞幹 |
| `docs.py` | C | 讀 WARC、HTML 轉成標題 + 內文；網頁和語意編碼共用 |
| `feedback.py` | A | `rocchio()`、`expand_terms()` |
| `semantic.py` | C | `semantic_search()`、離線編碼 `--build` |
| `WebApp.py` | C | 網頁介面，整合各模組 |
| `clustering.py` | B | 開發中 |
| `evaluate.py`、`lm.py` | D | 開發中 |
