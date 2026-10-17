import requests
import json

core_name = "hw1"
schema_url = f"http://localhost:8983/solr/{core_name}/schema"

payload = {
    "add-field": {
        "name": "content",
        "type": "text_general", # 使用預設型態，內建基本分詞與大小寫轉換
        "indexed": True,
        "stored": True,
        "termVectors": True,    # 紀錄詞向量
        "termPositions": True   # 紀錄精確位置
    }
}

headers = {"Content-type": "application/json"}
response = requests.post(schema_url, data=json.dumps(payload), headers=headers)

if response.status_code == 200:
    print("Schema 設定成功！")
else:
    print("設定失敗：", response.text)