import Search as S
from analyzer import analyze
from config import ROCCHIO_ALPHA, ROCCHIO_BETA, ROCCHIO_GAMMA, EXPAND_TERMS_M

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
