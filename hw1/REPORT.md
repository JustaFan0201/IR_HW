# HW1 設計說明與實測數據

環境建置與執行步驟請見 [README.md](README.md)。本文件說明作法、預處理規則，以及以 `02.warc`（ClueWeb09，1 GB，36,053 個網頁）實測的結果。

---

## 1. 作法概述

用 **Apache Solr** 幫忙斷詞、建倒排索引，再用 Python 取出結果，轉成作業指定的格式。

```
WARC 檔 → 取出 HTML 並轉成純文字 → 送進 Solr → Solr 斷詞並建索引 → 取出 term vector → 輸出詞典檔與索引檔
         (IndexWarc.py)                                              (ExportIndex.py)
```

**輸出格式**：

```
download, 5893: <clueweb09-en0000-02-00000, 3: <8, 28, 88>; clueweb09-en0000-02-00002, 1: <13>; ...>
```

詞 `download` 出現在 5,893 篇文件；第一篇的 tf 是 3，位置是 8、28、88。
輸出兩個檔案：`HW1_dictionary.txt`（排序後的詞典，一行一個詞）、`HW1.txt`（postings）。

---

## 2. 功能特色

### 2.1 語言處理可開關（`config.py`）

| 開關 | 作用 |
|---|---|
| `ENABLE_CASE_FOLDING` | 全部轉小寫 |
| `ENABLE_STOPWORD_REMOVAL` | 移除 35 個英文停用詞 |
| `ENABLE_STEMMING` | Porter 詞幹還原（`cats`→`cat`、`running`→`run`） |

改完開關後，執行 `SetupSchema.py` 套用設定，再重新匯入。

### 2.2 全關 vs 全開的實測對照

| | 全部關閉 | 全部開啟 | 說明 |
|---|---|---|---|
| 不同的詞數 | 669,100 | 502,131 | 少約 25% |
| 索引檔大小 | 566 MB | 457 MB | |
| 詞典檔大小 | 7.3 MB | 5.6 MB | |
| `the` 的 df | 30,840 | 13 | 停用詞被移除 |
| `The` 與 `the` | 分開算（23,744 與 30,840） | 合併 | case folding |
| `download` 的 df | 2,044 | 5,893 | `downloads` 等詞形被併入 |

### 2.3 其他

- **可處理完整的 1 GB 檔案**：依 WARC 標頭的 `Content-Length` 逐筆讀取，不會一次載入整個檔案。
- **文件 ID 使用標準的 `WARC-TREC-ID`**（例如 `clueweb09-en0000-02-00000`）。
- **匯入會統計失敗篇數**：這次匯入 35,011 篇、失敗 0 篇。
- 輸出依文件 ID 排序，每個詞的 postings 依文件順序排列。

---

## 3. 預處理方式

**HTML 轉文字**：用 BeautifulSoup 去掉標籤，並移除 `script`、`style`、`meta`、`noscript` 的內容。
36,053 個網頁中，有 1,042 篇去掉標籤後內容為空而略過，實際匯入 **35,011 篇**。

**斷詞**：使用 Solr 的 StandardTokenizer（Unicode 標準的斷詞規則）。實測結果：

| 類型 | 輸入 | 切出的詞 |
|---|---|---|
| 標點符號 | `cats, running!` | `cats`、`running`（標點被丟掉） |
| 連字號 | `State-of-the-art` | `State`、`of`、`the`、`art`（切開） |
| 日期 | `2005-09-12` | `2005`、`09`、`12`（切開） |
| 一般數字 | `2005` | `2005`（保留為詞） |
| 小數、千分位 | `3.14`、`1,000` | 整個保留 |
| 縮寫 | `don't` | `don't`（整個保留） |
| 網址、網域 | `www.amazon.de` | 整個保留 |
| 底線 | `user_id` | 整個保留 |
| Email | `E-mail` | `E`、`mail`（切開） |

**位置（positions）**：從 0 開始計算。移除停用詞時**不會重新編號**，會留下空位（例如 `state of the art` 移除停用詞後，`art` 的位置仍是原本的位置）。

**停用詞表**：Solr 內建的 `lang/stopwords_en.txt`，共 35 個詞。

---

## 4. 遇到的困難與解法

1. **WARC 解析：HTTP 標頭被當成內文。** 原本逐行猜測 HTML 的起點，容易出錯，也漏掉檔案最後一篇。改為依 `Content-Length` 讀取每筆記錄，並確認整份檔案 36,054 筆記錄全部對得上。
2. **停用詞設定沒有生效。** Solr 預設的 `stopwords.txt` 其實是空的，開了停用詞功能也不會移除任何詞。改用有內容的 `lang/stopwords_en.txt`。
3. **斷詞器選擇。** 原本用 WhitespaceTokenizer，標點會黏在詞上（`Google,` 與 `Google` 被當成不同的詞），改用 StandardTokenizer。我們也試過用正規式事先清掉所有標點，實測前 3,000 篇：清洗後有 18,607 個詞消失，其中約 81% 是 `42.37`、`www.amazon.de` 這類小數、網域，約 17% 是帶重音或非英文的字，且會把 `maría` 切成 `mar`、`a`，產生不存在的假詞，所以最後拿掉，標點交給 Solr 處理。
4. **詞幹還原後，少數詞又變回停用詞。** 處理順序是「轉小寫 → 去停用詞 → 詞幹還原」，所以 `its` 還原成 `it`、`ones` 還原成 `on` 之後，停用詞過濾已經做完。全開的詞典中共有 28 個這樣的詞，只占 postings 的 0.3%。這與 Lucene 英文分析器的順序相同，因此保留。
5. **Solr 預設記憶體只有 512 MB**，匯入 1 GB 資料前需調高（見 README）。

---

## 5. Skip pointer（選做）

`SkipPointer.py build` 另外輸出 `HW1_skip.txt`：df 至少 16 的詞，每隔 √df 筆放一個 skip pointer（標準輸出 `HW1.txt` 不變）。
`SkipPointer.py query 詞1 詞2` 做 AND 查詢，比較有無 skip 的比對次數。實測：

| 查詢 | 一般合併 | 有 skip | 減少 |
|---|---|---|---|
| `it` AND `firefox`（8,085 篇 對 694 篇） | 8,524 | 5,552 | 34.9% |
| `download` AND `linux`（5,893 篇 對 1,029 篇） | 6,447 | 4,715 | 26.9% |
| `download` AND `free`（5,893 篇 對 12,014 篇） | 15,714 | 13,397 | 14.7% |
| `on` AND `be`（13,922 篇 對 6,271 篇） | 15,532 | 15,630 | -0.6% |

兩個清單長度差越多，skip 越有效；長度接近時幾乎沒差，甚至略多（跳躍的檢查也算一次比對）。

---

## 6. 使用的開源工具

- Apache Solr 9.11.0（基於 Apache Lucene）：<https://solr.apache.org/>
- Python 套件 `requests`（呼叫 Solr 的 HTTP API）、`beautifulsoup4`（解析 HTML）
