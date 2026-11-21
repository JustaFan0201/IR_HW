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

    # + (beta / |Dr|) * sum(d_r)
    if rel_ids:
        scale_rel = beta / len(rel_ids)
        for doc_id in rel_ids:
            d_vec = S.get_doc_vector(doc_id)
            for term, w in d_vec.items():
                new_vec[term] = new_vec.get(term, 0.0) + scale_rel * w

    # - (gamma / |Dnr|) * sum(d_nr)
    if nonrel_ids:
        scale_nonrel = gamma / len(nonrel_ids)
        for doc_id in nonrel_ids:
            d_vec = S.get_doc_vector(doc_id)
            for term, w in d_vec.items():
                new_vec[term] = new_vec.get(term, 0.0) - scale_nonrel * w

    # 剔除權重 <= 0 的詞
    return {term: w for term, w in new_vec.items() if w > 0}


def expand_terms(query: str, top_ids: list[str], m=EXPAND_TERMS_M) -> list[tuple[str, float]]:
    """回傳建議擴展詞 [(詞, 分數)]，分數高到低，最多 m 個，不含原查詢已有的詞。"""
    orig_terms = set(analyze(query))
    
    term_scores = {}
    for doc_id in top_ids:
        d_vec = S.get_doc_vector(doc_id)
        for term, w in d_vec.items():
            if term not in orig_terms:
                term_scores[term] = term_scores.get(term, 0.0) + w

    ranked = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:m]