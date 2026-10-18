# IR Homework 1: 倒排索引建置
---

## 1. 系統與環境需求

- **Python 版本**：建議使用 Python 3.10 以上版本 (本專案於 Python 3.13 測試通過)。
- **Java 環境**：JDK 17。
- **搜尋引擎**：Apache Solr 9.x。

---

## 2. 套件安裝
切換到專案根目錄 (VSCode Terminal) 並執行以下指令來安裝相依套件：
```bash
cd hw1
pip install -r requirements.txt
```

---

## 3. Solr 核心 (Core) 建置與設定 
*(備註：環境已建置完畢則無須執行。若是直接 Clone 此專案且已包含設定檔，可跳過此步驟。)*

**3.1 創建 Core：**
切換到專案根目錄 (CMD)，創建 Core：
```bash
cd Solr\bin
solr.cmd create -c hw1
```

**3.2 初始化 Schema 設定與查詢通道：**
切換到專案根目錄 (VSCode Terminal) 並執行以下指令來初始化最基礎的 Schema 與開啟 TermVector 通道：
```bash
cd hw1
python SourceCode/InitSchema.py
```

---

## 4. 設定與功能開關 (Parameter Trigger)
 **`SourceCode/config.py`** 。

*   **資料集設定**：若要更換 `.warc` 檔案，請將檔案放置於 `hw1` 根目錄，並在 `config.py` 中修改 `WARC_FILE_NAME`。
*   **語言處理功能開關**：您可以在 `config.py` 中切換以下布林值 (`True`/`False`)：
    *   `ENABLE_CASE_FOLDING` (大小寫轉換)
    *   `ENABLE_STOPWORD_REMOVAL` (停用詞移除)
    *   `ENABLE_STEMMING` (詞幹提取)

修改完 `config.py` 後，若有變更語言處理開關，請執行以下指令來覆蓋 Solr Schema 設定 (Github上環境為開啟狀態)： 
```bash
python SourceCode/SetupSchema.py
```
(注意：每次覆蓋 Schema 後，必須重新執行下方第 5 步的 `IndexWarc.py` 讓資料重新建立索引方可生效)

---

## 5. 創建索引與匯出

**5.1 解析 WARC 並匯入資料：**
(執行後會清空 Solr 中的舊資料)
```bash
python SourceCode/IndexWarc.py
```
(測試時可加數字只匯入前 N 篇，例如 `python SourceCode/IndexWarc.py 200`)

**5.2 提取詞向量並匯出格式化索引：**
執行完畢後會在專案根目錄 (`hw1/`) 產出兩個檔案：
- `HW1_dictionary.txt`：詞典檔，排序後的詞，一行一個。
- `HW1.txt`：倒排索引，格式為 `term, df: <docID, tf: <pos1, pos2, ...>; ...>`。
```bash
python SourceCode/ExportIndex.py
```

**5.3 (選做) Skip pointer：**
另外輸出附帶 skip pointer 的索引 `HW1_skip.txt`，並可做 AND 查詢比較比對次數 (詞要用索引裡的形式)：
```bash
python SourceCode/SkipPointer.py build
python SourceCode/SkipPointer.py query download linux
```

---

## 6. 補充說明

* **文件 ID**：使用 WARC 標頭的 `WARC-TREC-ID` (例如 `clueweb09-en0000-02-00000`)。
* **詞的位置**：由 0 開始計算；移除停用詞後，位置不會重新編號 (會留下空位)。
* **斷詞**：使用 Solr 的 StandardTokenizer，標點符號會被切掉。
* **Solr 記憶體**：預設只有 512 MB，匯入完整的 1 GB 資料前建議先調高。啟動前在 CMD 執行 `set SOLR_HEAP=2g`，再執行 `start_solr.bat`。