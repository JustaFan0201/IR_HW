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
        max_df_ratio: float = PRF_MAX_DF_RATIO) -> list[tuple[str, float]]:
    """虛擬相關回饋 (Pseudo Relevance Feedback)：
    先搜一次取前 fb_docs 篇，假設它們是相關的，用 Rocchio 改寫查詢後重新搜尋，
    回傳前 k 篇 [(docID, score)]。

    k：最終回傳的篇數 (供 METHODS 介面呼叫，與回饋文件數無關)。
    fb_docs：當作虛擬相關文件的篇數 (PRF 慣例取少量，預設見 config.PRF_DOCS)。
    max_vec_terms：Rocchio 算出的新向量，扣掉原查詢詞後最多再保留幾個擴展詞。
    max_df_ratio：排除 df 佔總文件數比例超過此值的擴展詞 (太常見/雜訊詞)；
    原查詢詞不受此限制，一律保留，避免 query drift。
    """
    initial_results, _, _ = S.search(query, interactive=False, top_k=fb_docs)
    top_ids = [doc_id for doc_id, _ in initial_results[:fb_docs]]
    if not top_ids:
        return []

    query_terms = analyze(query)
    query_vec = S.query_vector(query_terms)
    new_query_vec = rocchio(query_vec, rel_ids=top_ids, nonrel_ids=[])

    # 原查詢詞一律保留，df 過濾只套用在 Rocchio 新加入的擴展詞上，避免原查詢詞被濾掉造成 query drift
    orig_terms = set(query_vec)
    max_df = S.TOTAL_DOCS * max_df_ratio
    filtered = {
        t: w for t, w in new_query_vec.items()
        if t in orig_terms or (t in S.inverted_index and S.inverted_index[t]["df"] <= max_df)
    }

    # 截斷前 max_vec_terms 個詞：原查詢詞不參與排名、直接保留，剩餘名額才給擴展詞依權重競爭
    if len(filtered) > max_vec_terms:
        protected = {t: w for t, w in filtered.items() if t in orig_terms}
        expandable = {t: w for t, w in filtered.items() if t not in orig_terms}
        remaining_slots = max(0, max_vec_terms - len(protected))
        top_expandable = sorted(expandable.items(), key=lambda x: x[1], reverse=True)[:remaining_slots]
        filtered = {**protected, **dict(top_expandable)}

    return S.rank_by_vector(filtered)[:k]

METHODS = {"prf": prf}