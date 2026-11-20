# 介面約定

各模組依此格式實作，C 整合時直接 import 呼叫。函式的參數或回傳格式要改的話，先在群組說一聲，確認不影響別人再改，並同步更新本檔。

## 共通規則

- **doc ID 一律是字串**（例如 `"123"`），和 `Search.py` 現有的 `inverted_index` 一致。
- **詞一律是經過 `analyzer.analyze()` 處理後的詞**（小寫、去停用詞、Porter stemming），不是原始字串。
- **分數越高越相關**，排序結果一律依分數由高到低。
- 程式放在 `hw2/SourceCode/`，可以直接 `import Search`、`from analyzer import analyze`，索引用 `Search.load_index()` 載入的那一份，不要自己再讀一次 `HW1.txt`。

## 檔案分配

| 模組 | 負責人 | 檔案 |
|---|---|---|
| 相關回饋與查詢擴展 | A | `feedback.py` |
| 分群與視覺化 | B | `clustering.py` |
| 語意檢索 | C | `semantic.py` |
| 評估與語言模型 | D | `evaluate.py`、`lm.py` |

只改自己的檔案。共用檔案的規則見最下方。

## 函式

### A：`feedback.py`

```python
def rocchio(query_vec: dict[str, float],
            rel_ids: list[str],
            nonrel_ids: list[str],
            alpha=1.0, beta=0.75, gamma=0.15) -> dict[str, float]:
    """回傳新的查詢向量 {詞: 權重}，負權重的詞要拿掉。"""

def expand_terms(query: str, top_ids: list[str], m=5) -> list[tuple[str, float]]:
    """回傳建議擴展詞 [(詞, 分數)]，分數高到低，最多 m 個，不含原查詢已有的詞。"""
```

### B：`clustering.py`

```python
def cluster(doc_ids: list[str]) -> list[dict]:
    """回傳 [{"label": str, "doc_ids": list[str]}]。
    label 是群中心權重最高的 3 個詞，用空白隔開，例如 "java island indonesia"。"""

def project_2d(doc_ids: list[str]) -> list[tuple[str, float, float, int]]:
    """回傳 [(doc_id, x, y, 群編號)]，群編號對應 cluster() 回傳清單的索引。"""
```

### C：`semantic.py`

```python
def semantic_search(query: str, k=10) -> list[tuple[str, float]]:
    """query 是原始查詢字串（不經 analyzer）。回傳 [(doc_id, cosine 分數)]。"""
```

### D：`evaluate.py`

```python
def evaluate(run: dict[str, list[str]],
             qrels: dict[str, dict[str, int]]) -> dict[str, float]:
    """run: {查詢編號: [doc_id, ...]}（已排序）
    qrels: {查詢編號: {doc_id: 相關程度}}，相關程度 0／1 或 0／1／2，沒標註的視為 0
    回傳 {"P@10": ..., "MAP": ..., "nDCG@10": ...}，為所有查詢的平均。"""
```

qrels 檔格式（TREC 格式，空白隔開）：

```
查詢編號 0 doc_id 相關程度
```

## 共用檔案

| 檔案 | 規則 |
|---|---|
| `Search.py` | 只能**新增**函式，不改既有函式的輸入、輸出與行為 |
| `Search.get_doc_vector(doc_id) -> dict[str, float]` | **由 A 實作**（TF-IDF 權重 `(1+log tf)·idf`），B 也用這一個，不要另寫 |
| `WebApp.py` | **只由 C 修改**。B 的前端畫面交 HTML/JS 片段或資料，由 C 接進網頁 |
| `requirements.txt` | 新增套件時自己加一行 |
| `config.py` | 新參數加在檔案最後，標註是哪個模組用的 |

## 分支

- 分支名稱：A `feature/relevance-feedback`、B `feature/clustering`、C `feature/semantic-search`、D `feature/evaluation`
- 不直接推 main。完成一項就推自己的分支並發 PR，由 C 合併。
- 開始工作前先 `git merge main`，拿到別人已合併的東西（例如 `get_doc_vector`）。
