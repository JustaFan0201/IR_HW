import os

# 取得目前 config.py 所在的目錄 (SourceCode)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 往上一層推，得到專案根目錄 (hw2)
BASE_DIR = os.path.dirname(CURRENT_DIR)

# 設定你的倒排索引檔名稱 (需確保該檔案已放在 hw2 根目錄下)
INDEX_FILE_NAME = "HW1.txt"

# 組合出完整的索引檔絕對路徑 (hw2/HW1.txt)
INDEX_FILE_PATH = os.path.join(BASE_DIR, INDEX_FILE_NAME)

# 總文件數 (N) - 用於計算 IDF: log(N/df)
# 請填寫你在 HW1 實際成功匯入的總文件數量 (例如 10000 篇)
TOTAL_DOCS = 35011
# 預設顯示/輸出前幾名 (可用命令列 --top N 覆蓋)
TOP_K = 10

# 批次模式 (--queries) 的預設輸出檔 (hw2/HW2.txt)
OUTPUT_FILE_NAME = "HW2.txt"
OUTPUT_FILE_PATH = os.path.join(BASE_DIR, OUTPUT_FILE_NAME)

# 網頁介面 (WebApp.py) 顯示摘要與全文用的 HW1 WARC 檔；找不到時網頁仍可搜尋，只是沒有摘要
WARC_FILE_PATH = os.path.join(os.path.dirname(BASE_DIR), "hw1", "02.warc")

# 預設權重/排序方案 (可用命令列 --weighting 覆蓋)：
#   tfidf     : 作業指定公式 (1 + log tf) * log(N/df)，cosine similarity
#   tfidf-raw : 原始 tf * log(N/df)，cosine similarity
#   bm25      : Okapi BM25 (不做 cosine 正規化，分數不在 0~1 之間)
DEFAULT_WEIGHTING = "tfidf"

# BM25 參數
BM25_K1 = 1.2
BM25_B = 0.75

# 萬用字元 (*) 展開後最多保留幾個索引詞 (取 df 最高者)，避免 a* 這類查詢展開成數萬個詞
WILDCARD_MAX_TERMS = 50
