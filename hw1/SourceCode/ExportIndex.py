import requests
import json
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(current_dir, f"HW1.txt")
solr_query_url = "http://localhost:8983/solr/hw1/tvrh"

inverted_index = {}
batch_size = 1000
start = 0

print("開始從 Solr 提取 Term Vectors 並轉換格式...")

while True:
    params = {
        "q": "*:*",
        "fl": "id",
        "tv": "true",
        "tv.fl": "content",
        "tv.tf": "true",
        "tv.positions": "true",
        "rows": batch_size,
        "start": start,
        "wt": "json"
    }
    
    response = requests.get(solr_query_url, params=params).json()
    docs = response.get('response', {}).get('docs', [])
    
    if not docs:
        break
        
    term_vectors = response.get('termVectors', [])
    
    # 解析 Solr 的交錯陣列結構
    for i in range(0, len(term_vectors), 2):
        doc_id = term_vectors[i]
        
        # 避開 Solr 系統回傳的 metadata (如 "uniqueKeyFieldName", "warnings")
        if doc_id == "uniqueKeyFieldName" or doc_id == "warnings":
            continue
            
        doc_data = term_vectors[i+1]
        
        try:
            content_idx = doc_data.index("content") + 1
            term_data = doc_data[content_idx]
        except ValueError:
            continue
            
        for j in range(0, len(term_data), 2):
            term = term_data[j]
            stats_list = term_data[j+1]
            
            tf = 0
            positions = []
            
            for k in range(len(stats_list)):
                if stats_list[k] == "tf":
                    tf = stats_list[k+1]
                elif stats_list[k] == "positions":
                    pos_data = stats_list[k+1]
                    positions = [p for p in pos_data if isinstance(p, (int, float))]
            
            if term not in inverted_index:
                inverted_index[term] = {"df": 0, "postings": []}
                
            inverted_index[term]["df"] += 1
            inverted_index[term]["postings"].append((doc_id, tf, positions))
            
    start += batch_size
    print(f"已處理 {start} 筆文件的索引資料...")

print("資料提取完畢，正在寫入 txt 檔案 (這可能會花一點時間，請耐心等候)...")

with open(output_file, "w", encoding="utf-8") as f:
    for term in sorted(inverted_index.keys()):
        df = inverted_index[term]["df"]
        postings = inverted_index[term]["postings"]
        
        postings_list = []
        for doc_id, tf, positions in postings:
            pos_str = ", ".join(map(str, positions))
            postings_list.append(f"{doc_id}, {tf}: <{pos_str}>")
            
        postings_str = "; ".join(postings_list)
        f.write(f"{term}, {df}: <{postings_str}>\n")

print(f"大功告成！檔案已儲存至：{output_file}")