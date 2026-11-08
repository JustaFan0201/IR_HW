# IR Homework 2: 查詢處理與搜尋系統 (Query Processing and Searching)
---

## 1. 系統與環境需求 (Execution Environments)

- **Python 版本**：建議使用 Python 3.10 以上版本 (本專案於 Python 3.13 測試通過)。
- **相依檔案需求**：先透過 HW1 生成倒排索引檔 (預設為 `HW1.txt`)。
- **相依套件**：`pip install -r requirements.txt`（僅需 nltk，提供 Porter 詞幹還原，與 HW1 的 Solr PorterStemFilter 一致）。
- **無特殊編譯器需求**：本專案以純 Python 實作向量空間模型，無需額外安裝 Java 執行環境或 Solr 伺服器即可進行搜尋運算。

---

## 2. 專案結構與前置作業

**放置索引檔案：**
請確保您已將 HW1 產出的倒排索引檔 (`HW1.txt`) 放置於本專案 (`hw2/`) 的根目錄下。

---

## 3. 設定與全域參數 (Configuration)
本系統的環境與參數皆封裝於 **`SourceCode/config.py`** 中。

*   **索引檔設定**：若您的索引檔案名稱不同，請於 `config.py` 中修改 `INDEX_FILE_NAME`。
*   **文件總數 (Total Documents)**：TF-IDF 計算中需要使用總文件數 (N)。請確認 `config.py` 中的 `TOTAL_DOCS` 參數與您 HW1 實際匯入的文件數量一致 (預設為 10000 篇)。

---

## 4. 系統執行與搜尋 (System Execution)

**4.1 啟動搜尋系統：**
在專案根目錄下，執行以下指令以載入索引並啟動互動式搜尋介面：
```bash
python SourceCode/Search.py
```

**4.2 支援的查詢格式 (Supported Queries)：**
查詢會先經過與 HW1 索引相同的分析鏈 (`SourceCode/analyzer.py`：切詞 → 小寫 → 停用詞 → Porter 詞幹)，因此 `governments` 會對應到索引中的 `govern`。
啟動後，您可以在終端機的 `cmd>` 提示字元輸入以下查詢類型：
- **單一關鍵字 (Single keywords)**：例如 `airplanes`
- **自由文本 (Free texts)**：例如 `United States government`
- **拼字校正 (Spell correction)**：查詢詞不在索引中時會列出最多 3 個候選詞，輸入 `y` 使用第一個建議，只檢查至少 4 個字母的英文詞
- **布林運算子搜尋 (Boolean operators search)**：支援 `AND`、`OR` 及括號，例如 `hong AND kong`、`hong OR kong`、`(arc OR zip) AND stop`。查詢含有 Boolean 運算子或括號時，未寫運算子的相鄰詞視為 `AND`，且 `AND` 優先於 `OR`。

**4.3 輸出格式與前 N 名 (`--top`)：**
系統採用 **向量空間模型 (Vector Space Model)** 排序，輸出格式遵守作業規範：
`<doc#>    <similarity score>` (例如：`clueweb09-en0000-02-12984    0.176598`)

用 `--top N` 決定顯示/輸出前 N 名 (預設 10，可在 `config.py` 的 `TOP_K` 修改)：
```bash
python SourceCode/Search.py --top 20
```
互動模式輸入 `exit` 即可安全關閉系統。

**4.3.1 批次模式與輸出檔：**
給一個查詢檔 (每行一個查詢，範例見 `queries.txt`)，結果寫入輸出檔 (預設 `HW2.txt`，可用 `--output` 或 `config.py` 修改)：
```bash
python SourceCode/Search.py --queries queries.txt --output HW2.txt --top 100
```
輸出檔每個查詢一段，`Query:` 開頭，接著 `<doc#>` 與分數 (以 Tab 分隔)；`#` 開頭的行是註解 (錯誤訊息、拼字建議)。批次模式不會詢問拼字替換，只把建議寫成註解。
