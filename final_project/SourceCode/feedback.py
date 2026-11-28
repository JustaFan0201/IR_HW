import Search as S
from analyzer import analyze
from config import (ROCCHIO_ALPHA, ROCCHIO_BETA, ROCCHIO_GAMMA, EXPAND_TERMS_M,
                     TOP_K, PRF_DOCS, PRF_MAX_VEC_TERMS, PRF_MAX_DF_RATIO)

def rocchio(query_vec: dict[str, float],
            rel_ids: list[str],
            nonrel_ids: list[str],
            alpha=ROCCHIO_ALPHA,
            beta=ROCCHIO_BETA,
            gamma=ROCCHIO_GAMMA) -> dict[str, float]:
    """回傳新的查詢向量 {詞: 權重}，負權重的詞要拿掉。"""
    new_vec = {}

    # alpha * Q_old
    for term, w in query_vec.items():
        new_vec[term] = alpha * w

    # + (beta / |Dr|) * sum(正規化後的 d_r)
    if rel_ids:
        scale_rel = beta / len(rel_ids)
        for doc_id in rel_ids:
            d_vec = S.get_doc_vector(doc_id)
            length = S.doc_lengths.get(doc_id)
            if not length:
                continue
            for term, w in d_vec.items():
                new_vec[term] = new_vec.get(term, 0.0) + scale_rel * (w / length)

    # - (gamma / |Dnr|) * sum(正規化後的 d_nr)
    if nonrel_ids:
        scale_nonrel = gamma / len(nonrel_ids)
        for doc_id in nonrel_ids:
            d_vec = S.get_doc_vector(doc_id)
            length = S.doc_lengths.get(doc_id)
            if not length:
                continue
            for term, w in d_vec.items():
                new_vec[term] = new_vec.get(term, 0.0) - scale_nonrel * (w / length)

    # 剔除權重 <= 0 的詞
    return {term: w for term, w in new_vec.items() if w > 0}

def expand_terms(query: str,
                 top_ids: list[str],
                 m=EXPAND_TERMS_M,
                 already_analyzed_terms: list[str] | None = None) -> list[tuple[str, float]]:
    """回傳建議擴展詞 [(詞, 分數)]，分數高到低，最多 m 個，不含原查詢已有的詞。

    若呼叫端已經做過拼字校正或布林/萬用字元展開，要透過 already_analyzed_terms 傳入，
    確保排除的詞跟實際拿去搜尋的詞一致；不傳的話則退回用 query 自行分析。

    註：若 query 為布林語法錯誤（例如引號不成對）或只含停用詞，
    Search.parse_boolean_query 內部會丟出 ValueError，此函式會將其視為
    「無布林/萬用字元展開」並退回只用 analyze(query) 的結果排除，不會中斷執行。
    """
    if already_analyzed_terms is not None:
        orig_terms = set(already_analyzed_terms)
    else:
        orig_terms = set(analyze(query))
        try:
            expression = S.parse_boolean_query(query)
            if expression is not None:
                orig_terms.update(S.get_boolean_terms(expression))
        except ValueError:
            pass

    term_scores = {}
    for doc_id in top_ids:
        d_vec = S.get_doc_vector(doc_id)
        for term, w in d_vec.items():
            if term not in orig_terms:
                term_scores[term] = term_scores.get(term, 0.0) + w

    ranked = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:m]

def prf(query: str, k: int = TOP_K, fb_docs: int = PRF_DOCS,
        max_vec_terms: int = PRF_MAX_VEC_TERMS,
        max_df_ratio: float = PRF_MAX_DF_RATIO,
        apply_suggestions: bool = False) -> list[tuple[str, float]]:
    """虛擬相關回饋 (Pseudo Relevance Feedback)：
    先搜一次取前 fb_docs 篇，假設它們是相關的，用 Rocchio 改寫查詢後重新搜尋，
    回傳前 k 篇 [(docID, score)]。

    兩輪都固定用 tfidf cosine：Rocchio 向量與 Search.rank_by_vector 都是 tfidf 空間，
    第一輪若用別的權重方案 (如 bm25)，挑出的虛擬相關文件與重排的尺度會不一致，
    fb_docs <= 0 時回傳的分數也會不在 [0, 1]。

    k：最終回傳的篇數 (供 METHODS 介面呼叫，與回饋文件數無關)；k <= 0 時直接回傳 []。
    fb_docs：當作虛擬相關文件的篇數 (PRF 慣例取少量，預設見 config.PRF_DOCS)；
    <= 0 時視為不做回饋，直接回傳第一輪搜尋結果的前 k 篇。
    max_vec_terms：改寫後的查詢向量 (含原查詢詞) 總詞數上限，避免向量過大拖慢排序。
    字面查詢詞不受此上限：字面詞本身比上限多時，向量詞數會超過上限；
    上限 <= 0 時只剩字面查詢詞 (沒有擴充詞)，仍會用它們重排；字面詞也沒有時退回第一輪結果。
    max_df_ratio：排除 df 佔總文件數比例超過此值的擴展詞 (太常見/雜訊詞)；
    使用者字面輸入的查詢詞不受此限制，一律保留，避免 query drift。
    萬用字元展開出來的詞不算字面查詢詞，視為擴展詞，一樣受 df 過濾與名額競爭，
    否則 inform* 這類查詢會把 50 個展開詞全部保護起來，沒有名額留給真正的擴充詞。
    apply_suggestions：預設 False，與 Search.search / run_batch 一致，保持使用者輸入的查詢詞不變，
    PRF 與 baseline 才是在比同一個查詢 (拼字正確但 df 偏低的詞不會被悄悄換掉)；
    True 時比照 Search.search(apply_suggestions=True)，用第一個拼字建議替換可疑的查詢詞。

    索引尚未載入時丟出 RuntimeError (與 Search.get_doc_vector 一致)。
    查詢無效時回傳 []，不拋錯 (刻意設計，讓 benchmark 批次執行不會中斷)，
    所以呼叫端無法從回傳值分辨「查詢無效」與「沒有符合的文件」。
    無效查詢包括：語法錯誤 (如引號不成對)、萬用字元範圍太廣 (如 a*)、
    只含停用詞、只有 NOT、萬用字元沒有符合的詞。
    """
    if not S.inverted_index:
        raise RuntimeError("尚未呼叫 Search.load_index()，索引是空的")
    if k <= 0:
        return []

    try:
        boolean_expression = S.parse_boolean_query(query)
        if boolean_expression is not None:
            query_terms = S.get_boolean_terms(boolean_expression)
            literal_terms = S.get_boolean_terms(boolean_expression, include_wildcard=False)
        else:
            query_terms = analyze(query)
            literal_terms = query_terms
        if not query_terms:
            return []

        # 拼字修正：只檢查字面詞 (萬用字元展開詞本來就在索引裡)，做法同 Search.search
        if apply_suggestions:
            suggestions = S.suggest_spelling_corrections(literal_terms)
            if suggestions:
                if boolean_expression is None:
                    query_terms = [suggestions[t][0] if t in suggestions else t for t in query_terms]
                    literal_terms = query_terms
                else:
                    boolean_expression = S.replace_boolean_terms(boolean_expression, suggestions)
                    query_terms = S.get_boolean_terms(boolean_expression)
                    literal_terms = S.get_boolean_terms(boolean_expression, include_wildcard=False)

        allowed_doc_ids = (
            S.evaluate_boolean_query(boolean_expression) if boolean_expression is not None else None
        )
        initial_results = S.rank_documents(query_terms, allowed_doc_ids, weighting="tfidf",
                                           min_results=max(k, fb_docs))
    except ValueError:
        return []

    if fb_docs <= 0:
        return initial_results[:k]

    top_ids = [doc_id for doc_id, _ in initial_results[:fb_docs]]
    if not top_ids:
        return []

    query_vec = S.query_vector(query_terms)
    new_query_vec = rocchio(query_vec, rel_ids=top_ids, nonrel_ids=[])

    # 只有字面查詢詞受保護；df 過濾套用在 Rocchio 新加入的詞與萬用字元展開詞上
    protected_terms = set(literal_terms) & set(query_vec)
    max_df = S.TOTAL_DOCS * max_df_ratio
    filtered = {
        t: w for t, w in new_query_vec.items()
        if t in protected_terms or (t in S.inverted_index and S.inverted_index[t]["df"] <= max_df)
    }
    # 截斷總詞數到 max_vec_terms：字面查詢詞直接保留，剩餘名額才給其他詞依權重競爭
    if len(filtered) > max_vec_terms:
        protected = {t: w for t, w in filtered.items() if t in protected_terms}
        expandable = {t: w for t, w in filtered.items() if t not in protected_terms}
        remaining_slots = max(0, max_vec_terms - len(protected))
        top_expandable = sorted(expandable.items(), key=lambda x: x[1], reverse=True)[:remaining_slots]
        filtered = {**protected, **dict(top_expandable)}

    if not filtered:
        # df 過濾或截斷後什麼都不剩 (例如純萬用字元查詢且展開詞全是高 df，或 max_vec_terms <= 0)，
        # 退回第一輪結果，避免 rank_by_vector 收到空向量而回傳 []
        return initial_results[:k]

    return S.rank_by_vector(filtered, allowed_doc_ids=allowed_doc_ids)[:k]

METHODS = {"prf": prf}