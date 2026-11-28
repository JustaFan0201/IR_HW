"""所有排序方案的統一介面。模組 D。

每個方案是一個函式 `fn(query: str, k: int) -> [(docID, score)]`，註冊在 METHODS。
內建：tfidf、tfidf-raw、bm25、lm (query likelihood, Dirichlet)。

A、C 的方法不用改這個檔案。在自己的模組裡放一個 `METHODS = {名稱: fn}`，
實驗時用 `--plugins 模組名` 載入 (模組名 = repo 裡的檔名，不含 .py)，例如：

    # semantic.py (C)
    def hybrid(query, k): ...
    METHODS = {"semantic": lambda q, k: semantic_search(q, k), "hybrid": hybrid}

    python SourceCode/RunExperiments.py --plugins semantic            # A 的 feedback.py 加上 METHODS 後再加 feedback

載入失敗 (找不到模組、模組沒有 METHODS) 會直接報錯結束，不會默默只跑 baseline。
過渡期：模組若還沒有 METHODS 但有 TASKS.md 約定的 `semantic_search(query, k)`，
會自動以名稱 "semantic" 註冊。
"""
import importlib
import sys

import Search as S
from Evaluate import split_item
from LMSearch import DEFAULT_MU, search_lm

METHODS = {}


def register(name, fn):
    """註冊方法；回傳值統一轉成 [(str(docID), float(score))]，plugin 回傳 list / numpy 列也沒問題。"""
    def normalized(query, k):
        return [split_item(item) for item in fn(query, k)]
    METHODS[name] = normalized


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
    """匯入其他組員的模組並註冊它們的 METHODS。
    找不到模組、或模組沒有提供任何方法時直接結束：否則比較表看起來完整，其實只有 baseline。"""
    for name in module_names or []:
        try:
            module = importlib.import_module(name)
        except ImportError as error:
            sys.exit(f"[錯誤] 無法載入 --plugins 指定的模組 {name}：{error}\n"
                     "模組名稱是檔名 (不含 .py)，且要在 SourceCode/ 下或在 PYTHONPATH 裡。")
        methods = dict(getattr(module, "METHODS", {}))
        if not methods and hasattr(module, "semantic_search"):
            methods = {"semantic": lambda q, k, _fn=module.semantic_search: _fn(q, k)}
        if not methods:
            sys.exit(f"[錯誤] 模組 {name} 沒有 METHODS ({{名稱: fn(query, k)}})，沒有任何方法可評估。\n"
                     "請該模組的負責人加上 METHODS，格式見 Methods.py 開頭的說明。")
        for method, fn in methods.items():
            register(method, fn)
            print(f"[載入] {name} -> {method}")
