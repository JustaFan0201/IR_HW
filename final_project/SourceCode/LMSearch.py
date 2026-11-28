"""Query likelihood 語言模型檢索 (Dirichlet 平滑)。模組 D。

    score(q, d) = sum_{t in q} log P(t | d)
    P(t | d)    = (tf(t,d) + mu * P(t | C)) / (|d| + mu)        P(t | C) = cf(t) / |C|

只對「至少含一個查詢詞」的文件計分，並用下面這個與原式排名完全等價的寫法，
這樣每個詞只需掃自己的 postings，不必逐篇文件走過所有查詢詞：

    score(q, d) = sum_{t in q, tf>0} log(1 + tf / (mu * P(t|C)))  +  |q| * log(mu / (|d| + mu))
                  (+ 與文件無關的常數 sum_t log P(t|C)，不影響排名所以省略)

所以分數是「相對值」，可以比大小，但不要拿來跟其他方案的分數直接比較。
|d| 用索引中的詞數 (doc_token_counts，已去除停用詞)，與 BM25 的文件長度一致。
"""
import math
from collections import Counter

import Search as S
from analyzer import analyze

DEFAULT_MU = 1000

_collection = {"length": None, "cf": {}}


def _collection_length():
    if _collection["length"] is None:
        _collection["length"] = sum(S.doc_token_counts.values())
    return _collection["length"]


def _collection_freq(term):
    """詞在整個文件集中出現的總次數 (第一次用到時才算，之後快取)。"""
    cf = _collection["cf"].get(term)
    if cf is None:
        cf = _collection["cf"][term] = sum(S.inverted_index[term]["postings"].values())
    return cf


def rank_lm(query_terms, mu=DEFAULT_MU, allowed_doc_ids=None):
    """回傳 [(docID, score)]，分數高到低。不在索引中的查詢詞直接略過。"""
    counts = Counter(t for t in query_terms if t in S.inverted_index)
    if not counts:
        return []
    total = _collection_length()
    scores = {}
    for term, q_count in counts.items():
        p_collection = _collection_freq(term) / total
        denom = mu * p_collection
        for doc_id, tf in S.inverted_index[term]["postings"].items():
            if allowed_doc_ids is not None and doc_id not in allowed_doc_ids:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + q_count * math.log(1 + tf / denom)
    query_length = sum(counts.values())
    results = [
        (doc_id, s + query_length * math.log(mu / (S.doc_token_counts[doc_id] + mu)))
        for doc_id, s in scores.items()
    ]
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def search_lm(query, top_k=10, mu=DEFAULT_MU):
    """自由文本查詢 (套用與索引相同的分析鏈)，回傳前 top_k 筆 [(docID, score)]。"""
    return rank_lm(analyze(query), mu)[:top_k]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Query likelihood (Dirichlet) 檢索")
    parser.add_argument("query")
    parser.add_argument("--mu", type=float, default=DEFAULT_MU)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    S.load_index()
    for doc_id, score in search_lm(args.query, args.top, args.mu):
        print(f"{doc_id}\t{score:.4f}")
