import difflib
import math
import os
import re
# 直接從同資料夾的 config.py 引入設定
from config import INDEX_FILE_PATH, TOTAL_DOCS
from analyzer import analyze

inverted_index = {} # term -> { "df": int, "postings": { docID: tf } }
doc_lengths = {}    # docID -> float (向量長度)
terms_by_length = {} # term length -> indexed terms

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
            terms_by_length.setdefault(len(term), []).append(term)

    # 將所有平方和開根號，完成向量長度計算
    for doc_id in doc_lengths:
        doc_lengths[doc_id] = math.sqrt(doc_lengths[doc_id])
    print("索引載入完成！")

def _spelling_distance(first, second):
    rows = len(first) + 1
    columns = len(second) + 1
    distances = [[0] * columns for _ in range(rows)]
    for row in range(rows):
        distances[row][0] = row
    for column in range(columns):
        distances[0][column] = column

    for row in range(1, rows):
        for column in range(1, columns):
            cost = 0 if first[row - 1] == second[column - 1] else 1
            distances[row][column] = min(
                distances[row - 1][column] + 1,
                distances[row][column - 1] + 1,
                distances[row - 1][column - 1] + cost,
            )
            if (
                row > 1
                and column > 1
                and first[row - 1] == second[column - 2]
                and first[row - 2] == second[column - 1]
            ):
                distances[row][column] = min(
                    distances[row][column],
                    distances[row - 2][column - 2] + 1,
                )
    return distances[-1][-1]

def suggest_spelling_corrections(query_terms):
    suggestions = {}
    for term in query_terms:
        if term in inverted_index or len(term) < 4 or not term.isalpha():
            continue

        candidates = [
            candidate
            for length in range(max(4, len(term) - 1), len(term) + 2)
            for candidate in terms_by_length.get(length, ())
            if candidate.isalpha()
        ]
        matches = difflib.get_close_matches(term, candidates, n=20, cutoff=0.7)
        max_distance = 1 if len(term) < 8 else 2
        ranked_matches = [
            (distance, -inverted_index[candidate]["df"], candidate)
            for candidate in matches
            if (distance := _spelling_distance(term, candidate)) <= max_distance
        ]
        ranked_matches.sort()
        matches = [candidate for _, _, candidate in ranked_matches[:3]]
        if matches:
            suggestions[term] = matches
    return suggestions

def parse_boolean_query(query):
    tokens = re.findall(r"\(|\)|[^\s()]+", query.lower())
    if not any(token in {"and", "or", "(", ")"} for token in tokens):
        return None

    position = 0

    def parse_primary():
        nonlocal position
        if position >= len(tokens):
            raise ValueError("布林查詢缺少搜尋詞。")

        token = tokens[position]
        if token == "(":
            position += 1
            expression = parse_or()
            if position >= len(tokens) or tokens[position] != ")":
                raise ValueError("布林查詢括號不匹配。")
            position += 1
            return expression
        if token in {"and", "or", ")"}:
            raise ValueError(f"布林運算子或括號位置錯誤：{token}")

        position += 1
        # 與 HW1 索引相同的分析鏈：切詞/小寫/停用詞/詞幹；停用詞回傳 None，多詞 (如 non-profit) 視為 AND
        expression = None
        for term in analyze(token):
            expression = combine("and", expression, term)
        return expression

    def combine(operator, left, right):
        # None 代表被停用詞移除的項，不影響另一邊
        if left is None:
            return right
        if right is None:
            return left
        return (operator, left, right)

    def parse_and():
        nonlocal position
        expression = parse_primary()
        while position < len(tokens) and tokens[position] not in {"or", ")"}:
            if tokens[position] == "and":
                position += 1
            expression = combine("and", expression, parse_primary())
        return expression

    def parse_or():
        nonlocal position
        expression = parse_and()
        while position < len(tokens) and tokens[position] == "or":
            position += 1
            expression = combine("or", expression, parse_and())
        return expression

    expression = parse_or()
    if position != len(tokens):
        raise ValueError(f"布林查詢語法錯誤：{tokens[position]}")
    if expression is None:
        raise ValueError("布林查詢只含停用詞，沒有可搜尋的詞。")
    return expression

def get_boolean_terms(expression):
    if isinstance(expression, str):
        return [expression]
    return get_boolean_terms(expression[1]) + get_boolean_terms(expression[2])

def replace_boolean_terms(expression, suggestions):
    if isinstance(expression, str):
        return suggestions.get(expression, [expression])[0]
    operator, left, right = expression
    return (
        operator,
        replace_boolean_terms(left, suggestions),
        replace_boolean_terms(right, suggestions),
    )

def evaluate_boolean_query(expression):
    if isinstance(expression, str):
        return set(inverted_index.get(expression, {}).get("postings", {}))

    operator, left, right = expression
    left_docs = evaluate_boolean_query(left)
    right_docs = evaluate_boolean_query(right)
    if operator == "and":
        return left_docs & right_docs
    return left_docs | right_docs

def calculate_cosine_similarity(query_terms, allowed_doc_ids=None):
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
        if allowed_doc_ids is not None and doc_id not in allowed_doc_ids:
            continue
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
            
        # 查詢前處理與 HW1 索引一致 (StandardTokenizer -> 小寫 -> 停用詞 -> Porter 詞幹)
        query_terms = analyze(query)
        try:
            boolean_expression = parse_boolean_query(query)
        except ValueError as error:
            print(f"布林查詢格式錯誤：{error}")
            continue
        if boolean_expression is not None:
            query_terms = get_boolean_terms(boolean_expression)

        if not query_terms:
            print("查詢只含停用詞或符號，沒有可搜尋的詞。")
            continue

        spelling_suggestions = suggest_spelling_corrections(query_terms)
        if spelling_suggestions:
            print("拼字建議：")
            for term, matches in spelling_suggestions.items():
                print(f"  {term} -> {', '.join(matches)}")
            use_suggestions = input("使用以上第一個建議替換查詢詞嗎？(y/N) ").strip().lower()
            if use_suggestions == "y":
                if boolean_expression is None:
                    query_terms = [
                        spelling_suggestions[term][0] if term in spelling_suggestions else term
                        for term in query_terms
                    ]
                else:
                    boolean_expression = replace_boolean_terms(boolean_expression, spelling_suggestions)
                    query_terms = get_boolean_terms(boolean_expression)
        
        allowed_doc_ids = (
            evaluate_boolean_query(boolean_expression)
            if boolean_expression is not None
            else None
        )
        results = calculate_cosine_similarity(query_terms, allowed_doc_ids)
        
        if not results:
            print("找不到符合的搜尋結果。")
            continue
            
        print("Ranked Search Results:")
        print("<doc#> \t\t <similarity score>")
        for rank, (doc_id, score) in enumerate(results[:10]): 
            print(f"{doc_id} \t {score:.6f}")