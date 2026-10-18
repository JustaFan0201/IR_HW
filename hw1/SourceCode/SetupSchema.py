import requests
import json
from config import ENABLE_CASE_FOLDING, ENABLE_STOPWORD_REMOVAL, ENABLE_STEMMING, SOLR_BASE_URL

filters = []
print("正在根據 config.py 設定 Schema...")

if ENABLE_CASE_FOLDING:
    filters.append({"class": "solr.LowerCaseFilterFactory"})
    print(" [+] 已啟用：大小寫轉換 (Case folding)")
    
if ENABLE_STOPWORD_REMOVAL:
    filters.append({"class": "solr.StopFilterFactory", "ignoreCase": "true", "words": "stopwords.txt"})
    print(" [+] 已啟用：停用詞移除 (Stopword removal)")
    
if ENABLE_STEMMING:
    filters.append({"class": "solr.PorterStemFilterFactory"})
    print(" [+] 已啟用：詞幹提取 (Stemming)")

if not filters:
    print(" [-] 未啟用任何加分功能，僅使用基礎切詞。")

payload = {
    "add-field-type": {
        "name": "custom_text_type",
        "class": "solr.TextField",
        "analyzer": {
            "tokenizer": {
                "class": "solr.WhitespaceTokenizerFactory" 
            },
            "filters": filters  
        }
    },
    "replace-field": {
        "name": "content",
        "type": "custom_text_type",
        "indexed": True,
        "stored": True,
        "termVectors": True,
        "termPositions": True
    }
}

url = f"{SOLR_BASE_URL}/schema"
headers = {"Content-type": "application/json"}
response = requests.post(url, data=json.dumps(payload), headers=headers)

if response.status_code == 200:
    print("Schema 更新成功！請執行 IndexWarc.py 重新匯入資料以套用新設定。")
else:
    print("Schema 更新失敗：", response.text)