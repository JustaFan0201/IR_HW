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
- **布林搜尋 (Boolean search)**：*(若有整合 Skip Pointer 加分項可於此註明，例如支援 `AND` / `OR` 運算)*

**4.3 輸出格式：**
系統將採用 **向量空間模型 (Vector Space Model)** 進行排序，並回傳前 10 名的搜尋結果 (Top-10 Ranking)，輸出格式嚴格遵守作業規範：
`<doc#>    <similarity score>` (例如：`urn:uuid:xxx    0.872350`)

輸入 `exit` 即可安全關閉系統。