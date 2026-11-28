# IR Homework 3: Open LLM 與 RAG 檢索增強生成 (LLM and RAG Systems)
---

## 1. 環境需求

- **Python 3.10 以上** (於 Python 3.13 測試通過)。
- **Ollama 伺服器**：需要在本地端安裝並執行 [Ollama](https://ollama.com/)，並下載指定模型：
  ```bash
  ollama run llama3.2
  ```
- **Python 套件**：`pip install -r requirements.txt` (包含 `ollama` 與 `nltk`)。
- **索引檔與 WARC 檔**：先準備好 `hw1/02.warc` 與 `hw1/HW1.txt`，再執行下面的「嵌入學號」產生 HW3 用的檔案。

### 嵌入學號 (特殊 token)

作業要求在文件集裡嵌入特殊 token。組員學號與要嵌入的文件寫在 `embed_tokens.json` (進 git)，由腳本產生 HW3 用的 WARC 與索引：

```bash
python SourceCode/EmbedTokens.py
```

- 輸入 (不修改)：`hw1/02.warc`、`hw1/HW1.txt`
- 輸出：`hw3/02_hw3.warc`、`hw3/HW1.txt` (被 `.gitignore`，每個人自己產生，約 20 秒)
- 每篇在 HTML 最前面插入一句 `IR HW3 special token: student ID <學號>.`；索引直接修補 (該篇原有詞的位置 +7，再加上這句的詞)，不需要重跑 Solr
- 同一份設定 + 同一支程式 → 輸出完全相同。跑完請比對 sha256：

| 檔案 | sha256 |
|---|---|
| `02_hw3.warc` | `e4a0b5831b2c58d233aae7cfb7beb8128e053db1cb6399aad99fe5c96ce829a5` |
| `HW1.txt` | `c37b71f5753152ce02a27fe1c6233cea43bd7cd569221f401157697491aec77d` |

| 學號 | 嵌入的文件 |
|---|---|
| 112590007 | `clueweb09-en0000-02-01999` |
| 112590030 | `clueweb09-en0000-02-11022` |
| 112590013 | `clueweb09-en0000-02-21424` |
| 112590019 | `clueweb09-en0000-02-29045` |

要換文件或改句子：改 `embed_tokens.json` 後重跑，並更新上表的 sha256。`python SourceCode/EmbedTokens.py --check` 可只檢查設定不寫檔 (文件不在索引裡、或抽出的文字不是以嵌入句開頭時會報錯)。

## 2. 設定 (`SourceCode/config.py`)

| 參數 | 說明 | 預設 |
|---|---|---|
| `INDEX_FILE_NAME` | 倒排索引檔名 | `HW1.txt` |
| `TOTAL_DOCS` | 文件總數 N (IDF 用)，須與 HW1 索引的文件數一致 | `35011` |
| `TOP_K` | Retriever 預設檢索的前 N 名文件筆數 | `10` |
| `DEFAULT_WEIGHTING` | 預設權重方案 (`tfidf` / `bm25`) | `tfidf` |
| `WARC_FILE_PATH` | 嵌入學號後的 WARC (提供 RAG 內文) | `02_hw3.warc` |
| `OUTPUT_FILE_NAME` | 批次模式的輸出檔名 | `HW3.txt` |

## 3. 執行

### 互動與對比測試模式 (Terminal Interactive Mode)

執行 `RagLLM.py` 可直接進行 **有 RAG vs 無 RAG** 的即時對比測試：

```bash
python SourceCode/RagLLM.py
```

執行後系統會自動載入 `HW1.txt` 倒排索引並背景掃描 `02.warc` 文件庫。在 `cmd>` 提示字元輸入 Prompt 後，系統會分別印出：
1. **[無 RAG 對照組]**：直接將 Prompt 送交 Ollama 模型回答。
2. **[有 RAG 實驗組]**：先呼叫 `Search.py` 檢索相關文件內文，組合成 Context 後送交 Ollama 模型回答。

### 程式碼引用範例 (API Call)

可直接從其他模組匯入 `RagLLM.py` 的核心函式進行系統整合：

```python
from RagLLM import generate_rag_response

# 呼叫無 RAG 模型回答
ans_no_rag = generate_rag_response("112590013", use_rag=False)

# 呼叫有 RAG 模型回答 (搭配 llama3.2)
ans_rag = generate_rag_response("112590013", use_rag=True, model_name="llama3.2")
```

## 4. 系統架構與模組設計

本作業採用 **Method 2 (Retriever Function + Open LLM)** 架構，流程如下：

```
[User Prompt] 
    │
    ├─── (無 RAG) ───> [Ollama LLM (llama3.2)] ───> LLM Response
    │
    └─── (有 RAG) ───> [Retriever (Search.py)] ───> 讀取倒排索引 (HW1.txt)
                             │
                             ▼
                      [DocStore (WebApp.py)] ───> 擷取 WARC 內文 (02.warc)
                             │
                             ▼
                      [Context + Prompt] ───> [Ollama LLM] ───> RAG Response
```

### 主要檔案與分工說明

| 檔案 | 功能描述 |
|---|---|
| `SourceCode/RagLLM.py` | **RAG 核心邏輯**：負責整合 Retriever 與 Ollama API，組合 Final Prompt 並控制 Context 視窗大小。 |
| `SourceCode/Search.py` | **Retriever 檢索器**：基於 HW2 向量空間模型 (TF-IDF + Cosine Similarity / BM25)，快速算出對應 Prompt 的前 $k$ 篇相關文件。 |
| `SourceCode/WebApp.py` (`DocStore`) | **文檔快取器**：負責解析 WARC 檔案，根據 `doc_id` 抽取對應文件的原始標題與內文。 |
| `SourceCode/analyzer.py` | **查詢前處理**：標準化切詞鏈 (StandardTokenizer → LowerCase → StopFilter → PorterStem)，確保查詢詞與 HW1 倒排索引完全對齊。 |
| `SourceCode/config.py` | **全域設定檔**：管理路徑、文件總數與模型預設參數。 |

## 5. 功能與驗證對比 (Ground Truth Verification)

為驗證 RAG 機制有效性，系統支援並通過以下兩類關鍵驗證：

| 測試類型 | 範例 Prompt | 無 RAG 回應表現 (No RAG) | 有 RAG 回應表現 (With RAG) |
|---|---|---|---|
| **特殊 Token / 學號** | `112590013` | 模型無法得知該 Token，產生幻覺或回答未知。 | **精確引述**：列出該學號出現的文件 ID (`clueweb09-...`)，並依據上下文正確回答。 |
| **事實與新聞主題** | `United States government` | 僅依據模型預訓練知識回答泛泛內容。 | **特定引述**：提取 ClueWeb09 資料集中相關新聞與網頁內文，並引述文件來源。 |

### Context 視窗控制機制
- 針對 WARC 檔案中的長篇文檔，`DocStore` 與 `RagLLM.py` 會自動過濾 HTML 標籤並擷取前 800 字之純文字片段。
- 在確保語意完整的同時，防止 Prompt 過大超出 LLM 的 Context Window 限制，並提升本地端 LLM 的推理生成速度。

## 6. 注意事項

- **Ollama 服務連線**：執行前請確認 Ollama 服務已於背景啟動（預設連接埠 `http://localhost:11434`），且已預先下載 `llama3.2` 模型。
- **WARC 檔案權限與路徑**：若找不到 WARC 檔案，系統仍可進行搜尋與 RAG 生成，但僅能提供 Document ID 及檢索分數作為 Context，無法提供全文內容。
- **Tokenizer 一致性**：Retriever 端之切詞與 Porter Stemming 完全沿用 HW1/HW2 之標準鏈，確保高精準度之文件召回率。