"""比較精確計分與 champion list 近似計分的速度與排名差異。

python SourceCode/Benchmark.py
python SourceCode/Benchmark.py --sizes 20 100 500 --repeat 50 --weighting bm25

只量「計分與排序」(rank_documents) 的時間；查詢先經過 analyze，不含拼字檢查與布林運算。
重疊率 = champion 前 10 名與精確前 10 名共有的文件比例。
"""
import argparse
import time

import Search as S
from analyzer import analyze

QUERIES = [
    "business",
    "hong kong business",
    "united states government",
    "free software download",
    "home page information",
    "airplanes",
    "linux",
    "microsoft windows",
    "health care",
    "school education",
    "open source software",
    "online shopping",
]


def mean_time(terms, weighting, use_champion, top_k, repeat):
    start = time.perf_counter()
    for _ in range(repeat):
        results = S.rank_documents(terms, None, weighting, use_champion, min_results=top_k)
    return (time.perf_counter() - start) / repeat, results


def main():
    parser = argparse.ArgumentParser(description="champion list 效能與排名差異比較")
    parser.add_argument("--sizes", type=int, nargs="+", default=[50, 200, 1000],
                        help="要測試的 champion list 大小 R")
    parser.add_argument("--repeat", type=int, default=30, help="每個查詢重複計時幾次")
    parser.add_argument("--top", type=int, default=10, help="比較前幾名")
    parser.add_argument("--weighting", choices=S.WEIGHTING_SCHEMES, default="tfidf")
    args = parser.parse_args()

    S.load_index()
    queries = [(q, analyze(q)) for q in QUERIES]

    # 精確計分當基準
    exact = {}
    exact_total = 0.0
    for query, terms in queries:
        seconds, results = mean_time(terms, args.weighting, False, args.top, args.repeat)
        exact[query] = [doc for doc, _ in results[:args.top]]
        exact_total += seconds
    print(f"\n權重方案 {args.weighting}，{len(queries)} 個查詢，每個重複 {args.repeat} 次")
    print(f"精確計分平均：{exact_total / len(queries) * 1000:.2f} ms/查詢\n")

    print(f"{'R':>6} {'建立(s)':>8} {'champion 詞數':>14} {'平均 ms':>9} {'加速':>6} "
          f"{'前%d重疊' % args.top:>9} {'退回精確':>8}")
    for size in args.sizes:
        start = time.perf_counter()
        count = S.build_champion_lists(size, args.weighting)
        build_seconds = time.perf_counter() - start

        total = 0.0
        overlap = 0.0
        fallbacks = 0
        for query, terms in queries:
            seconds, results = mean_time(terms, args.weighting, True, args.top, args.repeat)
            total += seconds
            top = [doc for doc, _ in results[:args.top]]
            overlap += len(set(top) & set(exact[query])) / args.top
            # 退回精確的查詢，其結果與精確計分完全相同
            if S.rank_documents(terms, None, args.weighting, True, 0) != results:
                fallbacks += 1
        mean_ms = total / len(queries) * 1000
        print(f"{size:>6} {build_seconds:>8.2f} {count:>14} {mean_ms:>9.2f} "
              f"{exact_total / total:>5.1f}x {overlap / len(queries):>9.0%} {fallbacks:>8}")


if __name__ == "__main__":
    main()
