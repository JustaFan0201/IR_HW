# IR Homework 2: 查詢處理與搜尋系統 (Query Processing and Searching)
---

## 1. 系統與環境需求 (Execution Environments)

- **Python 版本**：建議使用 Python 3.10 以上版本 (本專案於 Python 3.13 測試通過)。
- **相依檔案需求**：先透過 HW1 生成倒排索引檔 (預設為 `HW1.txt`)。
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
啟動後，您可以在終端機的 `cmd>` 提示字元輸入以下查詢類型：
- **單一關鍵字 (Single keywords)**：例如 `airplanes`
- **自由文本 (Free texts)**：例如 `United States government`
- **拼字校正 (Spell correction)**：查詢詞不在索引中時會列出最多 3 個候選詞，輸入 `y` 使用第一個建議，只檢查至少 4 個字母的英文詞
- **布林運算子搜尋 (Boolean operators search)**：支援 `AND`、`OR` 及括號，例如 `hong AND kong`、`hong OR kong`、`(arc OR zip) AND stop`。查詢含有 Boolean 運算子或括號時，未寫運算子的相鄰詞視為 `AND`，且 `AND` 優先於 `OR`。

**4.3 輸出格式：**
系統將採用 **向量空間模型 (Vector Space Model)** 進行排序，並回傳前 10 名的搜尋結果 (Top-10 Ranking)，輸出格式嚴格遵守作業規範：
`<doc#>    <similarity score>` (例如：`urn:uuid:xxx    0.872350`)

輸入 `exit` 即可安全關閉系統。

**4.4 執行測試：**
在專案根目錄執行以下指令，驗證 Boolean 查詢剖析、文件集合運算、錯誤語法處理，以及結果篩選：
```bash
python -m unittest discover -s SourceCode -p "test_*.py" -v
```