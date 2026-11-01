import math
import os
# 直接從同資料夾的 config.py 引入設定
from config import INDEX_FILE_PATH, TOTAL_DOCS

inverted_index = {} # term -> { "df": int, "postings": { docID: tf } }
doc_lengths = {}    # docID -> float (向量長度)

def load_index():
    if not os.path.exists(INDEX_FILE_PATH):
        print(f"[錯誤] 找不到索引檔：{INDEX_FILE_PATH}")
        print("請確認是否已將 HW1.txt 複製到 hw2 資料夾下！")
        exit(1)
        
    print(f"正在載入倒排索引: {INDEX_FILE_PATH} ...")
    with open(INDEX_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            # 解析 HW1.txt 格式: "term, df: <docID, tf: <pos...>; ...>"
            head, _, rest = line.rstrip("\n").partition(": <")
            term, _, df_str = head.rpartition(", ")
            df = int(df_str)
            
            postings_dict = {}
            for p in rest[:-1].split("; "):
                if not p: continue
                doc_part, _, _ = p.partition(": <")
                doc_id, tf_str = doc_part.split(", ")
                tf = int(tf_str)
                postings_dict[doc_id] = tf
                
                # 計算文件向量長度 (平方和)
                # 權重公式: wij = (1 + log10(tfij)) * log10(N/dfi)
                weight = (1 + math.log10(tf)) * math.log10(TOTAL_DOCS / df)
                doc_lengths[doc_id] = doc_lengths.get(doc_id, 0.0) + (weight ** 2)

            inverted_index[term] = {"df": df, "postings": postings_dict}

    # 將所有平方和開根號，完成向量長度計算
    for doc_id in doc_lengths:
        doc_lengths[doc_id] = math.sqrt(doc_lengths[doc_id])
    print("索引載入完成！")

def calculate_cosine_similarity(query_terms):
    scores = {}
    query_weights = {}
    
    # 計算 Query 向量權重: log(N/df)
    for term in query_terms:
        if term in inverted_index:
            df = inverted_index[term]["df"]
            query_weights[term] = math.log10(TOTAL_DOCS / df)
    
    query_length = math.sqrt(sum(w**2 for w in query_weights.values()))
    if query_length == 0:
        return []

    # 計算內積 (Dot Product)
    for term, q_weight in query_weights.items():
        postings = inverted_index[term]["postings"]
        df = inverted_index[term]["df"]
        for doc_id, tf in postings.items():
            d_weight = (1 + math.log10(tf)) * math.log10(TOTAL_DOCS / df)
            scores[doc_id] = scores.get(doc_id, 0.0) + (q_weight * d_weight)

    # 計算 Cosine Similarity (內積 / 兩向量長度相乘)
    results = []
    for doc_id, dot_product in scores.items():
        sim_score = dot_product / (query_length * doc_lengths[doc_id])
        results.append((doc_id, sim_score))

    # 依相似度分數降冪排序
    results.sort(key=lambda x: x[1], reverse=True)
    return results

if __name__ == "__main__":
    load_index()
    print("==================================================")
    print(" 歡迎使用 IR Homework 2: 查詢處理與搜尋系統")
    print(" 輸入 'exit' 離開程式")
    print("==================================================")
    
    while True:
        query = input("\ncmd> ")
        if query.lower() == "exit": 
            break
        if not query.strip():
            continue
            
        # TODO: 未來在此處實作呼叫 Solr Analysis API 進行查詢前處理 (Stemming/Stopwords)
        # 目前先以簡單轉小寫與空白切割處理
        query_terms = query.lower().split()
        
        results = calculate_cosine_similarity(query_terms)
        
        if not results:
            print("找不到符合的搜尋結果。")
            continue
            
        print("Ranked Search Results:")
        print("<doc#> \t\t <similarity score>")
        for rank, (doc_id, score) in enumerate(results[:10]): 
            print(f"{doc_id} \t {score:.6f}")