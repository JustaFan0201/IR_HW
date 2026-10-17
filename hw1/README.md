# IR Homework 1: 倒排索引建置
---

## 1. 系統與環境需求

* **Python 版本**：建議使用 Python 3.10 以上版本 (本專案於 Python 3.13 測試通過)。
* **Java 環境**：JDK 17 。
* **搜尋引擎**：Apache Solr 9.x。

---

## 2. 套件安裝
切換到專案根目錄(VSCode Terminal)並執行以下指令來安裝相依套件：
```bash
cd hw1
pip install -r requirements.txt
```
## 3. Solr 核心 (Core) 建置與設定 (備註：環境已建置完畢則無須執行)
請先參考根目錄的 README.md 啟動 Solr 伺服器。  
如果是直接 Clone 此專案且已包含設定檔，可跳過此步驟。  

切到專案根目錄(CMD)，創建 Core：
```bash
cd Solr\bin
solr.cmd create -c hw1
```
切換到專案根目錄(VSCode Terminal)並執行以下來初始化 Schema 設定
```bash
cd hw1
python SourceCode/SetupSchema.py
python SourceCode/EnableTV.py
```
## 4. 創建索引與匯出
請確保您的 .warc 資料集檔案已放置於 SourceCode 資料夾中。  
(註：若 .warc 檔案名稱非預設名稱 (02.warc) ，請到 IndexWarc.py 中修改對應的名稱。)  

解析 WARC 並匯入資料：
```bash
python SourceCode/IndexWarc.py
```
提取詞向量並匯出格式化索引
```bash
python SourceCode/ExportIndex.py
```