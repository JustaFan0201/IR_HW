"""語意檢索 (模組 C)。

離線：python semantic.py --build
    掃 WARC，每篇取「標題 + 內文前 SEMANTIC_BODY_WORDS 個字」用 sentence-transformers 編碼，
    向量 (已 L2 正規化) 存成 SEMANTIC_VECTORS_PATH，doc ID 順序存成 SEMANTIC_IDS_PATH。
    沒有內文的文件存零向量，語意分數即為 0。
查詢：semantic_search(query, k) -> [(doc_id, cosine 分數)]
"""
import argparse
import os
import time

import numpy as np

from config import (SEMANTIC_BATCH_SIZE, SEMANTIC_BODY_WORDS, SEMANTIC_IDS_PATH, SEMANTIC_MODEL,
                    SEMANTIC_VECTORS_PATH, WARC_FILE_PATH)

_state = {"model": None, "vectors": None, "doc_ids": None}


def _model():
    if _state["model"] is None:
        from sentence_transformers import SentenceTransformer
        _state["model"] = SentenceTransformer(SEMANTIC_MODEL, device="cpu")
    return _state["model"]


def load_vectors():
    """載入預先算好的文件向量；semantic_search 第一次呼叫時會自動載入。"""
    if _state["vectors"] is None:
        if not (os.path.exists(SEMANTIC_VECTORS_PATH) and os.path.exists(SEMANTIC_IDS_PATH)):
            raise FileNotFoundError(f"找不到語意向量檔 {SEMANTIC_VECTORS_PATH}，請先執行 python semantic.py --build")
        with open(SEMANTIC_IDS_PATH, encoding="utf-8") as f:
            doc_ids = [line.rstrip("\n") for line in f]
        vectors = np.load(SEMANTIC_VECTORS_PATH)
        # 兩個檔對不上 (只重建了一個、或 --build 中途中斷) 時，分數會默默對到錯的 doc ID
        if vectors.ndim != 2 or len(doc_ids) != vectors.shape[0]:
            raise ValueError(f"語意向量檔與 doc ID 檔不一致 (向量 {vectors.shape}、ID {len(doc_ids)} 筆)，"
                             f"請重新執行 python semantic.py --build")
        _state["doc_ids"], _state["vectors"] = doc_ids, vectors
    return _state["vectors"], _state["doc_ids"]


def encode_query(query):
    return _model().encode([query], normalize_embeddings=True)[0].astype(np.float32)


def semantic_search(query, k=10):
    """query 是原始查詢字串（不經 analyzer）。回傳 [(doc_id, cosine 分數)]，分數高到低。"""
    if not query.strip() or k <= 0:
        return []
    vectors, doc_ids = load_vectors()
    scores = vectors @ encode_query(query)
    k = min(k, len(scores))
    top = np.argpartition(-scores, k - 1)[:k]
    top = top[np.argsort(-scores[top])]
    return [(doc_ids[i], float(scores[i])) for i in top]


# ---------------------------------------------------------------- 離線編碼

def doc_text(title, body):
    """編碼用的文字：標題 + 內文前 SEMANTIC_BODY_WORDS 個字 (FirstP，模型最多讀 256 token)；沒有內文回傳空字串。"""
    words = body.split()[:SEMANTIC_BODY_WORDS]
    if not words:
        return ""
    return f"{title.strip()}. {' '.join(words)}" if title.strip() else " ".join(words)


def build():
    import Search
    from docs import html_to_text, iter_responses

    Search.load_index()
    index_ids = set(Search.doc_lengths)
    print(f"索引共 {len(index_ids)} 篇，開始從 WARC 取文字：{WARC_FILE_PATH}")

    start = time.time()
    texts = {}
    with open(WARC_FILE_PATH, "rb") as f:
        for doc_id, _, _, block in iter_responses(f):
            if doc_id in index_ids:
                texts[doc_id] = doc_text(*html_to_text(block))
    doc_ids = sorted(index_ids)
    missing = [d for d in doc_ids if d not in texts]
    to_encode = [d for d in doc_ids if texts.get(d)]
    print(f"取文字完成 ({time.time() - start:.0f} 秒)：有內文 {len(to_encode)} 篇，"
          f"無內文 {len(doc_ids) - len(to_encode)} 篇 (其中 WARC 找不到 {len(missing)} 篇)")

    model = _model()
    # sentence-transformers 5.x 改名為 get_embedding_dimension，舊版只有 get_sentence_embedding_dimension
    dimension = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
    vectors = np.zeros((len(doc_ids), dimension()), dtype=np.float32)
    if to_encode:
        start = time.time()
        encoded = model.encode([texts[d] for d in to_encode], batch_size=SEMANTIC_BATCH_SIZE,
                               normalize_embeddings=True, show_progress_bar=True).astype(np.float32)
        elapsed = time.time() - start
        print(f"編碼完成 ({elapsed:.0f} 秒，{len(to_encode) / max(elapsed, 1e-9):.0f} 篇/秒)")
        row = {d: i for i, d in enumerate(doc_ids)}
        vectors[[row[d] for d in to_encode]] = encoded
    else:
        print("警告：沒有任何文件有內文 (WARC 的 doc ID 可能與索引對不上)，全部存成零向量")
    np.save(SEMANTIC_VECTORS_PATH, vectors)
    with open(SEMANTIC_IDS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(doc_ids) + "\n")
    print(f"已存檔：{SEMANTIC_VECTORS_PATH} {vectors.shape}、{SEMANTIC_IDS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="語意檢索 (sentence-transformers)")
    parser.add_argument("--build", action="store_true", help="編碼全部文件並存檔")
    parser.add_argument("query", nargs="*", help="查詢字串 (不加 --build 時)")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    if args.build:
        build()
    elif args.query:
        for rank, (doc_id, score) in enumerate(semantic_search(" ".join(args.query), args.top), 1):
            print(f"{rank:>3}. {doc_id}  {score:.4f}")
    else:
        parser.print_help()
