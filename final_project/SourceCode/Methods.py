"""所有排序方案的統一介面。模組 D。

每個方案是一個函式 `fn(query: str, k: int) -> [(docID, score)]`，註冊在 METHODS。
內建：tfidf、tfidf-raw、bm25、lm (query likelihood, Dirichlet)。

A、C 的方法不用改這個檔案。在自己的模組裡放一個 `METHODS = {名稱: fn}`，
實驗時用 `--plugins 模組名` 載入，例如：

    # SemanticSearch.py (C)
    from Search import search
    def hybrid(query, k): ...
    METHODS = {"semantic": lambda q, k: semantic_search(q, k), "hybrid": hybrid}

    python RunExperiments.py --plugins SemanticSearch Feedback
"""
import importlib

import Search as S
from LMSearch import DEFAULT_MU, search_lm

METHODS = {}


def register(name, fn):
    METHODS[name] = fn


def _vsm(weighting):
    def run(query, k):
        try:
            results, _, _ = S.search(query, interactive=False, weighting=weighting, top_k=k)
        except ValueError:      # 查詢沒有可計分的詞
            return []
        return results[:k]
    return run


for _w in S.WEIGHTING_SCHEMES:
    register(_w, _vsm(_w))
register("lm", lambda query, k: search_lm(query, k, DEFAULT_MU))


def lm_with_mu(mu):
    return lambda query, k: search_lm(query, k, mu)


def load_plugins(module_names):
    """匯入其他組員的模組並註冊它們的 METHODS；缺模組時只提醒，不中斷。"""
    for name in module_names:
        try:
            module = importlib.import_module(name)
        except ImportError as error:
            print(f"[略過] 無法載入 {name}：{error}")
            continue
        for method, fn in getattr(module, "METHODS", {}).items():
            register(method, fn)
            print(f"[載入] {name} -> {method}")
