import requests
import json
from config import (ENABLE_CASE_FOLDING, ENABLE_STOPWORD_REMOVAL, ENABLE_STEMMING,
                    SOLR_BASE_URL, STOPWORD_FILE)

schema_url = f"{SOLR_BASE_URL}/schema"
headers = {"Content-type": "application/json"}

# filter 依開關疊加，順序固定：轉小寫 → 停用詞 → 詞幹
filters = []
print("正在根據 config.py 設定 Schema...")

if ENABLE_CASE_FOLDING:
    filters.append({"class": "solr.LowerCaseFilterFactory"})
    print(" [+] 已啟用：大小寫轉換 (Case folding)")

if ENABLE_STOPWORD_REMOVAL:
    filters.append({"class": "solr.StopFilterFactory", "ignoreCase": "true", "words": STOPWORD_FILE})
    print(" [+] 已啟用：停用詞移除 (Stopword removal)")

if ENABLE_STEMMING:
    filters.append({"class": "solr.PorterStemFilterFactory"})
    print(" [+] 已啟用：詞幹提取 (Stemming)")

if not filters:
    print(" [-] 未啟用任何加分功能，僅使用基礎切詞。")

# StandardTokenizer 會切掉標點；Whitespace 只切空白，標點會黏在詞上
field_type = {
    "name": "custom_text_type",
    "class": "solr.TextField",
    "positionIncrementGap": "100",
    "analyzer": {
        "tokenizer": {"class": "solr.StandardTokenizerFactory"},
        "filters": filters,
    },
}
field = {
    "name": "content",
    "type": "custom_text_type",
    "indexed": True,
    "stored": False,        # 原文不用存，省空間
    "termVectors": True,
    "termPositions": True,
}

# 類型已存在就用 replace，否則 add，這樣可以重複執行
types = requests.get(f"{schema_url}/fieldtypes").json().get("fieldTypes", [])
type_op = "replace-field-type" if any(t["name"] == field_type["name"] for t in types) else "add-field-type"

response = requests.post(schema_url, data=json.dumps({type_op: field_type, "replace-field": field}), headers=headers)

if response.status_code == 200:
    print("Schema 更新成功！請執行 IndexWarc.py 重新匯入資料以套用新設定。")
else:
    print("Schema 更新失敗：", response.text)
