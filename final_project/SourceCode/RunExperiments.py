"""比較各排序方案：P@10、MAP、nDCG@10。模組 D。

    python SourceCode/RunExperiments.py                                  # baseline：tfidf、tfidf-raw、bm25、lm
    python SourceCode/RunExperiments.py --plugins SemanticSearch Feedback  # 加入 A、C 的方法
    python SourceCode/RunExperiments.py --methods bm25 lm --baseline bm25
    python SourceCode/RunExperiments.py --sweep-mu 100 500 1000 2000 5000 # 語言模型的 mu 掃描

輸出 (eval/results/)：
    summary.csv       各方案整體指標
    per_query.csv     每個查詢、每個方案的指標 (找出哪些查詢哪個方法贏或輸)
    by_type.csv       依查詢類型 (ambiguous / synonym / general) 分開的指標
    runs/<方案>.run   TREC 格式的排序結果 (可給 trec_eval)
    comparison.png    長條圖 (需要 matplotlib，沒裝就略過)

注意：
    - 沒標註過的文件視為不相關。Unjudged@10 高的方案 (通常是 pooling 之後才加入的新方法)
      分數會被低估，先用 Pooling.py annotate 把它的前 10～20 名補標再比較。
    - 調 mu、α 等參數和最後報告數字用同一份 qrels 會偏樂觀；
      報告時說明這點，或把查詢分成「調參用」與「測試用」兩半。
"""
import argparse
import csv
import os

import Methods
import Search as S
from config import BASE_DIR
from Evaluate import (evaluate, evaluate_per_query, load_qrels, load_queries,
                      paired_randomization_test, write_run)

EVAL_DIR = os.path.join(BASE_DIR, "eval")
RESULT_DIR = os.path.join(EVAL_DIR, "results")
DEPTH = 100          # 每個查詢取前 100 名 (MAP 看到第 100 名)
K = 10
METRICS = ["P@10", "MAP", "nDCG@10", "Unjudged@10"]


def run_method(name, queries):
    fn = Methods.METHODS[name]
    return {qid: fn(query, DEPTH) for qid, query, _ in queries}


def markdown_table(rows, header):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def save_chart(summary, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(沒有 matplotlib，略過長條圖)")
        return
    names = list(summary)
    metrics = ["P@10", "MAP", "nDCG@10"]
    width = 0.8 / len(metrics)
    fig, ax = plt.subplots(figsize=(max(6, 1.4 * len(names) + 2), 4))
    for i, metric in enumerate(metrics):
        xs = [x + i * width for x in range(len(names))]
        bars = ax.bar(xs, [summary[n][metric] for n in names], width, label=metric)
        ax.bar_label(bars, fmt="%.2f", fontsize=7)
    ax.set_xticks([x + width for x in range(len(names))])
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylim(0, 1)
    ax.set_title("Retrieval effectiveness")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"已存圖：{path}")


def main():
    parser = argparse.ArgumentParser(description="排序方案比較實驗")
    parser.add_argument("--methods", nargs="+", default=["tfidf", "tfidf-raw", "bm25", "lm"])
    parser.add_argument("--plugins", nargs="*", default=[], help="載入其他組員的方法模組")
    parser.add_argument("--baseline", default="bm25", help="顯著性檢定的對照方案")
    parser.add_argument("--sweep-mu", type=float, nargs="+", help="只做語言模型 mu 的掃描")
    parser.add_argument("--qrels", default=os.path.join(EVAL_DIR, "qrels.txt"))
    parser.add_argument("--queries", default=os.path.join(EVAL_DIR, "eval_queries.txt"))
    args = parser.parse_args()

    queries = load_queries(args.queries)
    qrels = load_qrels(args.qrels)
    types = {qid: qtype for qid, _, qtype in queries}
    judged = [qid for qid, _, _ in queries if any(r >= 1 for r in qrels.get(qid, {}).values())]
    print(f"{len(queries)} 個查詢，其中 {len(judged)} 個有相關文件標註 (只有這些會納入平均)")
    if not judged:
        raise SystemExit("還沒有標註資料：先用 Pooling.py 標註 (見 Pooling.py 開頭的說明)。")

    S.load_index()

    if args.sweep_mu:
        print("\n語言模型 mu 掃描 (Dirichlet 平滑)：")
        rows = []
        for mu in args.sweep_mu:
            Methods.register(f"lm-mu{mu:g}", Methods.lm_with_mu(mu))
            m = evaluate(run_method(f"lm-mu{mu:g}", queries), qrels, K)
            rows.append([f"{mu:g}"] + [f"{m[k]:.4f}" for k in METRICS])
        print(markdown_table(rows, ["mu"] + METRICS))
        return

    Methods.load_plugins(args.plugins)
    names = [m for m in args.methods + [p for p in Methods.METHODS if p not in args.methods and p not in
             ("tfidf", "tfidf-raw", "bm25", "lm")] if m in Methods.METHODS]

    os.makedirs(os.path.join(RESULT_DIR, "runs"), exist_ok=True)
    runs, summary, per_query = {}, {}, {}
    for name in names:
        runs[name] = run_method(name, queries)
        write_run(os.path.join(RESULT_DIR, "runs", f"{name}.run"), runs[name], name)
        summary[name] = evaluate(runs[name], qrels, K)
        per_query[name] = evaluate_per_query(runs[name], qrels, K)

    # ---- 整體
    print("\n整體結果 (各查詢平均)：")
    print(markdown_table([[n] + [f"{summary[n][k]:.4f}" for k in METRICS] for n in names], ["方法"] + METRICS))
    with open(os.path.join(RESULT_DIR, "summary.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["method"] + METRICS)
        for n in names:
            w.writerow([n] + [f"{summary[n][k]:.4f}" for k in METRICS])

    # ---- 依查詢類型
    type_names = sorted({types[q] for q in judged})
    print("\n依查詢類型 (nDCG@10 / MAP)：")
    rows, csv_rows = [], []
    for n in names:
        row = [n]
        for t in type_names:
            sub_qrels = {q: j for q, j in qrels.items() if types.get(q) == t}
            m = evaluate(runs[n], sub_qrels, K)
            row.append(f"{m['nDCG@10']:.3f} / {m['MAP']:.3f}")
            csv_rows.append([n, t, f"{m['P@10']:.4f}", f"{m['MAP']:.4f}", f"{m['nDCG@10']:.4f}"])
        rows.append(row)
    print(markdown_table(rows, ["方法"] + [f"{t} ({sum(1 for q in judged if types[q] == t)})" for t in type_names]))
    with open(os.path.join(RESULT_DIR, "by_type.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["method", "type", "P@10", "MAP", "nDCG@10"])
        w.writerows(csv_rows)

    # ---- 逐查詢
    with open(os.path.join(RESULT_DIR, "per_query.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["qid", "query", "type", "method", "P@10", "AP", "nDCG@10", "Unjudged@10"])
        for qid, query, qtype in queries:
            for n in names:
                m = per_query[n].get(qid)
                if m:
                    w.writerow([qid, query, qtype, n, f"{m['P@10']:.4f}", f"{m['AP']:.4f}",
                                f"{m['nDCG@10']:.4f}", f"{m['Unjudged@10']:.2f}"])

    # ---- 顯著性 (nDCG@10，對 baseline)
    if args.baseline in per_query:
        print(f"\n對 {args.baseline} 的 nDCG@10 差異 (配對隨機化檢定；只有 {len(judged)} 個查詢，p 值僅供參考)：")
        base = {q: m["nDCG@10"] for q, m in per_query[args.baseline].items()}
        rows = []
        for n in names:
            if n == args.baseline:
                continue
            other = {q: m["nDCG@10"] for q, m in per_query[n].items()}
            diff = sum(other[q] - base[q] for q in base) / len(base)
            wins = sum(1 for q in base if other[q] > base[q] + 1e-9)
            losses = sum(1 for q in base if other[q] < base[q] - 1e-9)
            rows.append([n, f"{diff:+.4f}", f"{wins} / {losses}", f"{paired_randomization_test(other, base):.3f}"])
        print(markdown_table(rows, ["方法", "平均差", "贏 / 輸 (查詢數)", "p"]))

    # ---- 標註涵蓋度警告
    risky = [n for n in names if summary[n]["Unjudged@10"] > 0.2]
    if risky:
        print(f"\n[注意] {', '.join(risky)} 的前 10 名有超過 20% 沒標註過，分數可能被低估。"
              "請先 `Pooling.py annotate --methods ...` 補標。")

    save_chart(summary, os.path.join(RESULT_DIR, "comparison.png"))
    print(f"\n結果已存到 {RESULT_DIR}")


if __name__ == "__main__":
    main()
