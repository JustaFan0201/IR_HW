import requests
from config import SOLR_BASE_URL, BATCH_SIZE, OUTPUT_FILE_PATH, DICTIONARY_FILE_PATH

url = f"{SOLR_BASE_URL}/tvrh"

# term -> [df, [每篇文件的 postings 字串]]；直接存成字串比存 tuple 省記憶體
index = {}
start = 0
total = None

print("開始從 Solr 提取 Term Vectors 並轉換格式...")

while total is None or start < total:
    params = {
        "q": "*:*", "fl": "id", "sort": "id asc",  # 依 id 排序，postings 才會依文件順序
        "tv": "true", "tv.fl": "content", "tv.tf": "true", "tv.positions": "true",
        "rows": BATCH_SIZE, "start": start, "wt": "json",
    }
    resp = requests.get(url, params=params).json()
    total = resp["response"]["numFound"]
    tv = resp.get("termVectors", [])

    # termVectors 是 [key, value, key, value...] 的交錯陣列，略過 Solr 的中繼資料
    for i in range(0, len(tv), 2):
        doc_id, doc_data = tv[i], tv[i + 1]
        if doc_id in ("uniqueKeyFieldName", "warnings") or "content" not in doc_data:
            continue
        terms = doc_data[doc_data.index("content") + 1]

        for j in range(0, len(terms), 2):
            stats = dict(zip(terms[j + 1][::2], terms[j + 1][1::2]))
            positions = stats["positions"][1::2]  # ['position', 5, 'position', 9] -> [5, 9]
            entry = index.setdefault(terms[j], [0, []])
            entry[0] += 1
            entry[1].append(f"{doc_id}, {stats['tf']}: <{', '.join(map(str, positions))}>")

    start += BATCH_SIZE
    print(f"已處理 {min(start, total)} / {total} 篇")

print(f"共 {len(index)} 個不同的詞，正在寫入檔案 ...")

with open(DICTIONARY_FILE_PATH, "w", encoding="utf-8") as fd, open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as fi:
    for term in sorted(index):
        df, postings = index[term]
        fd.write(f"{term}\n")                                   # 詞典：排序後的詞，一行一個
        fi.write(f"{term}, {df}: <{'; '.join(postings)}>\n")    # term, df: <docID, tf: <pos...>; ...>

print(f"完成！\n詞典：{DICTIONARY_FILE_PATH}\n索引：{OUTPUT_FILE_PATH}")
