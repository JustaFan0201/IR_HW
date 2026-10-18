import requests
import json
import re
from bs4 import BeautifulSoup
from config import WARC_FILE_PATH, SOLR_BASE_URL, BATCH_SIZE

warc_file = WARC_FILE_PATH
solr_update_url = f"{SOLR_BASE_URL}/update/json/docs?commit=true"
headers = {'Content-type': 'application/json'}

print("正在清空 Solr 舊有資料，確保索引乾淨...")
delete_url = f"{SOLR_BASE_URL}/update?commit=true"
delete_payload = {"delete": {"query": "*:*"}}
requests.post(delete_url, json=delete_payload, headers=headers)
print("舊資料已清空！")

batch_size = BATCH_SIZE
docs_batch = []
doc_count = 0

print(f"開始使用掃描解析並匯入資料: {warc_file} ...")

# 準備用來抓取文件 ID 的正規表達式
id_pattern = re.compile(rb'WARC-Record-ID:\s*<([^>]+)>')

with open(warc_file, 'rb') as f:
    current_id = None
    html_buffer = []
    is_recording_html = False
    
    for line in f:
        # 1. 抓取這篇網頁的 ID
        if line.startswith(b'WARC-Record-ID:'):
            match = id_pattern.search(line)
            if match:
                current_id = match.group(1).decode('utf-8', errors='ignore')
        
        # 2. 如果遇到下一篇文件的開頭宣告，代表上一篇的 HTML 已經結束了，準備送出
        if line.startswith(b'WARC/0.') or line.startswith(b'WARC/1.'):
            if current_id and html_buffer:
                try:
                    # 將收集到的 HTML 行組合起來交給 BeautifulSoup 清理
                    raw_html = b''.join(html_buffer)
                    soup = BeautifulSoup(raw_html, 'html.parser')
                    text_content = soup.get_text(separator=' ', strip=True)
                    
                    if text_content:
                        docs_batch.append({
                            "id": current_id,
                            "content": text_content
                        })
                        doc_count += 1
                        
                        # 滿 500 筆送出一次
                        if len(docs_batch) >= batch_size:
                            requests.post(solr_update_url, data=json.dumps(docs_batch), headers=headers)
                            print(f"已成功匯入 {doc_count} 筆文件...")
                            docs_batch = []
                except Exception:
                    pass # 遇到極端亂碼直接忽略
            
            # 清空狀態，迎接新的一篇網頁
            current_id = None
            html_buffer = []
            is_recording_html = False
            continue

        # 3. 簡單判斷 HTML 的起始點 (避開上方的 HTTP Header)
        if not is_recording_html and (b'<html' in line.lower() or b'<!doctype' in line.lower() or b'<body' in line.lower()):
            is_recording_html = True
            
        # 4. 把網頁內容裝進緩衝區
        if is_recording_html:
            html_buffer.append(line)

# 處理檔案結尾剩下的尾數資料
if docs_batch:
    requests.post(solr_update_url, data=json.dumps(docs_batch), headers=headers)
    print(f"已成功匯入 {doc_count} 筆文件...")

print(f"所有資料匯入完成！總共成功匯入 {doc_count} 篇網頁。")