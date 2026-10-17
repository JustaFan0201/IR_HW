import requests
import json

# 透過 Config API 幫 hw1 核心新增 TermVector 查詢通道
url = "http://localhost:8983/solr/hw1/config"
payload = {
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

headers = {"Content-type": "application/json"}
response = requests.post(url, data=json.dumps(payload), headers=headers)

if response.status_code == 200:
    print("成功開啟 Term Vector 專屬查詢通道 (/tvrh)！")
else:
    print("設定失敗，請確認 Solr 狀態：", response.text)