"""模組 B：搜尋結果分群與視覺化 (課本 Ch.15)，介面見 INTERFACE.md。

    python SourceCode/clustering.py [--top 100] [--method kmeans|hier] [--k N] [--weighting tfidf]

對搜尋結果的前 N 篇文件做分群，並把文件投影到 2D 平面：
  - 文件向量：TF-IDF 權重 (1 + log tf) * log(N/df)，每篇長度正規化為 1 (內積 = cosine similarity)。
    Search 有 get_doc_vector (A 實作) 時就用它；還沒有時，退回自己由倒排索引建的稀疏矩陣 (第一次呼叫時建立)。
  - 分群方法：k-means，或階層式 (average linkage，距離 = 1 - cosine)。
  - 群數 k：k = CLUSTER_K_MIN ~ CLUSTER_K_MAX 都試，取 silhouette 最高的 (也可手動指定)。
  - 群標籤：群中心權重最高的 3 個詞，先扣掉全體中心 (去掉每群都有的查詢詞)。候選詞只含英文字母與數字、
    不是純數字，而且要在群內至少 30% 的文件出現 (最少 2 篇)，免得單一網站才有的怪詞變成標籤。
  - 分群依據有兩種：整頁 (預設)，或「查詢詞前後文」：只取查詢詞每次出現位置前後各 CLUSTER_CONTEXT_WINDOW 個詞
    組成向量。網頁常有大量導覽列與側欄文字，整頁向量容易分出「哪個網站」而不是「查詢詞在這頁是什麼意思」
    (例如 jaguar 的動物新聞藏在 USA Today 側欄裡)。前後文版需要傳入 query_terms 與 get_text。
  - 2D：PCA 前兩個主成分 (用 N x N 的 Gram 矩陣計算，等價於對中心化資料做 PCA)。

介面約定：
    cluster(doc_ids)    -> [{"label": "java island indonesia", "doc_ids": [...]}]   (大的群在前)
    project_2d(doc_ids) -> [(doc_id, x, y, 群編號)]    群編號 = cluster() 回傳清單的索引
doc_ids 要依排名由高到低給。兩者共用同一份快取的分群結果，所以群編號與座標一定對得上。
cluster() 的每個 dict 另外有 "terms" (標籤的詞幹串列) 與 "size"，用不到可以忽略。

網頁前端 (給 C 接進 WebApp.py)：render_sidebar()、render_scatter()、CLUSTER_CSS 等，見檔案最下方
與 clustering_integration.md。這個檔案本身不碰 WebApp.py。
"""
import argparse
import html
import math
import re
import threading
import time
from array import array
from collections import Counter, OrderedDict

import numpy as np
from scipy import sparse
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from config import (CLUSTER_TOP_N, CLUSTER_METHOD, CLUSTER_K_MIN, CLUSTER_K_MAX,
                    CLUSTER_LABEL_TERMS, CLUSTER_MIN_SILHOUETTE, CLUSTER_MIN_SIZE, CLUSTER_CONTEXT_WINDOW)
import Search
from analyzer import STOPWORDS, _TOKEN_RE, _stem, token_spans

# 前後文分群時，每篇文件最多讀前多少字元
_CONTEXT_MAX_CHARS = 60000
# 群標籤不用 df 超過全部文件這個比例的詞
_LABEL_MAX_DF = 0.2
# 前 N 篇至少要有幾篇才做「丟掉只出現在 1 篇的詞」
_PRUNE_MIN_DOCS = 10

METHODS = ("kmeans", "hier")
METHOD_NAMES = {"kmeans": "k-means", "hier": "階層式 (average linkage)"}

_lock = threading.Lock()
_state = {"ready": False, "matrix": None, "doc_index": None, "terms": None}
_cache = OrderedDict()   # (doc_ids, method, k) -> 分群結果，只留最近幾筆
_CACHE_SIZE = 16


# ---------------------------------------------------------------- 文件向量

def build_doc_matrix():
    """(退回用) 由倒排索引建出「文件 x 詞」稀疏矩陣 (csr)，每列是長度為 1 的 TF-IDF 向量。需先 Search.load_index()。
    Search 有 get_doc_vector 時不需要。cluster() 第一次呼叫會自動建立；想事先建好 (例如網頁啟動時) 可以自己呼叫。"""
    with _lock:
        if _state["ready"]:
            return
    doc_ids = sorted(Search.doc_lengths)
    doc_index = {doc_id: row for row, doc_id in enumerate(doc_ids)}
    lengths = Search.doc_lengths
    rows, cols, data = array("i"), array("i"), array("f")
    terms = []
    for term, entry in Search.inverted_index.items():
        idf = math.log10(Search.TOTAL_DOCS / entry["df"])
        if idf <= 0:          # 每篇都有的詞權重為 0，不需要存
            continue
        column = len(terms)
        terms.append(term)
        for doc_id, tf in entry["postings"].items():
            length = lengths[doc_id]
            if length == 0:
                continue
            rows.append(doc_index[doc_id])
            cols.append(column)
            data.append((1 + math.log10(tf)) * idf / length)
    matrix = sparse.csr_matrix(
        (np.frombuffer(data, dtype=np.float32),
         (np.frombuffer(rows, dtype=np.int32), np.frombuffer(cols, dtype=np.int32))),
        shape=(len(doc_ids), len(terms)))
    with _lock:
        _state.update(matrix=matrix, doc_index=doc_index, terms=terms, ready=True)


def is_ready():
    """可以直接分群了嗎 (有 get_doc_vector，或退回用的矩陣已建好)。"""
    return hasattr(Search, "get_doc_vector") or _state["ready"]


def _matrix_from_dicts(doc_ids, vectors):
    """把 [{詞: 權重}] 組成稀疏矩陣 (每列長度正規化為 1)；全是零的文件會被略過。回傳 (保留的 doc_ids, X, 欄位對應的詞)。"""
    kept, normed = [], []
    for doc_id, vector in zip(doc_ids, vectors):
        norm = math.sqrt(sum(w * w for w in vector.values())) if vector else 0.0
        if norm > 0:
            kept.append(doc_id)
            normed.append((vector, norm))
    vocabulary, rows, cols, data = {}, [], [], []
    for row, (vector, norm) in enumerate(normed):
        for term, weight in vector.items():
            if weight > 0:
                rows.append(row)
                cols.append(vocabulary.setdefault(term, len(vocabulary)))
                data.append(weight / norm)
    X = sparse.csr_matrix((np.array(data, dtype=np.float32), (rows, cols)),
                          shape=(len(kept), len(vocabulary)))
    terms = [None] * len(vocabulary)
    for term, column in vocabulary.items():
        terms[column] = term
    return kept, X, terms


def _submatrix_from_vectors(doc_ids):
    """用 Search.get_doc_vector (A 實作，回傳 {詞: TF-IDF 權重}) 組出稀疏矩陣。"""
    ids, vectors = [], []
    for doc_id in doc_ids:
        try:
            vectors.append(Search.get_doc_vector(doc_id))
            ids.append(doc_id)
        except KeyError:
            continue
    return _matrix_from_dicts(ids, vectors)


def _hit_pattern(query_terms):
    """在小寫文字裡粗略找出查詢詞出現位置的正規表示式 (比對詞幹的前綴 + 任意後綴；Porter 詞幹常只改字尾，
    例如 family -> famili，所以詞幹 4 個字元以上時少取最後一個字元)。只用來挑出要切詞的片段，找到後仍會用詞幹確認。"""
    prefixes = sorted({re.escape(q[:max(3, len(q) - 1)] if len(q) > 3 else q) for q in query_terms})
    return re.compile(r"\b(?:" + "|".join(prefixes) + r")\w*")


_pattern_cache = {}


def _window_counts(tokens, query_terms, window):
    """tokens (小寫的 token 串列) 裡，查詢詞前後各 window 個 token 的詞幹計數 (重疊的視窗只算一次，查詢詞本身不算)。"""
    firsts = {q[0] for q in query_terms}         # Porter 詞幹還原不會改第一個字元，先用它擋掉絕大多數 token
    forms = {t for t in set(tokens) if t[0] in firsts and t not in STOPWORDS and _stem(t) in query_terms}
    ranges = []                                  # 合併重疊的視窗 [低, 高)
    for i, t in enumerate(tokens):
        if t in forms:
            low, high = max(0, i - window), min(len(tokens), i + window + 1)
            if ranges and low <= ranges[-1][1]:
                ranges[-1][1] = max(ranges[-1][1], high)
            else:
                ranges.append([low, high])
    surface = Counter()
    for low, high in ranges:
        surface.update(tokens[low:high])
    counts = Counter()
    for token, tf in surface.items():
        if token not in STOPWORDS:
            stem = _stem(token)
            if stem not in query_terms:
                counts[stem] += tf
    return counts, bool(ranges)


def _context_vector(text, query_terms, window):
    """查詢詞每次出現位置前後各 window 個詞 (token) 的 TF-IDF 向量 {詞: 權重}，查詢詞本身不算；
    文字裡找不到查詢詞時回傳 None。tf-idf 的 idf 用整個索引的 df，與整頁向量一致。
    切詞是主要成本 (一頁幾千個 token)，所以先用正規表示式粗略找出查詢詞的位置，
    只對每個出現位置前後各 window * 30 個字元的片段切詞 (靠得近的合併成一段)。"""
    text = text[:_CONTEXT_MAX_CHARS].lower()
    query_terms = frozenset(query_terms)
    pattern = _pattern_cache.get(query_terms)
    if pattern is None:
        pattern = _pattern_cache[query_terms] = _hit_pattern(query_terms)
    margin = window * 30
    groups = []                                  # [片段起, 片段迄)，靠得近的命中合併
    for match in pattern.finditer(text):
        low, high = max(0, match.start() - margin), min(len(text), match.end() + margin)
        if groups and low <= groups[-1][1]:
            groups[-1][1] = high
        else:
            groups.append([low, high])
    counts, found = Counter(), False
    for low, high in groups:
        part, hit = _window_counts(_TOKEN_RE.findall(text[low:high]), query_terms, window)
        counts.update(part)
        found = found or hit
    if not found:
        return None
    vector = {}
    for term, tf in counts.items():
        entry = Search.inverted_index.get(term)
        if entry:
            idf = math.log10(Search.TOTAL_DOCS / entry["df"])
            if idf > 0:
                vector[term] = (1 + math.log10(tf)) * idf
    return vector or None


def _submatrix_context(doc_ids, query_terms, get_text, window):
    """前後文版的 _submatrix：回傳 (保留的 doc_ids, X, 詞)。
    取不到內文、或內文裡找不到查詢詞的文件不分群 (用整頁向量補上會被導覽列、側欄帶走，自己聚成「網站群」)。"""
    ids, vectors = [], []
    for doc_id in doc_ids:
        text = get_text(doc_id)
        vector = _context_vector(text, query_terms, window) if text else None
        if vector:
            ids.append(doc_id)
            vectors.append(vector)
    return _matrix_from_dicts(ids, vectors)


def _submatrix(doc_ids):
    """取出指定文件的向量 (只保留這些文件有出現的詞，矩陣才小)。
    回傳 (保留的 doc_ids, 稀疏矩陣 X, 欄位對應的詞)；索引裡沒有的文件會被略過。"""
    if hasattr(Search, "get_doc_vector"):
        return _submatrix_from_vectors(doc_ids)
    if not _state["ready"]:
        build_doc_matrix()          # 第一次呼叫時建立 (數秒)；網頁可在啟動時先在背景呼叫
    kept = [d for d in doc_ids if d in _state["doc_index"]]
    sub = _state["matrix"][[_state["doc_index"][d] for d in kept]]
    columns = np.unique(sub.indices)
    sub = sub[:, columns].tocsr()
    return kept, sub, [_state["terms"][c] for c in columns]


# ---------------------------------------------------------------- 分群

def _prune_rare_terms(X, terms):
    """丟掉只出現在 1 篇文件的詞再重新正規化。這種詞不能讓任兩篇文件變得相似，對分群沒有貢獻，
    卻佔掉大部分維度 (拖慢速度)，也最容易變成沒意義的群標籤 (人名、代號)。文件太少時不做。"""
    if X.shape[0] < _PRUNE_MIN_DOCS:
        return X, terms
    keep = np.flatnonzero(X.getnnz(axis=0) >= 2)
    if len(keep) == 0 or len(keep) == X.shape[1]:
        return X, terms
    X = X[:, keep].tocsr()
    norms = np.sqrt(np.asarray(X.multiply(X).sum(axis=1)).ravel())
    norms[norms == 0] = 1.0                      # 整篇都是稀有詞的文件變成零向量，與誰都不相似
    X = sparse.diags(1.0 / norms).dot(X).tocsr().astype(np.float32)
    return X, [terms[i] for i in keep]


def _distance_matrix(X):
    """cosine 距離 (1 - 內積)；X 的列已長度正規化。"""
    similarity = (X @ X.T).toarray().astype(np.float64)
    distance = np.clip(1.0 - similarity, 0.0, 2.0)
    distance = (distance + distance.T) / 2
    np.fill_diagonal(distance, 0.0)
    return distance


def _kmeans(X, k, n_init=5, max_iter=50, seed=0):
    """k-means (greedy k-means++ 初始化，歐氏距離；X 的列已長度正規化，所以等同 cosine 的近似)。回傳群標籤。
    自己用 numpy / scipy 寫而不用 sklearn.cluster.KMeans：這裡的資料很小 (約 100 篇)，運算只要幾 ms，
    但自動選 k 要擬合十幾次，用 sklearn 的 KMeans 實測整段要 1.5 秒 (向量與投影各只要幾 ms)，推測是每次擬合的固定成本。
    X 保持稀疏 (每篇只有幾百個非零詞)，群中心是 k x 詞數 的稠密矩陣。"""
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    X = X.tocsr().astype(np.float64)
    sq = np.asarray(X.multiply(X).sum(axis=1)).ravel()
    trials = 2 + int(np.log(k))
    everyone = np.arange(n)

    def sq_dist(centers):                       # (n, len(centers)) 每篇到每個中心的平方距離
        return np.maximum(sq[:, None] - 2.0 * np.asarray(X @ centers.T) + (centers ** 2).sum(axis=1)[None, :], 0.0)

    best_labels, best_inertia = None, np.inf
    for _ in range(n_init):
        centers = X[[rng.randint(n)]].toarray()
        closest = sq_dist(centers)[:, 0]
        for _ in range(1, k):                   # k-means++：離現有中心越遠的點越可能被選為下一個中心
            total = closest.sum()               # (貪婪版：抽幾個候選，留下讓總距離降最多的那個，與 sklearn 相同)
            candidates = rng.choice(n, size=trials, p=closest / total) if total > 0 else rng.randint(n, size=trials)
            options = np.minimum(closest[:, None], sq_dist(X[candidates].toarray()))
            best_option = int(np.argmin(options.sum(axis=0)))
            centers = np.vstack([centers, X[[candidates[best_option]]].toarray()])
            closest = options[:, best_option]
        labels = None
        for _ in range(max_iter):
            dist = sq_dist(centers)
            new = dist.argmin(axis=1)
            if labels is not None and np.array_equal(new, labels):
                break
            labels = new
            counts = np.bincount(labels, minlength=k)
            member = sparse.csr_matrix((1.0 / counts[labels], (labels, everyone)), shape=(k, n))
            centers = (member @ X).toarray()    # 每群的平均向量 (一次稀疏矩陣乘法)
            for c in np.flatnonzero(counts == 0):   # 空群：拿目前離中心最遠的點當新中心
                centers[c] = X[[dist.min(axis=1).argmax()]].toarray()[0]
        inertia = float(sq_dist(centers)[everyone, labels].sum())
        if inertia < best_inertia:
            best_labels, best_inertia = labels, inertia
    return best_labels


def _silhouette(distance, labels):
    """silhouette 平均分數 (與 sklearn.metrics.silhouette_score(metric="precomputed") 相同定義)。
    distance 是 N x N 距離矩陣；群數必須在 2 ~ N-1 之間。單篇群的分數算 0。"""
    n = len(labels)
    ids = np.unique(labels)
    own = np.searchsorted(ids, labels)
    counts = np.bincount(own, minlength=len(ids)).astype(np.float64)
    sums = np.stack([distance[:, own == c].sum(axis=1) for c in range(len(ids))], axis=1)   # 到各群的距離總和
    rows = np.arange(n)
    a = sums[rows, own] / np.maximum(counts[own] - 1.0, 1.0)     # 到自己群的平均距離 (不含自己)
    other = sums / counts[None, :]
    other[rows, own] = np.inf
    b = other.min(axis=1)                                        # 到最近的其他群的平均距離
    denominator = np.maximum(a, b)
    score = np.divide(b - a, denominator, out=np.zeros(n), where=denominator > 0)
    score[counts[own] == 1] = 0.0
    return float(score.mean())


def _kmeans_labeler(X):
    return lambda k: _kmeans(X, k)


def _hier_labeler(distance):
    tree = linkage(squareform(distance, checks=False), method="average")
    return lambda k: fcluster(tree, k, criterion="maxclust") - 1


def _choose_k(labeler, distance, k_fixed, k_min, k_max, min_size):
    """試各個 k，回傳 (silhouette, labels)；沒有可用的 k 時回傳 None。
    自動選 k 時，只考慮「每群至少 min_size 篇」的結果：階層式常把單一離群文件切成一群，silhouette 很漂亮
    但對使用者沒有幫助。手動指定 k 時照指定的切，不要求群大小。"""
    n = distance.shape[0]
    candidates = [k_fixed] if k_fixed else range(k_min, min(k_max, n // max(min_size, 1)) + 1)
    best = None
    for k in candidates:
        if k < 2 or k > n - 1:
            continue
        labels = np.asarray(labeler(k))
        counts = np.bincount(labels)
        counts = counts[counts > 0]
        if len(counts) < 2 or len(counts) > n - 1:     # silhouette 要求 2 <= 群數 <= n-1
            continue
        if not k_fixed and counts.min() < min_size:
            continue
        score = _silhouette(distance, labels)
        if best is None or score > best[0]:
            best = (score, labels)
    return best


def _label_terms(X, terms, labels, count, contrast):
    """每群回傳最多 count 個詞幹：群中心權重最高的詞。contrast=True 時先扣掉全體中心。
    候選詞：只含英文字母與數字 (ASCII)、不是純數字、不是到處都有的詞 (df 超過全部文件的 20%)，
    而且要在群內至少 30% 的文件出現 (最少 2 篇；群只有 1 篇時不限)，免得只出現在單一網站的怪詞
    (人名、代號、亂碼) 或 new、more 這類泛詞變成標籤。
    一個合格的詞都沒有時依序放寬：先改成「至少 2 篇」，再放寬「到處都有的詞」的限制。"""
    overall = np.asarray(X.mean(axis=0)).ravel()
    common_limit = _LABEL_MAX_DF * Search.TOTAL_DOCS

    def plain(term):
        return term.isascii() and term.isalnum() and not term.isdigit()

    def rare_enough(term):
        entry = Search.inverted_index.get(term)
        return entry is None or entry["df"] <= common_limit

    plain_mask = np.array([plain(term) for term in terms])
    strict_mask = plain_mask & np.array([rare_enough(term) for term in terms])
    result = []
    for cluster_id in sorted(set(labels.tolist())):
        members = np.flatnonzero(labels == cluster_id)
        sub = X[members]
        score = np.asarray(sub.mean(axis=0)).ravel()
        if contrast and len(set(labels.tolist())) > 1:
            score = score - overall
        in_cluster_docs = sub.getnnz(axis=0)
        need = max(2, math.ceil(0.3 * len(members))) if len(members) > 1 else 1

        def pick(mask, minimum):
            masked = np.where(mask & (in_cluster_docs >= minimum), score, -np.inf)
            top = np.argsort(-masked)[:count]
            return [terms[i] for i in top if masked[i] > 0]

        relaxed = min(2, len(members))
        result.append(pick(strict_mask, need) or pick(strict_mask, relaxed)
                      or pick(plain_mask, need) or pick(plain_mask, relaxed))
    return result


def _pca_2d(X):
    """PCA 前兩個主成分座標 (N x 2)。對 Gram 矩陣 (X X^T) 做雙重中心化再取特徵向量，結果等於對中心化資料做 PCA。"""
    n = X.shape[0]
    if n == 1:
        return np.zeros((1, 2))
    gram = (X @ X.T).toarray().astype(np.float64)
    gram = gram - gram.mean(axis=0, keepdims=True) - gram.mean(axis=1, keepdims=True) + gram.mean()
    values, vectors = np.linalg.eigh(gram)
    order = np.argsort(values)[::-1][:2]
    coords = vectors[:, order] * np.sqrt(np.maximum(values[order], 0.0))
    for column in range(coords.shape[1]):     # 固定正負號，同一組文件每次畫出來方向一致
        if coords[np.argmax(np.abs(coords[:, column])), column] < 0:
            coords[:, column] = -coords[:, column]
    if coords.shape[1] < 2:
        coords = np.hstack([coords, np.zeros((n, 1))])
    return coords


def analyze(doc_ids, method=CLUSTER_METHOD, k=None, contrast=True, query_terms=None, get_text=None, window=None):
    """分群並投影，回傳 dict (同一組參數的結果會快取)：
        method, k, silhouette (只有一群時為 None), elapsed_ms, timing_ms {vectors, cluster, project},
        no_structure (自動選 k 但分不出明顯的群，整批當一群；rejected_silhouette 是被拒絕的最佳分數 / None),
        clusters: [{id, terms (詞幹), doc_ids (依輸入順序), size}]  由大到小排序，id = 串列索引
        points:   [(doc_id, x, y, 群編號)]
        assignment: {doc_id: 群編號}
    doc_ids 要依排名由高到低給，群內文件才會保持排名順序。
    前後文分群：query_terms (查詢詞幹的集合) 與 get_text (doc_id -> 內文或 None) 都有給才啟用，window 預設
    CLUSTER_CONTEXT_WINDOW；結果多一個 "context": {window, docs_with_hits, docs}，整頁分群時為 None。
    內文裡找不到查詢詞的文件不分群 (不在 clusters / points / assignment 裡)；找得到的不到 3 篇時 no_structure 為 True。"""
    if method not in METHODS:
        raise ValueError(f"未知的分群方法：{method}")
    context = bool(query_terms) and get_text is not None
    window = (window or CLUSTER_CONTEXT_WINDOW) if context else None
    key = (tuple(doc_ids), method, k, contrast, frozenset(query_terms) if context else None, window)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    started = time.perf_counter()
    context_info = None
    if context:
        kept, X, terms = _submatrix_context(doc_ids, frozenset(query_terms), get_text, window)
        context_info = {"window": window, "docs_with_hits": len(kept), "docs": len(doc_ids)}
    else:
        kept, X, terms = _submatrix(doc_ids)
    X, terms = _prune_rare_terms(X, terms)
    n = len(kept)
    vectors_done = time.perf_counter()
    result = {"method": method, "k": 1 if n else 0, "silhouette": None, "no_structure": False,
              "rejected_silhouette": None, "context": context_info,
              "clusters": [], "points": [], "assignment": {}}
    if n:
        labels = np.zeros(n, dtype=int)
        if n >= 3:
            distance = _distance_matrix(X)
            labeler = _kmeans_labeler(X) if method == "kmeans" else _hier_labeler(distance)
            min_size = max(CLUSTER_MIN_SIZE, math.ceil(0.05 * n))
            best = _choose_k(labeler, distance, k, CLUSTER_K_MIN, CLUSTER_K_MAX, min_size)
            if best is not None and not k and best[0] < CLUSTER_MIN_SILHOUETTE:
                result["rejected_silhouette"] = best[0]
                best = None
            if best is not None:
                result["silhouette"], labels = best
            elif not k:
                result["no_structure"] = True
        cluster_done = time.perf_counter()
        # 群編號重排：大的群在前，同樣大小時最高排名文件在前的群在前
        raw_ids = sorted(set(labels.tolist()),
                         key=lambda c: (-int((labels == c).sum()), int(np.flatnonzero(labels == c)[0])))
        renumber = {old: new for new, old in enumerate(raw_ids)}
        labels = np.array([renumber[c] for c in labels.tolist()])
        label_terms = _label_terms(X, terms, labels, CLUSTER_LABEL_TERMS, contrast)
        for cluster_id, cluster_terms in enumerate(label_terms):
            members = [kept[i] for i in np.flatnonzero(labels == cluster_id)]
            result["clusters"].append({"id": cluster_id, "terms": cluster_terms,
                                       "doc_ids": members, "size": len(members)})
        result["k"] = len(label_terms)
        projected = time.perf_counter()
        coords = _pca_2d(X)
        result["timing_ms"] = {"vectors": (vectors_done - started) * 1000,
                               "cluster": (cluster_done - vectors_done) * 1000,
                               "project": (time.perf_counter() - projected) * 1000}
        result["points"] = [(kept[i], float(coords[i, 0]), float(coords[i, 1]), int(labels[i]))
                            for i in range(n)]
        result["assignment"] = {kept[i]: int(labels[i]) for i in range(n)}
    if context and n < 3:                       # 找得到查詢詞的文件太少，沒辦法分群
        result["no_structure"] = True
    result.setdefault("timing_ms", {"vectors": 0.0, "cluster": 0.0, "project": 0.0})
    result["elapsed_ms"] = (time.perf_counter() - started) * 1000

    with _lock:
        _cache[key] = result
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return result


def display_label(terms, surface=None):
    """標籤：詞用空白隔開 (INTERFACE.md)。surface 是 {詞幹: 原文常見寫法} (網頁顯示用，沒有就用詞幹)。"""
    surface = surface or {}
    return " ".join(surface.get(term, term) for term in terms) or "(其他)"


# ---------------------------------------------------------------- 介面約定的函式

def cluster(doc_ids, method=CLUSTER_METHOD, k=None, surface=None, query_terms=None, get_text=None, window=None):
    """介面約定：前 N 筆 doc ID -> [{"label", "doc_ids"}] (另有 "terms"、"size")。
    method：kmeans / hier；k：None 表示用 silhouette 自動選；surface：網頁顯示用，見 surface_forms()；
    query_terms、get_text、window：前後文分群 (選用)，見 analyze()。"""
    result = analyze(doc_ids, method, k, query_terms=query_terms, get_text=get_text, window=window)
    return [{"label": display_label(c["terms"], surface), "doc_ids": list(c["doc_ids"]),
             "terms": list(c["terms"]), "size": c["size"]} for c in result["clusters"]]


def project_2d(doc_ids, method=CLUSTER_METHOD, k=None, query_terms=None, get_text=None, window=None):
    """介面約定：前 N 筆 doc ID -> [(doc_id, x, y, 群編號)]；群編號就是 cluster() 回傳串列的索引。"""
    return list(analyze(doc_ids, method, k, query_terms=query_terms, get_text=get_text, window=window)["points"])


# ---------------------------------------------------------------- 命令列 (檢查分群結果用)

def main():
    parser = argparse.ArgumentParser(description="模組 B：搜尋結果分群 (命令列檢查用)")
    parser.add_argument("--top", type=Search.positive_int, default=CLUSTER_TOP_N,
                        help=f"對前 N 篇結果分群 (預設 {CLUSTER_TOP_N})")
    parser.add_argument("--method", choices=METHODS, default=CLUSTER_METHOD)
    parser.add_argument("--k", type=Search.positive_int, default=None, help="指定群數 (預設用 silhouette 自動選)")
    parser.add_argument("--weighting", choices=Search.WEIGHTING_SCHEMES, default=Search.DEFAULT_WEIGHTING,
                        help="搜尋結果的排序方案")
    parser.add_argument("--show", type=Search.positive_int, default=Search.TOP_K, help="每群顯示幾篇")
    args = parser.parse_args()

    Search.load_index()
    started = time.perf_counter()
    if not hasattr(Search, "get_doc_vector"):
        build_doc_matrix()
        print(f"文件矩陣建立完成 ({time.perf_counter() - started:.1f} 秒)")

    while True:
        query = input("\ncmd> ")
        if query.lower() == "exit":
            break
        if not query.strip():
            continue
        try:
            results, _, _ = Search.search(query, interactive=False, weighting=args.weighting, top_k=args.top)
        except ValueError as error:
            print(f"查詢錯誤：{error}")
            continue
        if not results:
            print("找不到符合的搜尋結果。")
            continue
        scores = dict(results)
        analysis = analyze([doc_id for doc_id, _ in results[:args.top]], args.method, args.k)
        silhouette = "-" if analysis["silhouette"] is None else f"{analysis['silhouette']:.3f}"
        timing = analysis["timing_ms"]
        print(f"前 {len(analysis['assignment'])} 篇分成 {analysis['k']} 群 "
              f"({METHOD_NAMES[args.method]}，silhouette {silhouette}，{analysis['elapsed_ms']:.0f} ms：向量 {timing['vectors']:.0f} + "
              f"分群 {timing['cluster']:.0f} + 投影 {timing['project']:.0f})")
        if analysis["no_structure"]:
            print("  " + no_structure_text(analysis))
        for c in analysis["clusters"]:
            print(f"\n[群 {c['id']}] {display_label(c['terms'])}  ({c['size']} 篇)")
            for doc_id in c["doc_ids"][:args.show]:
                print(f"    {doc_id}  {scores[doc_id]:.6f}")


# ---------------------------------------------------------------- 網頁前端片段 (交給 C 接進 WebApp.py)
# 只輸出 HTML 字串，不碰 WebApp.py。用法見 clustering_integration.md。

# 群的顏色 (淺色與深色模式都看得清楚)
PALETTE = ("#2455d8", "#e8590c", "#2b9348", "#9c36b5", "#d6336c", "#0c8599", "#a67c00", "#6c757d")

CLUSTER_CSS = """
.layout{display:grid;grid-template-columns:250px minmax(0,1fr);gap:18px;align-items:start;margin-top:8px}
@media (max-width:820px){.layout{grid-template-columns:1fr}}
.side{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 12px 8px;position:sticky;top:12px}
.side h2{font-size:15px;margin:0 0 2px}.side .meta{margin:2px 0 8px;font-size:12px}
.clusters{list-style:none;margin:0;padding:0}
.clusters a.cl{display:flex;align-items:center;gap:8px;padding:6px 8px;margin:2px 0;border-radius:8px;color:var(--fg);text-decoration:none;border:1px solid transparent}
.clusters a.cl:hover{background:var(--bg)}.clusters a.cl.active{border-color:var(--accent);background:var(--bg);font-weight:600}
.sw{flex:none;width:12px;height:12px;border-radius:50%}.sw.all{background:conic-gradient(#2455d8,#e8590c,#2b9348,#9c36b5,#2455d8)}
.cl-label{flex:1;min-width:0;overflow-wrap:anywhere}.n{flex:none;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.plot{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 10px 4px;margin-bottom:6px}
.plot svg{width:100%;height:auto;display:block}.plot .hint{color:var(--muted);font-size:12px;margin:0 0 2px}
.plot circle{stroke:var(--card);stroke-width:1;cursor:pointer}.plot a:hover circle{stroke:var(--fg);stroke-width:2}
.plot text{fill:var(--muted);font-size:10px}.plot .frame{fill:none;stroke:var(--line)}
.result.clustered{border-left-width:5px}.chip{display:inline-block;font-size:12px;color:var(--muted);margin-left:8px}
"""


def cluster_color(cluster_id):
    return PALETTE[cluster_id % len(PALETTE)]


def surface_forms(analysis, get_text, max_docs=15, max_chars=6000):
    """各群標籤用的詞幹 -> 原文常見寫法 (programm -> programming)，網頁顯示用。
    get_text(doc_id) 回傳文件內文，取不到 (例如 WARC 還沒掃完) 回傳 None。結果存在 analysis["surface"]。"""
    if "surface" in analysis:
        return analysis["surface"]
    wanted = {term for c in analysis["clusters"] for term in c["terms"]}
    counts = {term: Counter() for term in wanted}
    seen = False
    for c in analysis["clusters"]:
        for doc_id in c["doc_ids"][:max_docs]:
            text = get_text(doc_id)
            if not text:
                continue
            seen = True
            text = text[:max_chars]
            for start, end, stem in token_spans(text):
                if stem in wanted:
                    counts[stem][text[start:end].lower()] += 1
    surface = {term: c.most_common(1)[0][0] for term, c in counts.items() if c}
    if seen:                         # 一篇都沒讀到就不快取，下次再試
        analysis["surface"] = surface
    return surface


def doc_cluster_info(analysis, doc_id, surface=None):
    """文件所屬的群：回傳 (群編號, 顏色, 標籤)；不在分群範圍內回傳 None。結果卡片左邊的顏色條與標籤用。"""
    cluster_id = analysis["assignment"].get(doc_id)
    if cluster_id is None:
        return None
    label = display_label(analysis["clusters"][cluster_id]["terms"], surface)
    return cluster_id, cluster_color(cluster_id), label


def no_structure_text(analysis):
    """分不出群時的說明文字 (analysis["no_structure"] 為 True 時使用)。"""
    context = analysis.get("context")
    if context and context["docs_with_hits"] < 3:
        return (f"前後文分群需要在文件內文裡找到查詢詞，前 {context['docs']} 篇只有 {context['docs_with_hits']} 篇找到，"
                f"因此不分群。")
    detail = ""
    if analysis.get("rejected_silhouette") is not None:
        detail = f" (最佳 silhouette {analysis['rejected_silhouette']:.2f}，低於門檻 {CLUSTER_MIN_SILHOUETTE})"
    return f"前 {len(analysis['assignment'])} 篇沒有明顯的主題分群{detail}，因此不分群。"


def render_no_structure(analysis):
    """沒有明顯分群時的提示 HTML (用 WebApp 既有的 notice 樣式)。"""
    return f"<div class='notice'>{html.escape(no_structure_text(analysis))}</div>"


def render_sidebar(analysis, link, selected=None, surface=None):
    """左側欄 HTML：全部 + 各群 (顏色、標籤、篇數)。link(cluster_id 或 None) 回傳該群 (None = 全部) 的網址。"""
    method = METHOD_NAMES[analysis["method"]]
    silhouette = "" if analysis["silhouette"] is None else f"，silhouette {analysis['silhouette']:.2f}"
    total = len(analysis["assignment"])
    context = analysis.get("context")
    context_line = ""
    if context:
        left_out = context["docs"] - context["docs_with_hits"]
        context_line = (f"<br>依查詢詞前後文 ±{context['window']} 詞，{context['docs_with_hits']}/{context['docs']} 篇找到查詢詞"
                        + (f"，其餘 {left_out} 篇不分群" if left_out else "")
                        + f" (讀文與切詞 {analysis['timing_ms']['vectors']:.0f} ms)")
    items = [f"<li><a class='cl{' active' if selected is None else ''}' href='{html.escape(link(None))}'>"
             f"<span class='sw all'></span><span class='cl-label'>全部</span><span class='n'>{total}</span></a></li>"]
    for c in analysis["clusters"]:
        label = html.escape(display_label(c["terms"], surface))
        items.append(
            f"<li><a class='cl{' active' if selected == c['id'] else ''}' href='{html.escape(link(c['id']))}'>"
            f"<span class='sw' style='background:{cluster_color(c['id'])}'></span>"
            f"<span class='cl-label'>{label}</span><span class='n'>{c['size']}</span></a></li>")
    return (f"<aside class='side'><h2>結果分群</h2>"
            f"<div class='meta'>前 {total} 篇 → {analysis['k']} 群<br>{html.escape(method)}{silhouette} · "
            f"{analysis['elapsed_ms']:.0f} ms{context_line}</div><ul class='clusters'>{''.join(items)}</ul></aside>")


def render_scatter(analysis, doc_link, selected=None, titles=None, ranks=None, surface=None):
    """2D 散佈圖 (SVG，不需要 JavaScript)：一點一篇、顏色是所屬群、點下去打開該篇文件 (doc_link(doc_id) 回傳網址)；
    選了某群時其他群淡化。titles：{doc_id: 標題} (滑鼠移上去顯示，沒給就顯示 doc ID)；ranks：{doc_id: 名次}。"""
    points = analysis["points"]
    if len(points) < 2:
        return ""
    titles, ranks = titles or {}, ranks or {}
    width, height, pad = 560, 330, 22
    xs, ys = [p[1] for p in points], [p[2] for p in points]
    x_low, y_low = min(xs), min(ys)
    x_span, y_span = (max(xs) - x_low) or 1.0, (max(ys) - y_low) or 1.0
    labels = {c["id"]: display_label(c["terms"], surface) for c in analysis["clusters"]}
    circles = []
    for doc_id, x, y, cluster_id in sorted(points, key=lambda p: selected is not None and p[3] == selected):
        dim = selected is not None and cluster_id != selected    # 被選的群最後畫 (在最上層)
        cx = pad + (x - x_low) / x_span * (width - 2 * pad)
        cy = height - pad - (y - y_low) / y_span * (height - 2 * pad)
        tip = html.escape(f"{ranks.get(doc_id, '')}. {(titles.get(doc_id) or doc_id)[:80]}\n群 {cluster_id}：{labels[cluster_id]}")
        circles.append(
            f"<a href='{html.escape(doc_link(doc_id))}'><circle cx='{cx:.1f}' cy='{cy:.1f}' "
            f"r='{4 if dim else 5.5}' fill='{cluster_color(cluster_id)}' "
            f"opacity='{0.18 if dim else 0.85}'><title>{tip}</title></circle></a>")
    return (f"<div class='plot'><p class='hint'>每個點是一篇文件，顏色是所屬群，距離近代表內容相近；點一個點打開該篇文件</p>"
            f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='搜尋結果 2D 散佈圖'>"
            f"<rect class='frame' x='1' y='1' width='{width - 2}' height='{height - 2}' rx='6'/>"
            f"{''.join(circles)}"
            f"<text x='{width - pad}' y='{height - 6}' text-anchor='end'>PC1</text>"
            f"<text x='8' y='{pad - 8}'>PC2</text></svg></div>")


if __name__ == "__main__":
    main()