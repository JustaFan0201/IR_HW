"""Pooling 與相關性標註。模組 D。

流程：各方案取前 depth 筆合併成候選集 (pool)，人工標註，存成 qrels (TREC 格式)。
新方案 (語意、混合、回饋) 完成後重跑一次，只會問「還沒標註過」的文件。

    # 1. 互動標註 (終端機，每標一筆就存檔，可隨時中斷、下次接著做)
    python SourceCode/Pooling.py annotate --methods tfidf bm25 --depth 20
    python SourceCode/Pooling.py annotate --queries Q01 Q02        # 只標指定查詢，方便組員分工

    # 2. 或匯出 CSV 用試算表標註，填完 rel 欄位再合併
    python SourceCode/Pooling.py export --methods tfidf bm25 --depth 20 --out eval/pool.csv
    python SourceCode/Pooling.py merge eval/pool.csv

    # 3. 看標註進度與每個查詢的相關文件數
    python SourceCode/Pooling.py status

相關性等級 (標註準則)：
    2 高度相關：頁面主要內容就是這個主題，使用者會直接滿意
    1 部分相關：有提到、或只是主題的一小部分、或屬於多義詞的其中一種意思但內容有用
    0 不相關
多義詞查詢 (類型 ambiguous)：頁面主要談的是任何一種意思，都算相關；
同一個頁面若只是順帶出現該詞 (例如頁尾廣告、導覽列) 給 0。
"""
import argparse
import csv
import os
import sys

import Methods
import Search as S
from config import BASE_DIR
from Evaluate import append_qrel, load_qrels, load_queries

EVAL_DIR = os.path.join(BASE_DIR, "eval")
QUERIES_PATH = os.path.join(EVAL_DIR, "eval_queries.txt")
QRELS_PATH = os.path.join(EVAL_DIR, "qrels.txt")


def build_pool(queries, method_names, depth):
    """回傳 {qid: {docID: [提供這筆的方案]}}，保持各方案排名順序。"""
    pool = {}
    for qid, query, _ in queries:
        docs = {}
        for name in method_names:
            for doc_id, _ in Methods.METHODS[name](query, depth):
                docs.setdefault(doc_id, []).append(name)
        pool[qid] = docs
    return pool


def _doc_store():
    """嘗試讀 WARC 以顯示標題與摘要；找不到檔案時回傳 None (標註時只看得到文件編號)。"""
    from config import WARC_FILE_PATH
    from WebApp import DocStore
    store = DocStore(WARC_FILE_PATH)
    if not store.available:
        print(f"[提醒] 找不到 WARC 檔 {WARC_FILE_PATH}，沒有標題與內文可看，無法標註。")
        return None
    print("掃描 WARC ...")
    store.scan()
    return store


def _snippet(store, doc_id, query, chars=500):
    if store is None:
        return "", ""
    got = store.get(doc_id)
    if got is None:
        return "(WARC 中找不到此文件)", ""
    title, text = got
    from analyzer import analyze, token_spans
    terms = set(analyze(query))
    hits = [s for s, _, stem in token_spans(text) if stem in terms]
    start = max(0, hits[0] - 100) if hits else 0
    return (title or "(無標題)"), " ".join(text[start:start + chars].split())


def cmd_annotate(args, queries):
    pool = build_pool(queries, args.methods, args.depth)
    qrels = load_qrels(QRELS_PATH) if os.path.exists(QRELS_PATH) else {}
    store = _doc_store()
    if store is None:
        return
    todo = [(qid, q, t) for qid, q, t in queries if not args.queries or qid in args.queries]
    total = sum(1 for qid, _, _ in todo for d in pool[qid] if d not in qrels.get(qid, {}))
    done = 0
    print(f"\n待標註 {total} 筆。輸入 2 / 1 / 0；s 跳過；q 離開 (進度已存檔)。標錯時直接在 qrels.txt 末尾補一行同 qid／docID 的新標註 (後面的覆蓋前面的)。\n")
    for qid, query, qtype in todo:
        for doc_id, sources in pool[qid].items():
            if doc_id in qrels.get(qid, {}):
                continue
            title, snippet = _snippet(store, doc_id, query)
            while True:
                print(f"[{done + 1}/{total}] {qid} 「{query}」({qtype})   來源：{','.join(sources)}")
                print(f"  {doc_id}\n  標題：{title}\n  內文：{snippet}")
                answer = input("  相關性 (2/1/0/s/q)> ").strip().lower()
                if answer in ("0", "1", "2"):
                    append_qrel(QRELS_PATH, qid, doc_id, int(answer))
                    qrels.setdefault(qid, {})[doc_id] = int(answer)
                    done += 1
                    print()
                    break
                if answer == "s":
                    print()
                    break
                if answer == "q":
                    print(f"已標 {done} 筆，結束。")
                    return
    print(f"全部完成，本次標 {done} 筆。")


def cmd_export(args, queries):
    pool = build_pool(queries, args.methods, args.depth)
    qrels = load_qrels(QRELS_PATH) if os.path.exists(QRELS_PATH) else {}
    store = _doc_store()
    rows = 0
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig 讓 Excel 正確顯示中文
        writer = csv.writer(f)
        writer.writerow(["qid", "query", "type", "docID", "sources", "title", "snippet", "rel"])
        for qid, query, qtype in queries:
            for doc_id, sources in pool[qid].items():
                if doc_id in qrels.get(qid, {}):
                    continue
                title, snippet = _snippet(store, doc_id, query)
                writer.writerow([qid, query, qtype, doc_id, "+".join(sources), title, snippet, ""])
                rows += 1
    print(f"已匯出 {rows} 筆未標註的候選文件到 {args.out}；在 rel 欄填 0/1/2 後用 merge 合併。")


def cmd_merge(args, queries):
    existing = load_qrels(QRELS_PATH) if os.path.exists(QRELS_PATH) else {}
    added = skipped = 0
    for path in args.files:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rel = row["rel"].strip()
                if rel not in ("0", "1", "2"):
                    skipped += 1
                    continue
                if row["docID"] in existing.get(row["qid"], {}):
                    continue
                append_qrel(QRELS_PATH, row["qid"], row["docID"], int(rel))
                existing.setdefault(row["qid"], {})[row["docID"]] = int(rel)
                added += 1
    print(f"合併 {added} 筆；{skipped} 筆 rel 欄空白或格式不對，已略過。")


def cmd_status(args, queries):
    qrels = load_qrels(QRELS_PATH) if os.path.exists(QRELS_PATH) else {}
    print(f"{'qid':<5}{'查詢':<34}{'已標':>5}{'rel=2':>7}{'rel=1':>7}{'rel=0':>7}")
    for qid, query, _ in queries:
        j = qrels.get(qid, {})
        count = lambda r: sum(1 for v in j.values() if v == r)
        flag = "  <- 沒有相關文件，評估會略過" if j and count(1) + count(2) == 0 else ""
        print(f"{qid:<5}{query:<34}{len(j):>5}{count(2):>7}{count(1):>7}{count(0):>7}{flag}")


def main():
    parser = argparse.ArgumentParser(description="Pooling 與相關性標註")
    parser.add_argument("command", choices=["annotate", "export", "merge", "status"])
    parser.add_argument("files", nargs="*", help="merge 用：要合併的 CSV")
    parser.add_argument("--methods", nargs="+", default=["tfidf", "bm25"])
    parser.add_argument("--depth", type=int, default=20)
    parser.add_argument("--queries", nargs="+", help="只處理指定的 qid")
    parser.add_argument("--out", default=os.path.join(EVAL_DIR, "pool.csv"))
    parser.add_argument("--plugins", nargs="*", default=[], help="載入其他組員的方法模組")
    args = parser.parse_args()

    queries = load_queries(QUERIES_PATH)
    if args.command in ("merge", "status"):
        return {"merge": cmd_merge, "status": cmd_status}[args.command](args, queries)

    S.load_index()
    Methods.load_plugins(args.plugins)
    unknown = [m for m in args.methods if m not in Methods.METHODS]
    if unknown:
        sys.exit(f"未知的方法：{unknown}；可用：{sorted(Methods.METHODS)}")
    {"annotate": cmd_annotate, "export": cmd_export}[args.command](args, queries)


if __name__ == "__main__":
    main()
