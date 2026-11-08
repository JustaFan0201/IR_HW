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
