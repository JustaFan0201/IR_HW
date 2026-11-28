import os

# 取得目前 config.py 所在的目錄 (SourceCode)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 往上一層推，得到專案根目錄 (hw3)
BASE_DIR = os.path.dirname(CURRENT_DIR)

# 倒排索引檔名稱：由 EmbedTokens.py 從 hw1/HW1.txt 嵌入組員學號後產生於 hw3 根目錄
INDEX_FILE_NAME = "HW1.txt"

# 組合出完整的索引檔絕對路徑 (hw3/HW1.txt)
INDEX_FILE_PATH = os.path.join(BASE_DIR, INDEX_FILE_NAME)

# 總文件數 (N) - 用於計算 IDF: log(N/df)
# 請填寫你在 HW1 實際成功匯入的總文件數量 (例如 10000 篇)
TOTAL_DOCS = 35011
# 預設顯示/輸出前幾名 (可用命令列 --top N 覆蓋)
TOP_K = 10

# 批次模式 (--queries) 的預設輸出檔 (hw3/HW3.txt)
OUTPUT_FILE_NAME = "HW3.txt"
OUTPUT_FILE_PATH = os.path.join(BASE_DIR, OUTPUT_FILE_NAME)

# RAG 取文件內文用的 WARC 檔：由 EmbedTokens.py 從 hw1/02.warc 嵌入組員學號後產生 (hw3/02_hw3.warc)
# 找不到時仍可搜尋，只是沒有內文
WARC_FILE_PATH = os.path.join(BASE_DIR, "02_hw3.warc")

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

# 模型名稱
DEFAULT_MODEL = "llama3.2"
