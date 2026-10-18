import requests
import json
from config import SOLR_BASE_URL

headers = {"Content-type": "application/json"}
print("開始初始化 Solr 核心設定...")

print("\n[1/2] 正在建立 'content' 欄位與詞向量設定...")
schema_url = f"{SOLR_BASE_URL}/schema"
schema_payload = {
    "add-field": {
        "name": "content",
        "type": "text_general", 
        "indexed": True,
        "stored": True,
        "termVectors": True,    
        "termPositions": True   
    }
}
schema_response = requests.post(schema_url, data=json.dumps(schema_payload), headers=headers)
if schema_response.status_code == 200:
    print(" -> Schema 欄位設定成功！")
else:
    print(" -> Schema 設定失敗 (可能欄位已存在)：", schema_response.text)

print("\n[2/2] 正在開啟 Term Vector 專屬查詢通道 (/tvrh)...")
config_url = f"{SOLR_BASE_URL}/config"
config_payload = {
    "add-searchcomponent": {
        "name": "tvComponent",
        "class": "solr.TermVectorComponent"
    },
    "add-requesthandler": {
        "name": "/tvrh",
        "class": "solr.SearchHandler",
        "defaults": { "tv": "true" },
        "last-components": ["tvComponent"]
    }
}
config_response = requests.post(config_url, data=json.dumps(config_payload), headers=headers)
if config_response.status_code == 200:
    print(" -> 成功開啟 Term Vector 查詢通道！")
else:
    print(" -> 通道設定失敗 (可能通道已存在)：", config_response.text)

print("\n初始化作業完成！")