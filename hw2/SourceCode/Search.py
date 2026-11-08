import argparse
import difflib
import math
import os
import re
# 直接從同資料夾的 config.py 引入設定
from config import (BM25_B, BM25_K1, DEFAULT_WEIGHTING, INDEX_FILE_PATH,
                    OUTPUT_FILE_PATH, TOP_K, TOTAL_DOCS)
from analyzer import analyze, analyze_positions

WEIGHTING_SCHEMES = ("tfidf", "tfidf-raw", "bm25")

inverted_index = {} # term -> { "df": int, "postings": { docID: tf } }
doc_lengths = {}    # docID -> float (tfidf 方案的文件向量長度)
doc_lengths_raw = {} # docID -> float (tfidf-raw 方案的文件向量長度)
doc_token_counts = {} # docID -> 文件在索引中的詞數 (BM25 的文件長度)
avg_doc_length = 0.0
terms_by_length = {} # term length -> indexed terms
term_offsets = {}   # term -> 該詞在索引檔中的位元組位置 (phrase/proximity 查詢時才回頭讀位置資訊)

def load_index():
    if not os.path.exists(INDEX_FILE_PATH):
        print(f"[錯誤] 找不到索引檔：{INDEX_FILE_PATH}")
        print("請確認是否已將 HW1.txt 複製到 hw2 資料夾下！")
        exit(1)

    print(f"正在載入倒排索引: {INDEX_FILE_PATH} ...")
    offset = 0
    # 以二進位讀取才能記錄每行的位元組位置 (文字模式的 tell() 在迭代時不可用)
    with open(INDEX_FILE_PATH, "rb") as f:
        for raw_line in f:
            line_offset = offset
            offset += len(raw_line)
            line = raw_line.decode("utf-8")
            # 解析 HW1.txt 格式: "term, df: <docID, tf: <pos...>; ...>"
            head, _, rest = line.rstrip("\r\n").partition(": <")
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
                idf = math.log10(TOTAL_DOCS / df)
                weight = (1 + math.log10(tf)) * idf
                doc_lengths[doc_id] = doc_lengths.get(doc_id, 0.0) + (weight ** 2)
                raw_weight = tf * idf  # tfidf-raw 方案
                doc_lengths_raw[doc_id] = doc_lengths_raw.get(doc_id, 0.0) + (raw_weight ** 2)
                doc_token_counts[doc_id] = doc_token_counts.get(doc_id, 0) + tf

            inverted_index[term] = {"df": df, "postings": postings_dict}
            term_offsets[term] = line_offset
            terms_by_length.setdefault(len(term), []).append(term)

    # 將所有平方和開根號，完成向量長度計算
    for doc_id in doc_lengths:
        doc_lengths[doc_id] = math.sqrt(doc_lengths[doc_id])
        doc_lengths_raw[doc_id] = math.sqrt(doc_lengths_raw[doc_id])

    global avg_doc_length
    avg_doc_length = sum(doc_token_counts.values()) / len(doc_token_counts)
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

# 索引只存詞幹，拼錯的字常常剛好還原成索引裡的雜訊詞 (例如 goverment -> gover, df=30)。
# 所以 df 偏低的詞也視為可疑：若有編輯距離 1 且 df 高很多倍的詞，就提出建議。
SUSPICIOUS_DF = 50
DF_RATIO = 20

def suggest_spelling_corrections(query_terms):
    suggestions = {}
    for term in query_terms:
        if len(term) < 4 or not term.isalpha():
            continue
        term_df = inverted_index[term]["df"] if term in inverted_index else 0
        if term_df >= SUSPICIOUS_DF:
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
            # 排序：編輯距離小 -> 字形相似度高 -> df 高 (gover 的建議要 govern 優先於 over)
            (distance, -difflib.SequenceMatcher(None, term, candidate).ratio(),
             -inverted_index[candidate]["df"], candidate)
            for candidate in matches
            if candidate != term
            and (distance := _spelling_distance(term, candidate)) <= max_distance
            and (
                term_df == 0  # 完全不在索引裡
                or (distance <= 1 and inverted_index[candidate]["df"] >= DF_RATIO * term_df)
            )
        ]
        ranked_matches.sort()
        matches = [ranked[-1] for ranked in ranked_matches[:3]]
        if matches:
            suggestions[term] = matches
    return suggestions

# 查詢語法 (運算式節點)：
#   "term"                      -> 字串
#   ("and"/"or", 左, 右)        -> 布林運算
#   ("not", 子式)               -> 排除 (只能搭配至少一個正向詞)
#   ("phrase", ((詞, 位置), ...), slop) -> 片語 (slop=0) 或鄰近 (slop=k，k 個位置內、不限順序)
_PHRASE_TOKEN_RE = re.compile(r'"([^"]*)"(?:~(\d+))?')

def _is_and(token):
    return token.lower() == "and"

def _is_or(token):
    return token.lower() == "or"

def parse_boolean_query(query):
    if query.count('"') % 2:
        raise ValueError("引號不成對。")
    # token：帶引號的片語 (可接 ~k)、括號、其他以空白分隔的詞
    tokens = re.findall(r'"[^"]*"(?:~\d+)?|\(|\)|[^\s()"]+', query)
    # NOT 只認大寫，避免把一般英文的 not (停用詞) 誤判成運算子
    if not any(
        _is_and(t) or _is_or(t) or t in {"NOT", "(", ")"} or t.startswith('"')
        for t in tokens
    ):
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
        if token == "NOT":
            position += 1
            operand = parse_primary()
            return None if operand is None else ("not", operand)
        if _is_and(token) or _is_or(token) or token == ")":
            raise ValueError(f"布林運算子或括號位置錯誤：{token}")

        position += 1
        if token.startswith('"'):
            match = _PHRASE_TOKEN_RE.fullmatch(token)
            items = analyze_positions(match.group(1))
            slop = int(match.group(2)) if match.group(2) else 0
            if not items:
                return None
            if len(items) == 1:
                return items[0][0]
            return ("phrase", tuple(items), slop)
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
        while position < len(tokens) and not _is_or(tokens[position]) and tokens[position] != ")":
            if _is_and(tokens[position]):
                position += 1
            expression = combine("and", expression, parse_primary())
        return expression

    def parse_or():
        nonlocal position
        expression = parse_and()
        while position < len(tokens) and _is_or(tokens[position]):
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
    """取出參與計分的正向詞 (NOT 底下的詞不計分)。"""
    if isinstance(expression, str):
        return [expression]
    if expression[0] == "phrase":
        return [term for term, _ in expression[1]]
    if expression[0] == "not":
        return []
    return get_boolean_terms(expression[1]) + get_boolean_terms(expression[2])

def replace_boolean_terms(expression, suggestions):
    if isinstance(expression, str):
        return suggestions.get(expression, [expression])[0]
    if expression[0] == "phrase":
        items = tuple(
            (suggestions.get(term, [term])[0], offset) for term, offset in expression[1]
        )
        return ("phrase", items, expression[2])
    if expression[0] == "not":
        return ("not", replace_boolean_terms(expression[1], suggestions))
    operator, left, right = expression
    return (
        operator,
        replace_boolean_terms(left, suggestions),
        replace_boolean_terms(right, suggestions),
    )

def read_positions(term, doc_ids):
    """回頭讀索引檔，取出 term 在指定文件中的位置清單 {docID: [pos, ...]}。"""
    offset = term_offsets.get(term)
    if offset is None:
        return {}
    with open(INDEX_FILE_PATH, "rb") as f:
        f.seek(offset)
        line = f.readline().decode("utf-8").rstrip("\r\n")
    _, _, rest = line.partition(": <")
    found = {}
    for posting in rest[:-1].split("; "):
        doc_part, _, positions_part = posting.partition(": <")
        doc_id = doc_part.partition(", ")[0]
        if doc_id in doc_ids:
            found[doc_id] = [int(p) for p in positions_part.rstrip(">").split(", ")]
    return found

def _phrase_in_order(items, position_lists):
    """每個詞的位置要剛好等於第一個詞的位置加上它們在查詢裡的相對位置 (含停用詞留下的空位)。"""
    base = items[0][1]
    later_sets = [set(positions) for positions in position_lists[1:]]
    return any(
        all(start + items[i][1] - base in later_sets[i - 1] for i in range(1, len(items)))
        for start in position_lists[0]
    )

def _within_window(position_lists, slop):
    """所有詞是否出現在寬度 slop 的視窗內 (不限順序)，用滑動視窗掃描合併後的位置。"""
    merged = sorted((p, i) for i, positions in enumerate(position_lists) for p in positions)
    needed = len(position_lists)
    counts = [0] * needed
    covered = 0
    left = 0
    for right in range(len(merged)):
        index = merged[right][1]
        if counts[index] == 0:
            covered += 1
        counts[index] += 1
        while covered == needed:
            if merged[right][0] - merged[left][0] <= slop:
                return True
            counts[merged[left][1]] -= 1
            if counts[merged[left][1]] == 0:
                covered -= 1
            left += 1
    return False

def evaluate_phrase(items, slop):
    terms = [term for term, _ in items]
    if any(term not in inverted_index for term in terms):
        return set()

    # 先用 AND 縮小候選文件，再只對候選文件讀位置
    candidates = None
    for term in sorted(set(terms), key=lambda t: inverted_index[t]["df"]):
        docs = set(inverted_index[term]["postings"])
        candidates = docs if candidates is None else candidates & docs
        if not candidates:
            return set()

    positions = {term: read_positions(term, candidates) for term in set(terms)}
    matched = set()
    for doc_id in candidates:
        position_lists = [positions[term][doc_id] for term in terms]
        if slop == 0:
            if _phrase_in_order(items, position_lists):
                matched.add(doc_id)
        elif _within_window(position_lists, slop):
            matched.add(doc_id)
    return matched

def evaluate_boolean_query(expression):
    if isinstance(expression, str):
        return set(inverted_index.get(expression, {}).get("postings", {}))
    if expression[0] == "phrase":
        return evaluate_phrase(expression[1], expression[2])
    if expression[0] == "not":
        return set(doc_lengths) - evaluate_boolean_query(expression[1])

    operator, left, right = expression
    left_docs = evaluate_boolean_query(left)
    right_docs = evaluate_boolean_query(right)
    if operator == "and":
        return left_docs & right_docs
    return left_docs | right_docs

def _rank_bm25(query_terms, allowed_doc_ids):
    """Okapi BM25：score = sum idf * tf*(k1+1) / (tf + k1*(1-b+b*|d|/avgdl))。
    idf 用 ln(1 + (N-df+0.5)/(df+0.5)) (恆為正)；不做 cosine 正規化。"""
    scores = {}
    for term in set(query_terms):
        entry = inverted_index.get(term)
        if entry is None:
            continue
        df = entry["df"]
        idf = math.log(1 + (TOTAL_DOCS - df + 0.5) / (df + 0.5))
        for doc_id, tf in entry["postings"].items():
            if allowed_doc_ids is not None and doc_id not in allowed_doc_ids:
                continue
            length_norm = BM25_K1 * (1 - BM25_B + BM25_B * doc_token_counts[doc_id] / avg_doc_length)
            scores[doc_id] = scores.get(doc_id, 0.0) + idf * tf * (BM25_K1 + 1) / (tf + length_norm)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

def rank_documents(query_terms, allowed_doc_ids=None, weighting=DEFAULT_WEIGHTING):
    """依指定權重方案計分並排序，回傳 [(docID, score)] (分數高到低)。"""
    if weighting not in WEIGHTING_SCHEMES:
        raise ValueError(f"未知的權重方案：{weighting}")
    if weighting == "bm25":
        return _rank_bm25(query_terms, allowed_doc_ids)

    # 向量空間模型：tfidf = (1+log tf)*idf；tfidf-raw = tf*idf；兩者都用 cosine similarity
    if weighting == "tfidf-raw":
        tf_weight = lambda tf: tf
        lengths = doc_lengths_raw
    else:
        tf_weight = lambda tf: 1 + math.log10(tf)
        lengths = doc_lengths

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
        idf = math.log10(TOTAL_DOCS / inverted_index[term]["df"])
        for doc_id, tf in postings.items():
            if allowed_doc_ids is not None and doc_id not in allowed_doc_ids:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + (q_weight * tf_weight(tf) * idf)

    # 計算 Cosine Similarity (內積 / 兩向量長度相乘)
    results = [
        (doc_id, dot_product / (query_length * lengths[doc_id]))
        for doc_id, dot_product in scores.items()
    ]

    # 依相似度分數降冪排序
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def search(query, interactive=True, weighting=DEFAULT_WEIGHTING):
    """執行一個查詢，回傳 (results, spelling_suggestions)。

    查詢格式錯誤或沒有可搜尋的詞時丟出 ValueError。
    interactive=True 時遇到拼字建議會詢問使用者是否替換；批次模式不替換，只回傳建議。
    """
    # 查詢前處理與 HW1 索引一致 (StandardTokenizer -> 小寫 -> 停用詞 -> Porter 詞幹)
    query_terms = analyze(query)
    boolean_expression = parse_boolean_query(query)
    if boolean_expression is not None:
        query_terms = get_boolean_terms(boolean_expression)
    if not query_terms:
        raise ValueError("沒有可計分的正向搜尋詞 (查詢只含停用詞、符號，或只有 NOT)。")

    spelling_suggestions = suggest_spelling_corrections(query_terms)
    if spelling_suggestions and interactive:
        print("拼字建議 (索引存的是詞幹，所以建議也是詞幹形式)：")
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
    return rank_documents(query_terms, allowed_doc_ids, weighting), spelling_suggestions

def run_batch(queries_path, output_path, top_k, weighting=DEFAULT_WEIGHTING):
    """讀查詢檔 (每行一個查詢)，把每個查詢的前 top_k 名寫入輸出檔。"""
    with open(queries_path, "r", encoding="utf-8") as f:
        queries = [line.strip() for line in f if line.strip()]

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"# weighting: {weighting}\n\n")
        for query in queries:
            out.write(f"Query: {query}\n")
            try:
                results, suggestions = search(query, interactive=False, weighting=weighting)
            except ValueError as error:
                out.write(f"# 錯誤：{error}\n\n")
                continue
            for term, matches in suggestions.items():
                out.write(f"# 拼字建議：{term} -> {', '.join(matches)}\n")
            if not results:
                out.write("# 找不到符合的搜尋結果。\n")
            for doc_id, score in results[:top_k]:
                out.write(f"{doc_id}\t{score:.6f}\n")
            out.write("\n")
            print(f"{query!r}: 命中 {len(results)} 篇，輸出前 {min(top_k, len(results))} 名")
    print(f"完成！結果已寫入 {output_path}")

def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("必須是大於 0 的整數")
    return number

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IR HW2: 向量空間模型搜尋 (TF-IDF + cosine similarity)")
    parser.add_argument("--top", type=positive_int, default=TOP_K,
                        help=f"顯示/輸出前 N 名 (預設 {TOP_K}，可在 config.py 的 TOP_K 修改)")
    parser.add_argument("--weighting", choices=WEIGHTING_SCHEMES, default=DEFAULT_WEIGHTING,
                        help=f"權重/排序方案 (預設 {DEFAULT_WEIGHTING})：tfidf、tfidf-raw、bm25")
    parser.add_argument("--queries", metavar="FILE",
                        help="批次模式：查詢檔，每行一個查詢；結果寫入輸出檔")
    parser.add_argument("--output", metavar="FILE", default=OUTPUT_FILE_PATH,
                        help=f"批次模式的輸出檔 (預設 {OUTPUT_FILE_PATH})")
    args = parser.parse_args()

    load_index()

    if args.queries:
        run_batch(args.queries, args.output, args.top, args.weighting)
        raise SystemExit(0)

    print("==================================================")
    print(" 歡迎使用 IR Homework 2: 查詢處理與搜尋系統")
    print(f" 權重方案：{args.weighting}；每次顯示前 {args.top} 名；輸入 'exit' 離開程式")
    print("==================================================")

    while True:
        query = input("\ncmd> ")
        if query.lower() == "exit":
            break
        if not query.strip():
            continue

        try:
            results, _ = search(query, weighting=args.weighting)
        except ValueError as error:
            print(f"查詢錯誤：{error}")
            continue

        if not results:
            print("找不到符合的搜尋結果。")
            continue

        print("Ranked Search Results:")
        print("<doc#> \t\t <similarity score>")
        for doc_id, score in results[:args.top]:
            print(f"{doc_id} \t {score:.6f}")
