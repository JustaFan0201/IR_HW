import os

# 檔案路徑設定
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

# 輸入的 WARC 檔案設定
WARC_FILE_NAME = "02.warc"
WARC_FILE_PATH = os.path.join(BASE_DIR, WARC_FILE_NAME)

# 輸出的倒排索引檔案設定
OUTPUT_FILE_NAME = "HW1.txt"
OUTPUT_FILE_PATH = os.path.join(BASE_DIR, OUTPUT_FILE_NAME)

DICTIONARY_FILE_PATH = os.path.join(BASE_DIR, "HW1_dictionary.txt")

# 附加 skip pointer 的索引 (選做加分項目，不影響上面的標準輸出)
SKIP_FILE_PATH = os.path.join(BASE_DIR, "HW1_skip.txt")
SKIP_MIN_DF = 16  # postings 太短的詞不放 skip pointer

# 停用詞表 (Solr core 的 conf/ 底下，內含 35 個英文停用詞)
STOPWORD_FILE = "lang/stopwords_en.txt"

# 決定是否開啟「大小寫轉換」 (Case folding)
ENABLE_CASE_FOLDING = True

# 決定是否開啟「停用詞移除」 (Stopword removal)
ENABLE_STOPWORD_REMOVAL = True

# 決定是否開啟「詞幹提取」 (Stemming/Lemmatization)
ENABLE_STEMMING = True

# Solr 伺服器的 API 網址
SOLR_BASE_URL = "http://localhost:8983/solr/hw1"

# 批次處理的大小
BATCH_SIZE = 500