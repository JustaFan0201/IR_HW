"""評估程式：P@k、MAP、nDCG@k。模組 D。

介面 (與 TASKS.md 的約定一致)：
    evaluate(run, qrels) -> {"P@10": ..., "MAP": ..., "nDCG@10": ..., "Unjudged@10": ...}

    run   : {qid: [(docID, score), ...]}，已依分數高到低排好；也可以是 {qid: [docID, ...]}
    qrels : {qid: {docID: rel}}，rel = 0 (不相關)、1 (部分相關)、2 (高度相關)

定義：
    - 相關：rel >= 1。沒有標註過的文件一律當不相關 (pooling 評估的標準做法)。
    - P@k      = 前 k 名中相關文件數 / k
    - AP       = 每個相關文件出現位置的 P@i 平均，分母是 qrels 中該查詢的相關文件總數 R；
                 只看前 MAP_DEPTH (100) 名。MAP 是各查詢 AP 的平均。
    - nDCG@k   = DCG / IDCG，gain = 2^rel - 1，折扣 = log2(位置 + 1)；IDCG 由 qrels 的最佳排法算出。
    - Unjudged@k = 前 k 名中沒有標註過的比例，用來檢查結果可不可信 (越高代表標註越沒涵蓋這個方案)。
    - 沒有任何相關文件 (R = 0) 的查詢不納入平均 (沒有東西可找)。

qrels 檔格式是 TREC 標準：每行 `qid 0 docID rel`。
"""
import math
import random
from collections import defaultdict

MAP_DEPTH = 100


# ---------------------------------------------------------------- 檔案讀寫

def load_qrels(path):
    qrels = defaultdict(dict)
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 4 and not line.startswith("#"):
                qid, _, doc_id, rel = parts
                qrels[qid][doc_id] = int(rel)
    return dict(qrels)


def append_qrel(path, qid, doc_id, rel):
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{qid} 0 {doc_id} {rel}\n")


def load_queries(path):
    """eval_queries.txt：`qid<TAB>查詢<TAB>類型`，回傳 [(qid, query, type)]。# 開頭為註解。"""
    queries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.rstrip("\n").split("\t")
                queries.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return queries


def write_run(path, run, name):
    """寫成 TREC run 格式 (`qid Q0 docID rank score name`)，可直接給 trec_eval 用。"""
    with open(path, "w", encoding="utf-8") as f:
        for qid, ranked in run.items():
            for rank, item in enumerate(ranked, 1):
                doc_id, score = item if isinstance(item, tuple) else (item, 0.0)
                f.write(f"{qid} Q0 {doc_id} {rank} {score:.6f} {name}\n")


# ---------------------------------------------------------------- 單一查詢的指標

def _doc_ids(ranked):
    return [item[0] if isinstance(item, tuple) else item for item in ranked]


def precision_at_k(ranked, judgments, k=10):
    docs = _doc_ids(ranked)[:k]
    return sum(1 for d in docs if judgments.get(d, 0) >= 1) / k


def average_precision(ranked, judgments, depth=MAP_DEPTH):
    total_relevant = sum(1 for r in judgments.values() if r >= 1)
    if total_relevant == 0:
        return 0.0
    hits, ap = 0, 0.0
    for i, d in enumerate(_doc_ids(ranked)[:depth], 1):
        if judgments.get(d, 0) >= 1:
            hits += 1
            ap += hits / i
    return ap / total_relevant


def ndcg_at_k(ranked, judgments, k=10):
    gain = lambda rel: 2 ** rel - 1
    dcg = sum(gain(judgments.get(d, 0)) / math.log2(i + 1)
              for i, d in enumerate(_doc_ids(ranked)[:k], 1))
    ideal = sorted(judgments.values(), reverse=True)[:k]
    idcg = sum(gain(r) / math.log2(i + 1) for i, r in enumerate(ideal, 1))
    return dcg / idcg if idcg > 0 else 0.0


def unjudged_at_k(ranked, judgments, k=10):
    docs = _doc_ids(ranked)[:k]
    return sum(1 for d in docs if d not in judgments) / k


# ---------------------------------------------------------------- 整組查詢

def evaluate_per_query(run, qrels, k=10):
    """回傳 {qid: {"P@k", "AP", "nDCG@k", "Unjudged@k"}}，只含 qrels 中有相關文件的查詢。"""
    per_query = {}
    for qid, judgments in qrels.items():
        if qid not in run or not any(r >= 1 for r in judgments.values()):
            continue
        ranked = run[qid]
        per_query[qid] = {
            f"P@{k}": precision_at_k(ranked, judgments, k),
            "AP": average_precision(ranked, judgments),
            f"nDCG@{k}": ndcg_at_k(ranked, judgments, k),
            f"Unjudged@{k}": unjudged_at_k(ranked, judgments, k),
        }
    return per_query


def evaluate(run, qrels, k=10):
    """各查詢平均：{"P@10", "MAP", "nDCG@10", "Unjudged@10"}。"""
    per_query = evaluate_per_query(run, qrels, k)
    if not per_query:
        return {f"P@{k}": 0.0, "MAP": 0.0, f"nDCG@{k}": 0.0, f"Unjudged@{k}": 0.0}
    mean = lambda key: sum(m[key] for m in per_query.values()) / len(per_query)
    return {f"P@{k}": mean(f"P@{k}"), "MAP": mean("AP"),
            f"nDCG@{k}": mean(f"nDCG@{k}"), f"Unjudged@{k}": mean(f"Unjudged@{k}")}


def paired_randomization_test(scores_a, scores_b, trials=10000, seed=0):
    """配對隨機化檢定 (sign-flip)：兩方案逐查詢分數差的平均是否顯著不為 0。
    scores_a / scores_b 是 {qid: 分數}；回傳雙尾 p 值。查詢只有 20～30 個，p 值只能當參考。"""
    diffs = [scores_a[q] - scores_b[q] for q in scores_a if q in scores_b]
    if not diffs:
        return 1.0
    rng = random.Random(seed)
    observed = abs(sum(diffs))
    extreme = sum(
        1 for _ in range(trials)
        if abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= observed - 1e-12
    )
    return extreme / trials


if __name__ == "__main__":
    # 自我檢查：用手算得出答案的小例子驗證公式
    j = {"a": 2, "b": 0, "c": 1, "d": 1}          # R = 3，最佳排序 a, c, d
    run = ["a", "x", "c", "y", "d"]
    assert abs(precision_at_k(run, j, 5) - 3 / 5) < 1e-9
    assert abs(average_precision(run, j) - (1 / 1 + 2 / 3 + 3 / 5) / 3) < 1e-9
    dcg = 3 / math.log2(2) + 1 / math.log2(4) + 1 / math.log2(6)
    idcg = 3 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
    assert abs(ndcg_at_k(run, j, 5) - dcg / idcg) < 1e-9
    assert unjudged_at_k(run, j, 5) == 2 / 5
    res = evaluate({"q": run}, {"q": j}, k=5)
    assert abs(res["nDCG@5"] - dcg / idcg) < 1e-9
    print("Evaluate.py 自我檢查通過")
