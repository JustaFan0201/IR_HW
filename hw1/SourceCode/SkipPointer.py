"""選做加分：為 postings 加上 skip pointer，並示範 AND 查詢能少比幾次。

用法：
  python SkipPointer.py build                 讀 HW1.txt，輸出 HW1_skip.txt
  python SkipPointer.py query 詞1 詞2         AND 查詢，比較有無 skip 的比對次數
                                              (詞要用索引裡的形式，例如開了詞幹還原就要輸入 download，不是 downloads)
"""
import sys
import math
from config import OUTPUT_FILE_PATH, SKIP_FILE_PATH, SKIP_MIN_DF


def parse_line(line):
    """'term, df: <p1; p2; ...>' -> (term, [p1, p2, ...])，每個 p 是 'docID, tf: <位置...>'。"""
    head, _, rest = line.rstrip("\n").partition(": <")
    term, _, _df = head.rpartition(", ")
    return term, rest[:-1].split("; ")


def build():
    """每隔 √df 筆放一個 skip pointer，寫成 '... ->目標位置'。標準輸出檔 HW1.txt 不動。"""
    with open(OUTPUT_FILE_PATH, encoding="utf-8") as src, open(SKIP_FILE_PATH, "w", encoding="utf-8") as dst:
        for line in src:
            term, postings = parse_line(line)
            df = len(postings)
            if df >= SKIP_MIN_DF:
                step = int(math.sqrt(df))
                for i in range(0, df - step, step):
                    postings[i] += f" ->{i + step}"
            dst.write(f"{term}, {df}: <{'; '.join(postings)}>\n")
    print(f"完成！{SKIP_FILE_PATH}")


def load(terms):
    """掃一次 HW1_skip.txt，取出指定詞的 (docID 清單, skip 目標清單)。"""
    found = {}
    with open(SKIP_FILE_PATH, encoding="utf-8") as f:
        for line in f:
            head = line.split(": <", 1)[0]
            term = head.rpartition(", ")[0]
            if term not in terms:
                continue
            docs, skips = [], []
            for p in parse_line(line)[1]:
                docs.append(p.split(",", 1)[0])
                skips.append(int(p.rsplit("->", 1)[1]) if "->" in p else None)
            found[term] = (docs, skips)
            if len(found) == len(terms):
                break
    return found


def intersect_plain(a, b):
    """一般的雙指標合併。回傳 (交集, 比對次數)。"""
    i = j = comps = 0
    out = []
    while i < len(a) and j < len(b):
        comps += 1
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return out, comps


def intersect_skip(a, a_skip, b, b_skip):
    """有 skip 的合併：落後的一邊，若跳過去的位置仍不超過對方，就直接跳。"""
    i = j = comps = 0
    out = []
    while i < len(a) and j < len(b):
        comps += 1
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif a[i] < b[j]:
            while a_skip[i] is not None:
                comps += 1
                if a[a_skip[i]] <= b[j]:
                    i = a_skip[i]
                else:
                    break
            if a[i] < b[j]:
                i += 1
        else:
            while b_skip[j] is not None:
                comps += 1
                if b[b_skip[j]] <= a[i]:
                    j = b_skip[j]
                else:
                    break
            if b[j] < a[i]:
                j += 1
    return out, comps


def query(t1, t2):
    found = load({t1, t2})
    for t in (t1, t2):
        if t not in found:
            sys.exit(f"索引裡找不到 '{t}'")
    (a, a_skip), (b, b_skip) = found[t1], found[t2]
    plain, c1 = intersect_plain(a, b)
    skip, c2 = intersect_skip(a, a_skip, b, b_skip)
    assert plain == skip == sorted(set(a) & set(b)), "兩種方法的結果不一致"
    print(f"{t1}: {len(a)} 篇，{t2}: {len(b)} 篇，AND 結果: {len(plain)} 篇")
    print(f"比對次數  一般合併: {c1}  有 skip: {c2}  (減少 {1 - c2 / c1:.1%})")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "build":
        build()
    elif len(sys.argv) == 4 and sys.argv[1] == "query":
        query(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
